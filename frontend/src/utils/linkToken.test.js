import { describe, expect, it } from 'vitest';
import { tokenFromHash } from './linkToken';

describe("an emailed link's token", () => {
    it('is read named or bare', () => {
        expect(tokenFromHash('#token=ab_C-12')).toBe('ab_C-12');
        expect(tokenFromHash('#x=1&token=ab_C-12')).toBe('ab_C-12');
        expect(tokenFromHash('#0af3.9bc1')).toBe('0af3.9bc1');
    });

    it('is nothing otherwise', () => {
        ['', '#', undefined, '#<script>', '#a/b'].forEach((hash) => expect(tokenFromHash(hash)).toBe(''));
    });
});
