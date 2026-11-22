// AI help's pure parts (components/AiPictureMaker.js, components/AiCardHelp.js).

const TEXT_FIELDS = ['title', 'care_about', 'because', 'drift_looks_like', 'in_conflict', 'never_do'];
const BRIEF_FIELDS = ['title', 'care_about', 'because'];

/** The part of the card form that may be sent: only what's typed in fields the member can see. */
export function cardForHelp(form, { brief = false } = {}) {
    const out = {};
    (brief ? BRIEF_FIELDS : TEXT_FIELDS).forEach((key) => {
        const value = (form[key] || '').trim();
        if (value) out[key] = value;
    });
    if (!brief) {
        const lines = (form.looks_like_raw || '').split('\n').map((l) => l.trim()).filter(Boolean);
        if (lines.length) out.looks_like = lines;
    }
    return out;
}

/**
 * The form with a suggestion in it. An empty suggestion never wipes what was
 * typed, and Simple's fields are all that change in Simple.
 */
export function withSuggestion(form, draft, { brief = false } = {}) {
    const next = { ...form };
    (brief ? BRIEF_FIELDS : [...TEXT_FIELDS, 'frankl_mode']).forEach((key) => {
        if (draft[key]) next[key] = draft[key];
    });
    if (!brief && draft.looks_like?.length) next.looks_like_raw = draft.looks_like.join('\n');
    return next;
}

/** A picture as it came from the server, byte for byte: that is how it stays labelled. */
export function pictureFile(base64, type = 'image/jpeg') {
    const binary = atob(base64);
    const bytes = new Uint8Array(binary.length);
    for (let i = 0; i < binary.length; i += 1) bytes[i] = binary.charCodeAt(i);
    return new File([bytes], 'ai-picture.jpg', { type });
}
