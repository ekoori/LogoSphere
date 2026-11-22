// Where signing in or joining goes back to: only ever a page of this site.

/** Where ProtectedRoute (or an invitation) was headed, from the router's state. */
export function returnTo(state, fallback = '/profile') {
    const from = state?.from;
    const path = from?.pathname;
    if (typeof path !== 'string' || !/^\/(?![/\\])/.test(path) || /^\/(login|register)\b/.test(path)) return fallback;
    return `${path}${from.search || ''}${from.hash || ''}`;
}

/** The code in "/invite#code" or "/register#invite=code". */
export function inviteFromHash(hash) {
    return /^#?(?:invite=)?([\w-]{16,100})$/.exec(hash || '')?.[1] || '';
}

export const groupHref = (group) => (group ? `/${group.kind}?id=${group.id}` : null);
