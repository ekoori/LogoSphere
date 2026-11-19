import { describe, expect, it } from 'vitest';
import { fmtDate, imageForService, mapExchange, mapService } from './mappers';

const ME = 'me-id';
const STEVE = 'steve-id';

const row = (extra = {}) => ({
    exchange_id: 'x1', exchange_description: 'Fence rebuild', exchange_status: 'Initiated',
    initiator_id: ME, initiator_name: 'Joe Rogan', initiator_kind: 'user',
    other_user_id: STEVE, other_user_name: 'Steve Wozniak', other_kind: 'user',
    viewer_is_initiator: true, likes: {}, ...extra,
});

describe('mapExchange', () => {
    it('names the trail owner "You" on their own trail', () => {
        const x = mapExchange(row(), { ownerId: ME });
        expect(x.participants.map((p) => p.name)).toEqual(['You', 'Steve Wozniak']);
        expect(x.participants[1].id).toBe(STEVE);
    });

    it('keeps the order initiator -> recipient when the owner received', () => {
        const x = mapExchange(row({ viewer_is_initiator: false, initiator_id: STEVE, initiator_name: 'Steve Wozniak',
            other_user_id: ME, other_user_name: 'Joe Rogan' }), { ownerId: ME });
        expect(x.participants.map((p) => p.name)).toEqual(['Steve Wozniak', 'You']);
    });

    it('says who acted for a group', () => {
        const x = mapExchange(row({ other_kind: 'alliance', other_user_id: 'a1', other_user_name: 'Repair Café',
            recipient_acting_user_id: 'marie-id', recipient_acting_user_name: 'Marie Kondo' }), { ownerId: ME });
        expect(x.participants[1]).toEqual({ name: 'Marie Kondo on behalf of Repair Café', id: 'a1', kind: 'alliance' });
    });

    it('attributes the receipt to the recipient and the note to the initiator', () => {
        const x = mapExchange(row({ gratitude_comment: 'Thank you', user_comment: 'Glad to help' }), { ownerId: ME });
        expect(x.receipts.map((r) => [r.author, r.commentType])).toEqual([
            ['Steve Wozniak', 'gratitude'], ['You', 'user']]);
    });

    it('reads likes by what was liked', () => {
        const x = mapExchange(row({ likes: { exchange: { count: 2, liked: true, by: [{ id: STEVE }] } } }));
        expect(x.likesCount).toBe(2);
        expect(x.likedByCurrentUser).toBe(true);
    });

    it('treats settled statuses as completed', () => {
        expect(mapExchange(row({ exchange_status: 'Receipted' })).type).toBe('completed');
        expect(mapExchange(row({ exchange_status: 'In Progress' })).type).toBe('offer');
    });
});

describe('mapService', () => {
    const service = (extra = {}) => ({
        service_id: 's1', title: 'Spare GPU hours', type: 'offer', status: 'Posted', cadence: 'single',
        provider: 'Joe Rogan', provider_id: ME, sphere_id: 'sp1', spheres: ['AI Commons'], likes: 3, ...extra,
    });

    it('links the sphere by id', () => {
        expect(mapService(service()).spheres).toEqual([{ id: 'sp1', name: 'AI Commons' }]);
    });

    it('prefers an uploaded banner over the bundled illustration', () => {
        expect(mapService(service({ has_image: true })).imageUrl).toBe('/api/openings/s1/image');
        expect(mapService(service()).imageUrl).toBe(imageForService(undefined, 'Spare GPU hours'));
    });

    it('carries the viewer-relative flags and acceptances', () => {
        const s = mapService(service({ is_provider: true, can_manage: true,
            pending_acceptances: [{ accepter_id: STEVE }], my_acceptance: null }));
        expect(s.isProvider).toBe(true);
        expect(s.canManage).toBe(true);
        expect(s.pendingAcceptances).toHaveLength(1);
        expect(s.likesCount).toBe(3);
    });
});

describe('formatting', () => {
    it('formats dates and tolerates junk', () => {
        expect(fmtDate('2026-06-02T10:00:00')).not.toBe('');
        expect(fmtDate('not a date')).toBe('');
        expect(fmtDate(null)).toBe('');
    });

    it('picks an illustration from the title', () => {
        expect(imageForService(null, 'H100 compute share')).toBe('/static/h100_cpus.webp');
        expect(imageForService('garden', 'anything')).toBe('/static/garden_old.webp');
        expect(imageForService(null, 'something else')).toBe('/static/gift_economy.png');
    });
});
