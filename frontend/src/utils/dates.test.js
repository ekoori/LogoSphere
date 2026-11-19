import { describe, expect, it } from 'vitest';
import { parseServerDate, formatServerDate, timeAgo } from './dates';

describe('parseServerDate', () => {
    it('reads a zone-less API datetime as UTC, not local time', () => {
        expect(parseServerDate('2026-11-18T20:52:14').toISOString()).toBe('2026-11-18T20:52:14.000Z');
        expect(parseServerDate('2026-11-18 20:52').toISOString()).toBe('2026-11-18T20:52:00.000Z');
    });

    it('keeps milliseconds of a Python microsecond timestamp', () => {
        expect(parseServerDate('2026-11-18T20:52:14.416000').toISOString()).toBe('2026-11-18T20:52:14.416Z');
    });

    it('takes zoned values as written', () => {
        expect(parseServerDate('2026-11-18T20:52:14Z').toISOString()).toBe('2026-11-18T20:52:14.000Z');
        expect(parseServerDate('2026-11-19T07:52:14+11:00').toISOString()).toBe('2026-11-18T20:52:14.000Z');
        expect(parseServerDate('Wed, 18 Nov 2026 20:52:14 GMT').toISOString()).toBe('2026-11-18T20:52:14.000Z');
    });

    it('gives null for nothing or nonsense', () => {
        expect(parseServerDate(null)).toBeNull();
        expect(parseServerDate('')).toBeNull();
        expect(parseServerDate('not a date')).toBeNull();
    });
});

describe('timeAgo', () => {
    const now = Date.parse('2026-11-18T21:00:00Z');

    it('counts from the UTC instant', () => {
        expect(timeAgo('2026-11-18T20:52:14.416000', now)).toBe('7m ago');
        expect(timeAgo('2026-11-18T20:59:30', now)).toBe('just now');
        expect(timeAgo('2026-11-18T18:00:00', now)).toBe('3h ago');
        expect(timeAgo('2026-11-16T21:00:00', now)).toBe('2d ago');
    });

    it('falls back to the date after a week, and to nothing without one', () => {
        expect(timeAgo('2026-07-05T05:13:26', now)).toBe(formatServerDate('2026-07-05T05:13:26', { year: false }));
        expect(timeAgo(undefined, now)).toBe('');
    });
});
