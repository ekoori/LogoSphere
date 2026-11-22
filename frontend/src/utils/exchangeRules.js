// Exchange lifecycle rules for the Exchange page — what a participant can do
// next. They follow the backend's guards (routes/meaning_trail.py
// _TRANSITIONS) so the page never offers a move the server refuses; the
// Android app's ExchangeRules mirrors them.

// The progress bar's steps. The follow-up step is only ever reached by
// actually adding a follow-up note, so it isn't one of these.
export const XC_STEPS = ['Initiated', 'In Progress', 'Finished', 'Receipted'];
export const XC_FOLLOWUP_STEP = 'Follow up added';
export const XC_FOLLOWUP_STATUS = 'Additional Comments Added';

// The only moves made by hand. "Receipted" is reached by adding the receipt,
// never set directly — offering "Mark as Receipted" only ever got a 409.
const MANUAL_NEXT = { 'Initiated': 'In Progress', 'In Progress': 'Finished' };
// The initiator may cancel only before the exchange is finished.
const CANCELLABLE = ['Initiated', 'In Progress'];

export const statusOf = (xc) => (xc && xc.exchange_status) || 'Initiated';

export const isCancelled = (xc) => statusOf(xc) === 'Cancelled';

/** The status a participant can move the exchange to next, or null. */
export const nextStatus = (xc) => (isCancelled(xc) ? null : MANUAL_NEXT[statusOf(xc)] || null);

/** Cancelling is the initiator's, and only before the exchange is finished. */
export const canCancel = (xc, isInitiator) => !!isInitiator && CANCELLABLE.includes(statusOf(xc));

/** Finished, but the recipient hasn't written their receipt yet. */
export const awaitingReceipt = (xc) => statusOf(xc) === 'Finished' && !xc.gratitude_comment;

/** Which side of an exchange this person is, by name or by acting for it; null for neither. */
export const sideOf = (row, userId) => {
    if (!row || !userId) return null;
    const me = String(userId);
    if ([row.user_id, row.initiator_acting_user_id].some((id) => id && String(id) === me)) return 'initiator';
    if ([row.other_user_id, row.recipient_acting_user_id].some((id) => id && String(id) === me)) return 'recipient';
    return null;
};

/** Index of a status on the progress bar (unknown statuses count as the first step). */
export const stepIndex = (status) => {
    const i = XC_STEPS.findIndex((s) => s.toLowerCase() === (status || '').toLowerCase());
    return i >= 0 ? i : 0;
};

/** Whether the follow-up step shows: a follow-up note exists, or the status says so. */
export const hasFollowup = (xc) =>
    !!(xc.initiator_comment || xc.recipient_comment) || statusOf(xc) === XC_FOLLOWUP_STATUS;

/**
 * The AI persona label belongs next to a person: a side that is a group
 * (alliance, project, sphere) is never labelled, even when a persona acted
 * for it, and "You" isn't either. `party` is a mapped participant
 * ({ name, kind, isAgent }).
 */
export const showsPersonaTag = (party) =>
    !!party && typeof party === 'object' && !!party.isAgent
    && (!party.kind || party.kind === 'user') && party.name !== 'You';
