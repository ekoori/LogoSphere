import { describe, expect, it } from 'vitest';
import { cardForHelp, pictureFile, withSuggestion } from './aiHelp';

const form = {
    title: 'Mending', care_about: ' ', because: '', looks_like_raw: 'Darning\n\n  Asking who can ',
    drift_looks_like: 'Buying new', in_conflict: '', never_do: '', frankl_mode: 'creative', color_key: 'leaf',
};

describe('AI help with a card', () => {
    it('sends only what is typed in fields that show', () => {
        expect(cardForHelp(form)).toEqual({
            title: 'Mending', drift_looks_like: 'Buying new', looks_like: ['Darning', 'Asking who can'],
        });
        expect(cardForHelp(form, { brief: true })).toEqual({ title: 'Mending' });
    });

    it('never wipes what was typed with an empty suggestion', () => {
        const next = withSuggestion(form, { title: '', care_about: 'I care about mending.', looks_like: [] });
        expect(next).toEqual({ ...form, care_about: 'I care about mending.' });
    });

    it('changes nothing hidden in Simple', () => {
        const draft = { title: 'Mend first', looks_like: ['x'], never_do: 'Bin it', frankl_mode: 'attitudinal' };
        expect(withSuggestion(form, draft, { brief: true })).toEqual({ ...form, title: 'Mend first' });
        expect(withSuggestion(form, draft)).toMatchObject({ looks_like_raw: 'x', never_do: 'Bin it', frankl_mode: 'attitudinal' });
    });

    it('keeps a picture byte for byte', async () => {
        const file = pictureFile(btoa(String.fromCharCode(255, 216, 0, 7)));
        expect(file.type).toBe('image/jpeg');
        expect([...new Uint8Array(await file.arrayBuffer())]).toEqual([255, 216, 0, 7]);
    });
});
