// Simple or Advanced: how much of LogoSphere someone is shown. Simple keeps to
// the gift economy with fewer options; nothing is ever forbidden by it, and
// whatever is owed (approvals, confirmations, a link to a vote) still shows.
// The choice is account data (users.ui_mode); this browser only remembers the
// last one, so the first paint doesn't flash the other.
export const SIMPLE = 'simple';
export const ADVANCED = 'advanced';
export const MODE_CHOICES = [
    [SIMPLE, 'Simple', 'Offers, needs, thanks and what people care about, with fewer options.'],
    [ADVANCED, 'Advanced', 'Everything: voting, group settings, kinds of meaning and fine-tuning.'],
];

const KEY = 'logosphere-ui-mode';

/** A signed-in account's mode, from its data. Nothing said counts as Advanced. */
export const modeOfAccount = (data) => (data?.ui_mode === SIMPLE ? SIMPLE : ADVANCED);

/** Before anyone is known to be signed in: the last one here, else Simple (a newcomer). */
export function rememberedMode() {
    try {
        return window.localStorage.getItem(KEY) === ADVANCED ? ADVANCED : SIMPLE;
    } catch (_) {
        return SIMPLE;
    }
}

export function rememberMode(mode) {
    try {
        window.localStorage.setItem(KEY, mode);
    } catch (_) { /* private mode: it holds for this page */ }
}
