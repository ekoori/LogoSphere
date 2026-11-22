import { describe, expect, it } from 'vitest';
import { groupHref, inviteFromHash, returnTo } from './returnTo';

describe('returnTo', () => {
    it('goes back to the page that was asked for', () => {
        expect(returnTo({ from: { pathname: '/event', search: '?id=7', hash: '' } })).toBe('/event?id=7');
        expect(returnTo({ from: { pathname: '/invite', hash: '#abc' } })).toBe('/invite#abc');
    });
    it('only ever to a page of this site, and not to signing in', () => {
        for (const pathname of ['//elsewhere.example', '/\\elsewhere.example', 'https://elsewhere.example', '/login', undefined, 7]) {
            expect(returnTo({ from: { pathname } })).toBe('/profile');
        }
        expect(returnTo(null, '/')).toBe('/');
    });
});

describe('inviteFromHash', () => {
    const code = 'Zm9v-YmFy_YmF6cXV4MTIzNDU2';
    it('reads both forms', () => {
        expect(inviteFromHash(`#${code}`)).toBe(code);
        expect(inviteFromHash(`#invite=${code}`)).toBe(code);
    });
    it('reads nothing else', () => {
        for (const hash of ['', '#short', `#token=${code}`, `#${code}<x>`]) expect(inviteFromHash(hash)).toBe('');
    });
});

describe('groupHref', () => {
    it('is the group page', () => {
        expect(groupHref({ id: '7', kind: 'alliance' })).toBe('/alliance?id=7');
        expect(groupHref(null)).toBe(null);
    });
});
