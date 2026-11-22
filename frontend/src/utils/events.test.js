import { describe, expect, it } from 'vitest';
import { comingText, hasEnded, lengthText, ordinal, repeatText, tileOf, whenText } from './events';

const opts = { locale: 'en-GB', viewerZone: 'Europe/Paris', now: new Date('2027-01-01T00:00:00Z') };

describe('repeating, in words', () => {
    it('names the weekday, the date or which weekday of the month', () => {
        expect(repeatText('never', '2027-03-25')).toBe("Doesn't repeat");
        expect(repeatText('weekly', '2027-03-25')).toBe('Every Thursday');
        expect(repeatText('monthly', '2027-03-12')).toBe('Every month on the 12th');
        expect(repeatText('monthly', '2027-03-31')).toBe("Every month on the 31st, or the month's last day");
        expect(repeatText('monthly_weekday', '2027-01-12')).toBe('Every month on the second Tuesday');
        expect(repeatText('monthly_weekday', '2027-03-31')).toBe('Every month on the last Wednesday');
    });
    it('still says something before a date is chosen', () => {
        expect(repeatText('weekly', '')).toBe('Every week');
    });
    it('counts in English', () => {
        expect([1, 2, 3, 4, 11, 12, 13, 21, 22, 23].map(ordinal))
            .toEqual(['1st', '2nd', '3rd', '4th', '11th', '12th', '13th', '21st', '22nd', '23rd']);
    });
});

describe('when it is', () => {
    const evening = { starts_at: '2027-03-25T18:00:00', ends_at: '2027-03-25T20:00:00' };

    it("is told on the event's clock, the API's times being UTC", () => {
        const { text, zoneNote } = whenText(evening, 'Europe/Paris', opts);
        expect(text).toMatch(/25 Mar, 19:00–21:00$/);
        expect(zoneNote).toBe('');
    });
    it('names the clock when the reader is on another', () => {
        expect(whenText(evening, 'America/New_York', opts).zoneNote).toBe('America/New York time');
    });
    it('does not name two names for one clock', () => {
        expect(whenText(evening, 'Asia/Calcutta', { ...opts, viewerZone: 'Asia/Kolkata' }).zoneNote).toBe('');
    });
    it('gives both days when it runs past one', () => {
        const long = { starts_at: '2027-03-25T09:00:00', ends_at: '2027-03-27T09:00:00' };
        expect(whenText(long, 'Europe/Paris', opts).text).toMatch(/25 Mar, 10:00 – .*27 Mar, 10:00$/);
    });
    it('knows when it has ended', () => {
        expect(hasEnded(evening, Date.UTC(2027, 2, 25, 19, 59))).toBe(false);
        expect(hasEnded(evening, Date.UTC(2027, 2, 25, 20, 0))).toBe(true);
    });
});

describe('small words', () => {
    it('says how long', () => {
        expect([30, 60, 90, 120, 100, 1440, 4320].map(lengthText))
            .toEqual(['30 minutes', '1 hour', '1½ hours', '2 hours', '1 hour 40 minutes', '1 day', '3 days']);
    });
    it('keeps a date its own in every zone', () => {
        expect(tileOf('2027-11-01', 'en-GB')).toEqual({ date: '1', month: 'Nov' });
    });
    it('says who is coming', () => {
        expect(comingText({ going: 2, maybe: 1 })).toBe('2 going · 1 maybe');
        expect(comingText({ going: 0, maybe: 0 })).toBe('');
    });
});
