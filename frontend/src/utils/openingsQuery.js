// What the openings page asks the server for, a page at a time (backend: app/utils/openings_feed.py).

export const OPENINGS_PAGE = 30;

/** The filters on the page, as GET /api/openings takes them. */
export function openingsQuery({ filter = 'all', sphereFilter = 'all', near = 0, q = '' } = {}) {
    const out = { limit: OPENINGS_PAGE };
    if (filter === 'offers') out.type = 'offer';
    if (filter === 'needs') out.type = 'need';
    if (filter === 'loans') out.loans = 1;
    if (sphereFilter === 'real' || sphereFilter === 'demo') out.demo = sphereFilter;
    else if (sphereFilter && sphereFilter !== 'all') out.sphere = sphereFilter;
    if (near > 0) out.km = near;
    const words = (q || '').trim();
    if (words) out.q = words;
    return out;
}

/** All the pages loaded so far, as one list: each opening once, in the order they came. */
export function openingsOf(pages) {
    const seen = new Set();
    const out = [];
    (pages || []).forEach((page) => (page.openings || []).forEach((o) => {
        if (!seen.has(o.id)) {
            seen.add(o.id);
            out.push(o);
        }
    }));
    return out;
}
