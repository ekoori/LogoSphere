// Resolves sphere / alliance / project NAMES to their UUIDs so cards and
// breadcrumbs can link by ?id= (stable) instead of ?name= (fragile: breaks on
// rename, ambiguous across duplicates). Several models store cross-references
// as bare name strings (a sphere's `alliances`/`projects`, a project's
// `owner_alliance`), so the id has to be looked up from the canonical lists.
//
// The three lists are fetched once and memoised module-wide (short TTL) so
// every card on a page shares one round-trip.
import { useEffect, useState } from 'react';
import api from '../api';

const TTL = 30_000;
const cache = { data: null, ts: 0, inflight: null };

function buildIndex([spheres, alliances, projects]) {
    const map = (rows, idKey) => {
        const byName = {};
        (rows || []).forEach((r) => {
            if (r && r.name && r[idKey]) byName[r.name] = r[idKey];
        });
        return byName;
    };
    return {
        sphereIdByName: map(spheres, 'sphere_id'),
        allianceIdByName: map(alliances, 'alliance_id'),
        projectIdByName: map(projects, 'project_id'),
    };
}

async function loadIndex() {
    const now = Date.now();
    if (cache.data && now - cache.ts < TTL) return cache.data;
    if (cache.inflight) return cache.inflight;
    cache.inflight = Promise.all([
        api.get('/api/spheres').then((r) => r.data).catch(() => []),
        api.get('/api/alliances').then((r) => r.data).catch(() => []),
        api.get('/api/projects').then((r) => r.data).catch(() => []),
    ]).then((lists) => {
        cache.data = buildIndex(lists);
        cache.ts = Date.now();
        cache.inflight = null;
        return cache.data;
    }).catch(() => {
        cache.inflight = null;
        return { sphereIdByName: {}, allianceIdByName: {}, projectIdByName: {} };
    });
    return cache.inflight;
}

const EMPTY = { sphereIdByName: {}, allianceIdByName: {}, projectIdByName: {} };

// Returns { sphereIdByName, allianceIdByName, projectIdByName, entityHref }.
// entityHref(kind, name, knownId) → '/kind?id=<id>' when resolvable, else
// '/kind?name=<name>' as a graceful fallback.
export function useEntityIndex() {
    const [index, setIndex] = useState(cache.data || EMPTY);
    useEffect(() => {
        let alive = true;
        loadIndex().then((idx) => { if (alive) setIndex(idx); });
        return () => { alive = false; };
    }, []);

    const mapFor = { sphere: index.sphereIdByName, alliance: index.allianceIdByName, project: index.projectIdByName };
    const entityHref = (kind, name, knownId) => {
        const id = knownId || (mapFor[kind] || {})[name];
        if (id) return `/${kind}?id=${id}`;
        return `/${kind}?name=${encodeURIComponent(name)}`;
    };

    return { ...index, entityHref };
}
