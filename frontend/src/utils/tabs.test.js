import { describe, expect, it } from 'vitest';
import { tabFrom } from './tabs';

const ALL = ['meaning_trail', 'offers-needs', 'members', 'governance'];

describe('the tab a page opens on', () => {
    it('is Openings unless a link says otherwise', () => {
        expect(tabFrom(null, ALL)).toBe('offers-needs');
        expect(tabFrom('nonsense', ALL)).toBe('offers-needs');
    });
    it('follows a link, in either vocabulary', () => {
        expect(tabFrom('meaning_trail', ALL)).toBe('meaning_trail');
        expect(tabFrom('trail', ALL)).toBe('meaning_trail');
        expect(tabFrom('people', ALL)).toBe('members');
        expect(tabFrom('governance', ALL)).toBe('governance');
    });
    it('never opens a tab the page does not have', () => {
        expect(tabFrom('governance', ['meaning_trail', 'offers-needs'])).toBe('offers-needs');
    });
});
