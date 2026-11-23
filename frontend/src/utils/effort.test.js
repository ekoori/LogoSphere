import { describe, expect, it } from 'vitest';
import { hoursGiven } from './effort';

describe('hours on a receipt', () => {
    it('says it as plainly as it was given', () => {
        expect(hoursGiven(2)).toBe('About 2 hours');
        expect(hoursGiven(1)).toBe('About 1 hour');
        expect(hoursGiven(2.5)).toBe('About 2.5 hours');
        expect(hoursGiven(0.75)).toBe('About 45 minutes');
        expect(hoursGiven(1.25, { short: true })).toBe('1.25 h');
        expect(hoursGiven(0.5, { short: true })).toBe('30 min');
    });

    it('says nothing when nothing was given', () => {
        expect(hoursGiven(null)).toBe('');
        expect(hoursGiven(0)).toBe('');
        expect(hoursGiven('x')).toBe('');
    });
});
