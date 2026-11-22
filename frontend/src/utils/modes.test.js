import { afterEach, describe, expect, it, vi } from 'vitest';
import { ADVANCED, SIMPLE, modeOfAccount, rememberMode, rememberedMode } from './modes';

afterEach(() => vi.unstubAllGlobals());

describe('Simple or Advanced', () => {
    it('takes the account at its word, and silence as Advanced', () => {
        expect(modeOfAccount({ ui_mode: 'simple' })).toBe(SIMPLE);
        expect(modeOfAccount({ ui_mode: 'advanced' })).toBe(ADVANCED);
        expect(modeOfAccount({})).toBe(ADVANCED);
        expect(modeOfAccount(undefined)).toBe(ADVANCED);
    });

    it('a newcomer starts Simple, storage or no storage', () => {
        expect(rememberedMode()).toBe(SIMPLE);
        vi.stubGlobal('window', { localStorage: { getItem: () => null } });
        expect(rememberedMode()).toBe(SIMPLE);
    });

    it('remembers the last choice in this browser', () => {
        const kept = new Map();
        vi.stubGlobal('window', { localStorage: { getItem: (k) => kept.get(k) ?? null, setItem: (k, v) => kept.set(k, v) } });
        rememberMode(ADVANCED);
        expect(rememberedMode()).toBe(ADVANCED);
        rememberMode(SIMPLE);
        expect(rememberedMode()).toBe(SIMPLE);
    });
});
