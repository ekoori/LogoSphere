// Resolves the spheres/alliances/projects a user manages — used to populate
// "clone this value card to..." pickers. Mirrors useEntityIndex.js: the three
// lists are fetched once and memoised module-wide (short TTL) so every chip
// on a page shares one round-trip instead of each firing its own.
//
// "Manages" mirrors the backend's can_manage_entity (permissions.py) exactly,
// so anything offered here is guaranteed to be accepted server-side:
//   sphere:  any member (the sphere model treats all participants as able
//            to act on the sphere's behalf)
//   alliance: role 'admin' (Lead) or 'steward' (Board member)
//   project:  role 'manager' or 'steward'
import { useEffect, useState } from 'react';
import api from '../api';

const TTL = 30_000;
const cache = { userId: null, data: null, fetchedAt: 0, inflight: null };

function hasRole(members, userId, roles) {
    const m = (members || []).find((x) => String(x.id) === String(userId));
    return !!m && (!roles || roles.includes(m.role));
}

function buildManaged([spheres, alliances, projects], userId) {
    const out = [];
    // sphere_id lets callers scope entities to a given sphere (e.g. accepting an
    // opening as an entity that must belong to that opening's sphere). A sphere
    // is "in" itself; an alliance/project carries its own sphere_id.
    (spheres || []).forEach((s) => {
        if (hasRole(s.members, userId)) {
            out.push({ id: s.sphere_id, name: s.name, kind: 'sphere', sphere_id: s.sphere_id });
        }
    });
    (alliances || []).forEach((a) => {
        if (hasRole(a.members, userId, ['admin', 'steward'])) {
            out.push({ id: a.alliance_id || a.id, name: a.name, kind: 'alliance', sphere_id: a.sphere_id });
        }
    });
    (projects || []).forEach((p) => {
        if (hasRole(p.members, userId, ['manager', 'steward'])) {
            out.push({ id: p.project_id || p.id, name: p.name, kind: 'project', sphere_id: p.sphere_id });
        }
    });
    return out;
}

async function loadManaged(userId) {
    const now = Date.now();
    if (cache.data && cache.userId === userId && now - cache.fetchedAt < TTL) return cache.data;
    if (cache.inflight) return cache.inflight;
    cache.inflight = Promise.all([
        api.get('/api/spheres').then((r) => r.data).catch(() => []),
        api.get('/api/alliances').then((r) => r.data).catch(() => []),
        api.get('/api/projects').then((r) => r.data).catch(() => []),
    ]).then((lists) => {
        cache.data = buildManaged(lists, userId);
        cache.userId = userId;
        cache.fetchedAt = Date.now();
        cache.inflight = null;
        return cache.data;
    }).catch(() => {
        cache.inflight = null;
        return [];
    });
    return cache.inflight;
}

// Returns [{ id, name, kind }] for every entity `userId` can act on behalf of.
export function useManagedEntities(userId) {
    const [managed, setManaged] = useState([]);
    useEffect(() => {
        if (!userId) { setManaged([]); return undefined; }
        let alive = true;
        loadManaged(userId).then((list) => { if (alive) setManaged(list); });
        return () => { alive = false; };
    }, [userId]);
    return managed;
}
