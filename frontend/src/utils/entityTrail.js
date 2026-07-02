// Aggregates a Meaning Trail for a governance entity (sphere/alliance/project)
// out of two sources:
//   - `ownEntityIds` — entities whose own MeaningTrail partition is fetched
//     directly (an entity can itself be an opening's provider / an exchange's
//     initiator, exactly like a user — see backend `Service.create`).
//   - `projectIds` — projects whose personally-tagged exchanges (project_id on
//     someone's own trail row) also belong to this page's feed.
// Results are deduped by exchange_id and mapped through mapExchange with a
// per-row perspective: "You" only when the ACTUAL viewer happens to be that
// row's initiator, real names otherwise (this is an aggregate multi-person
// feed, not a single person's trail).
import api from '../api';
import { mapExchange } from './mappers';

export async function fetchAggregateTrail({ ownEntityIds = [], projectIds = [] }, viewerId) {
    const calls = [
        ...ownEntityIds.filter(Boolean).map((id) =>
            api.post('/api/meaning_trail', { userId: id }).then((r) => r.data || []).catch(() => [])),
        ...projectIds.filter(Boolean).map((id) =>
            api.get(`/api/meaning_trail/by_project/${id}`).then((r) => r.data || []).catch(() => [])),
    ];
    const results = await Promise.all(calls);

    const seen = new Set();
    const rows = [];
    results.flat().forEach((row) => {
        if (seen.has(row.exchange_id)) return;
        seen.add(row.exchange_id);
        rows.push(row);
    });

    return rows.map((row) => mapExchange(row, {
        ownerLabel: row.initiator_id === viewerId ? 'You' : (row.initiator_name || 'Initiator'),
        ownerId: row.initiator_id === viewerId ? null : row.initiator_id,
    }));
}
