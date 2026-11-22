// An opening's loan label, and the spheres it can be shared with (the server
// decides: app/routes/openings.py, _shared_spheres).

export const loanLabel = (type) => (type === 'need' ? 'To borrow' : 'To lend');
export const loanQuestion = (type) => (type === 'need' ? 'I only need to borrow it' : "It's a loan: I'd like it back");

const same = (one, other) => String(one) === String(other);

/** Whether an opening (as mapService gives it) is in that sphere, its own or shared. */
export function inSphere(opening, sphereId) {
    if (!sphereId) return false;
    return same(opening.sphereId, sphereId) || (opening.sharedWith || []).some((s) => same(s.id, sphereId));
}

/**
 * The spheres to offer: those the viewer is in, on the same side of demo and
 * real as the opening's own, and whatever it's shared with already (so that
 * can be taken back).
 */
export function shareChoices(spheres, { homeId, userId, isDemo, already = [], mayAdd = true }) {
    if (!homeId) return [];
    const out = new Map(already.map((s) => [String(s.id), { id: String(s.id), name: s.name }]));
    if (mayAdd) {
        (spheres || []).forEach((s) => {
            if (same(s.sphere_id, homeId) || !!s.is_demo !== !!isDemo) return;
            if (!(s.members || []).some((m) => same(m.id, userId) && m.role !== 'pending')) return;
            out.set(String(s.sphere_id), { id: String(s.sphere_id), name: s.name });
        });
    }
    return [...out.values()].sort((a, b) => (a.name || '').localeCompare(b.name || ''));
}
