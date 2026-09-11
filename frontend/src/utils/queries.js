// queries.js — the app's data layer on top of TanStack Query.
//
// Every page used to fetch whole list endpoints (and then .find() one row),
// and every card fired its own /api/value_cards/<id> request; two hand-rolled
// module caches (useEntityIndex / useManagedEntities) papered over the worst
// of it. This replaces all of that with shared, cached, de-duplicated queries:
//
//   useEntity(kind, id)        one sphere/alliance/project by id (detail endpoint)
//   useEntityList(kind)        the list (value cards embedded server-side)
//   useOpenings()              the marketplace list
//   useEntityIndex()           name -> id resolution for legacy name references
//   useManagedEntities(userId) entities the user can act on behalf of
//   invalidateEntity(kind,id)  refresh after a mutation
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useMemo } from 'react';
import api from '../api';
import { useLogin } from '../App';

export const KIND_PATH = { sphere: 'spheres', alliance: 'alliances', project: 'projects' };
export const ID_KEY = { sphere: 'sphere_id', alliance: 'alliance_id', project: 'project_id' };

const STALE = 30_000;

const get = (url) => api.get(url).then((r) => r.data);

// ── Entities ─────────────────────────────────────────────────────────────────
export function useEntity(kind, id, { enabled = true } = {}) {
    return useQuery({
        queryKey: ['entity', kind, id],
        queryFn: () => get(`/api/${KIND_PATH[kind]}/${id}`),
        enabled: !!kind && !!id && enabled,
        staleTime: STALE,
        retry: (count, err) => err?.response?.status >= 500 && count < 2,
    });
}

export function useEntityList(kind, { enabled = true } = {}) {
    return useQuery({
        queryKey: ['entities', kind],
        queryFn: () => get(`/api/${KIND_PATH[kind]}`),
        enabled: !!kind && enabled,
        staleTime: STALE,
    });
}

export function useOpenings({ enabled = true } = {}) {
    return useQuery({
        queryKey: ['openings'],
        queryFn: () => get('/api/openings'),
        enabled,
        staleTime: 15_000,
    });
}

export function useOpening(id, { enabled = true } = {}) {
    return useQuery({
        queryKey: ['opening', id],
        queryFn: () => get(`/api/openings/${id}`),
        enabled: !!id && enabled,
        staleTime: 15_000,
        retry: false,
    });
}

// A public (logged-out) view of a sphere flagged is_public.
export function usePublicSphere(id, { enabled = true } = {}) {
    return useQuery({
        queryKey: ['public-sphere', id],
        queryFn: () => get(`/api/public/spheres/${id}`),
        enabled: !!id && enabled,
        staleTime: STALE,
        retry: false,
    });
}

// ── Derived views over the lists ────────────────────────────────────────────
const EMPTY_INDEX = { sphereIdByName: {}, allianceIdByName: {}, projectIdByName: {} };

// Some rows still cross-reference by NAME (a sphere's `alliances`/`projects`,
// a project's `owner_alliance`). entityHref(kind, name, knownId) resolves to a
// stable ?id= link when it can, falling back to ?name=.
export function useEntityIndex() {
    // Lists are members-only; don't fire (and 401) for logged-out visitors.
    const { userId } = useLogin();
    const spheres = useEntityList('sphere', { enabled: !!userId });
    const alliances = useEntityList('alliance', { enabled: !!userId });
    const projects = useEntityList('project', { enabled: !!userId });
    const index = useMemo(() => {
        const map = (rows, idKey) => {
            const byName = {};
            (rows || []).forEach((r) => { if (r?.name && r[idKey]) byName[r.name] = r[idKey]; });
            return byName;
        };
        if (!spheres.data && !alliances.data && !projects.data) return EMPTY_INDEX;
        return {
            sphereIdByName: map(spheres.data, 'sphere_id'),
            allianceIdByName: map(alliances.data, 'alliance_id'),
            projectIdByName: map(projects.data, 'project_id'),
        };
    }, [spheres.data, alliances.data, projects.data]);

    const mapFor = { sphere: index.sphereIdByName, alliance: index.allianceIdByName, project: index.projectIdByName };
    const entityHref = (kind, name, knownId) => {
        const id = knownId || (mapFor[kind] || {})[name];
        return id ? `/${kind}?id=${id}` : `/${kind}?name=${encodeURIComponent(name)}`;
    };
    return { ...index, entityHref };
}

function hasRole(members, userId, roles) {
    const m = (members || []).find((x) => String(x.id) === String(userId));
    return !!m && (!roles || roles.includes(m.role));
}

// Entities the user may act on behalf of — mirrors backend can_manage_entity:
//   sphere: admin only; alliance: admin/steward; project: manager/steward.
// (A platform admin can act for anything; callers pass isPlatformAdmin.)
export function useManagedEntities(userId, isPlatformAdmin = false) {
    const spheres = useEntityList('sphere', { enabled: !!userId });
    const alliances = useEntityList('alliance', { enabled: !!userId });
    const projects = useEntityList('project', { enabled: !!userId });
    return useMemo(() => {
        if (!userId) return [];
        const out = [];
        (spheres.data || []).forEach((s) => {
            if (isPlatformAdmin || hasRole(s.members, userId, ['admin'])) {
                out.push({ id: s.sphere_id, name: s.name, kind: 'sphere', sphere_id: s.sphere_id });
            }
        });
        (alliances.data || []).forEach((a) => {
            if (isPlatformAdmin || hasRole(a.members, userId, ['admin', 'steward'])) {
                out.push({ id: a.alliance_id, name: a.name, kind: 'alliance', sphere_id: a.sphere_id });
            }
        });
        (projects.data || []).forEach((p) => {
            if (isPlatformAdmin || hasRole(p.members, userId, ['manager', 'steward'])) {
                out.push({ id: p.project_id, name: p.name, kind: 'project', sphere_id: p.sphere_id });
            }
        });
        return out;
    }, [userId, isPlatformAdmin, spheres.data, alliances.data, projects.data]);
}

// ── Invalidation helpers ────────────────────────────────────────────────────
export function useInvalidate() {
    const qc = useQueryClient();
    return {
        entity: (kind, id) => Promise.all([
            qc.invalidateQueries({ queryKey: ['entity', kind, id] }),
            qc.invalidateQueries({ queryKey: ['entities', kind] }),
            qc.invalidateQueries({ queryKey: ['public-sphere', id] }),
        ]),
        openings: () => qc.invalidateQueries({ queryKey: ['openings'] }),
        opening: (id) => Promise.all([
            qc.invalidateQueries({ queryKey: ['opening', id] }),
            qc.invalidateQueries({ queryKey: ['openings'] }),
        ]),
        all: () => qc.invalidateQueries(),
    };
}
