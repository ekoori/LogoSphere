// What the Meaning Graph shows for the current filters (pure; the app's
// core/logic/GraphView.kt does the same). Closeness itself is the server's:
// nothing here changes a score, only what is drawn.
export const KINDS = [
    { key: 'creative', glyph: '✶', label: 'Creative', gloss: 'something made or given' },
    { key: 'experiential', glyph: '❍', label: 'Experiential', gloss: 'something received or shared' },
    { key: 'attitudinal', glyph: '△', label: 'Attitudinal', gloss: 'a stance taken under constraint' },
];
export const kindOf = (node) => KINDS.find((k) => k.key === node?.card?.frankl_mode) || KINDS[0];
export const titleOf = (node) => node?.card?.title || node?.card?.care_about || 'Untitled value';
export const percent = (x) => `${Math.round((x || 0) * 100)}%`;

function matches(node, query) {
    const q = (query || '').trim().toLowerCase();
    if (!q) return true;
    const c = node.card || {};
    return [c.title, c.care_about, c.because, node.owner?.name, ...(c.looks_like || [])]
        .some((f) => (f || '').toLowerCase().includes(q));
}

/**
 * The cards and connections to draw.
 * scope: 'all', 'near' (your spheres) or 'mine' (your cards and what they connect to).
 * owner: one person's or group's cards and what they connect to; focus: one card's.
 * A search keeps what matches and what that connects to, so it isn't an island.
 */
export function visibleGraph(graph, { scope = 'all', owner = null, focus = null, demos = true, query = '', from = 0 } = {}) {
    let nodes = graph.nodes.filter((n) => demos || !n.is_demo || n.mine);
    let ids = new Set(nodes.map((n) => n.id));
    let edges = graph.edges.filter((e) => e.closeness >= from && ids.has(e.a) && ids.has(e.b));

    const around = (keep) => {
        const out = new Set(nodes.filter(keep).map((n) => n.id));
        const seeds = new Set(out);
        edges.forEach((e) => {
            if (seeds.has(e.a)) out.add(e.b);
            if (seeds.has(e.b)) out.add(e.a);
        });
        return out;
    };
    const narrow = (keep) => {
        nodes = nodes.filter((n) => keep.has(n.id));
        ids = new Set(nodes.map((n) => n.id));
        edges = edges.filter((e) => ids.has(e.a) && ids.has(e.b));
    };

    if (focus && ids.has(focus)) narrow(around((n) => n.id === focus));
    else if (owner) narrow(around((n) => n.owner?.id === owner));
    else if (scope === 'mine') narrow(around((n) => n.mine));
    else if (scope === 'near') narrow(new Set(nodes.filter((n) => n.near).map((n) => n.id)));

    const found = new Set(nodes.filter((n) => matches(n, query)).map((n) => n.id));
    if ((query || '').trim()) narrow(around((n) => found.has(n.id)));

    const degree = new Map(nodes.map((n) => [n.id, 0]));
    edges.forEach((e) => {
        degree.set(e.a, degree.get(e.a) + 1);
        degree.set(e.b, degree.get(e.b) + 1);
    });
    return { nodes, edges, degree, found };
}

/** A card's connections, closest first. */
export function closestTo(id, edges) {
    return edges
        .filter((e) => e.a === id || e.b === id)
        .map((e) => ({ edge: e, other: e.a === id ? e.b : e.a }))
        .sort((x, y) => y.edge.closeness - x.edge.closeness || x.other.localeCompare(y.other));
}
