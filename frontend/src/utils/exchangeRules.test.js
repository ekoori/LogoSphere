import { describe, expect, it } from 'vitest';
import { awaitingReceipt, canCancel, hasFollowup, isCancelled, nextStatus, stepIndex } from './exchangeRules';

const xc = (status, extra = {}) => ({ exchange_status: status, ...extra });

describe('nextStatus', () => {
    it('moves Initiated -> In Progress -> Finished by hand', () => {
        expect(nextStatus(xc('Initiated'))).toBe('In Progress');
        expect(nextStatus(xc(undefined))).toBe('In Progress');
        expect(nextStatus(xc('In Progress'))).toBe('Finished');
    });

    it('never offers Receipted: adding the receipt reaches it (the server refuses Finished -> Receipted)', () => {
        expect(nextStatus(xc('Finished'))).toBeNull();
        expect(nextStatus(xc('Receipted'))).toBeNull();
        expect(nextStatus(xc('Additional Comments Added'))).toBeNull();
    });

    it('offers nothing once cancelled', () => {
        expect(isCancelled(xc('Cancelled'))).toBe(true);
        expect(nextStatus(xc('Cancelled'))).toBeNull();
    });
});

describe('canCancel', () => {
    it('is the initiator\'s, before the exchange is finished', () => {
        expect(canCancel(xc('Initiated'), true)).toBe(true);
        expect(canCancel(xc('In Progress'), true)).toBe(true);
        expect(canCancel(xc('Finished'), true)).toBe(false);
        expect(canCancel(xc('Receipted'), true)).toBe(false);
        expect(canCancel(xc('Cancelled'), true)).toBe(false);
        expect(canCancel(xc('Initiated'), false)).toBe(false);
    });
});

describe('progress', () => {
    it('places statuses on the bar', () => {
        expect(stepIndex('Initiated')).toBe(0);
        expect(stepIndex('in progress')).toBe(1);
        expect(stepIndex('Receipted')).toBe(3);
        expect(stepIndex('Something else')).toBe(0);
    });

    it('waits for the receipt once finished', () => {
        expect(awaitingReceipt(xc('Finished'))).toBe(true);
        expect(awaitingReceipt(xc('Finished', { gratitude_comment: 'Thanks' }))).toBe(false);
        expect(awaitingReceipt(xc('In Progress'))).toBe(false);
    });

    it('shows the follow-up step only when there is one', () => {
        expect(hasFollowup(xc('Receipted'))).toBe(false);
        expect(hasFollowup(xc('Receipted', { recipient_comment: 'Still grateful' }))).toBe(true);
        expect(hasFollowup(xc('Additional Comments Added'))).toBe(true);
    });
});
