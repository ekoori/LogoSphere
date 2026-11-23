import { describe, expect, it } from 'vitest';
import { lastOfTheirs, mergeMessages, messagesHref, subjectOf } from './thread';

const m = (id, at, mine = false, text = id) => ({ id, at: `2026-11-23T10:00:0${at}.000`, mine, text });

describe('a conversation', () => {
    it('merges pages and polls, oldest first, each once', () => {
        const merged = mergeMessages([m('b', 2), m('c', 3)], [m('a', 1), m('c', 3, false, 'again'), m('d', 4)]);
        expect(merged.map((x) => x.id)).toEqual(['a', 'b', 'c', 'd']);
        expect(merged[2].text).toBe('again');
    });

    it('knows how far was read', () => {
        expect(lastOfTheirs([m('a', 1), m('b', 2), m('c', 3, true)])).toBe('b');
        expect(lastOfTheirs([m('c', 3, true)])).toBe(null);
    });

    it('links to a person, about an opening or not', () => {
        expect(messagesHref('p')).toBe('/messages?with=p');
        expect(messagesHref('p', 'o')).toBe('/messages?with=p&opening=o');
        expect(messagesHref('p', { kind: 'sphere', id: 's' })).toBe('/messages?with=p&about=sphere:s');
    });

    it('reads what a message is about, old or new', () => {
        expect(subjectOf({ about: { kind: 'event', id: 'e', title: 'Supper', link: '/event?id=e' } }).link).toBe('/event?id=e');
        expect(subjectOf({ opening: { id: 'o', title: 'Ladder' } })).toEqual({ id: 'o', title: 'Ladder', kind: 'opening', link: '/opening?id=o' });
        expect(subjectOf({ text: 'hi' })).toBeNull();
    });
});
