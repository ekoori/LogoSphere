// The tab a page opens on. Openings is the default everywhere (Trail stays
// first in the row); a link can name another with ?tab=, in the site's keys or
// in the short names the app and notifications use.
export const TRAIL_TAB = 'meaning_trail';
export const OPENINGS_TAB = 'offers-needs';
export const DEFAULT_TAB = OPENINGS_TAB;

const SHORT = { trail: TRAIL_TAB, openings: OPENINGS_TAB, people: 'members' };

export function tabFrom(param, allowed) {
    const key = SHORT[param] || param;
    return allowed.includes(key) ? key : DEFAULT_TAB;
}
