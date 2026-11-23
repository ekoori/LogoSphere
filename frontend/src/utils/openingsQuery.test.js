import { describe, expect, it } from 'vitest';
import { OPENINGS_PAGE, openingsOf, openingsQuery } from './openingsQuery';

describe('the openings page asks for one page at a time', () => {
    it('turns the filters into the server’s terms', () => {
        expect(openingsQuery()).toEqual({ limit: OPENINGS_PAGE });
        expect(openingsQuery({ filter: 'needs', sphereFilter: 'demo', near: 5, q: '  drill ' }))
            .toEqual({ limit: OPENINGS_PAGE, type: 'need', demo: 'demo', km: 5, q: 'drill' });
        expect(openingsQuery({ filter: 'loans', sphereFilter: 's1' })).toEqual({ limit: OPENINGS_PAGE, loans: 1, sphere: 's1' });
    });

    it('lists each opening once, in the order the pages came', () => {
        const pages = [{ openings: [{ id: 'a' }, { id: 'b' }] }, { openings: [{ id: 'b' }, { id: 'c' }] }];
        expect(openingsOf(pages).map((o) => o.id)).toEqual(['a', 'b', 'c']);
        expect(openingsOf(undefined)).toEqual([]);
    });
});
