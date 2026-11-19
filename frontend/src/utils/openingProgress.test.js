import { describe, expect, it } from 'vitest';
import { buildOpeningProgress, SERVICE_STEPS } from './openingProgress';

describe('buildOpeningProgress', () => {
    it('follows a one-time opening\'s status, dating each phase once reached', () => {
        const p = buildOpeningProgress({
            status: 'In Progress', cadence: 'single',
            postedAt: 'Jun 1, 2026', acceptedAt: 'Jun 2, 2026', inProgressAt: 'Jun 3, 2026', completedAt: 'Jun 9, 2026',
        });
        expect(p.currentIndex).toBe(2);
        expect(p.cancelled).toBe(false);
        expect(p.steps.map((s) => s.label)).toEqual(SERVICE_STEPS);
        expect(p.steps.map((s) => s.time)).toEqual(['Jun 1, 2026', 'Jun 2, 2026', 'Jun 3, 2026', '']);
    });

    it('aggregates a perpetual opening\'s many acceptances', () => {
        const p = buildOpeningProgress({
            status: 'Posted', cadence: 'perpetual', postedAt: 'Jun 1, 2026',
            activity: { acceptedCount: 3, acceptedLastAt: 'Jul 1, 2026', inProgressCount: 1, inProgressLastAt: 'Jul 2, 2026' },
        });
        expect(p.currentIndex).toBe(2);
        expect(p.steps[1].label).toBe('Accepted (multiple)');
        expect(p.steps[2].time).toBe('Jul 2, 2026');
        expect(p.steps[3].time).toBe('');
    });

    it('marks a withdrawn opening cancelled', () => {
        const p = buildOpeningProgress({ status: 'Cancelled', cadence: 'single', postedAt: 'Jun 1, 2026' });
        expect(p.cancelled).toBe(true);
    });

    it('treats an unknown status as just posted', () => {
        expect(buildOpeningProgress({ status: 'Open', cadence: 'single' }).currentIndex).toBe(0);
    });
});
