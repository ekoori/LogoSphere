import { describe, expect, it } from 'vitest';
import { fitWithin } from './pictures';

describe('phone photos before upload', () => {
    it('shrinks to the longest side', () => {
        expect(fitWithin(4032, 3024)).toEqual({ width: 2048, height: 1536 });
        expect(fitWithin(3024, 4032)).toEqual({ width: 1536, height: 2048 });
    });
    it('never enlarges', () => {
        expect(fitWithin(800, 600)).toEqual({ width: 800, height: 600 });
    });
});
