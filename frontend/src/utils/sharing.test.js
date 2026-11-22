import { describe, expect, it } from 'vitest';
import { inSphere, loanLabel, shareChoices } from './sharing';

const member = [{ id: 'me', role: 'member' }];
const spheres = [
    { sphere_id: 'home', name: 'Home', members: member },
    { sphere_id: 'hill', name: 'Hill', members: member },
    { sphere_id: 'demo', name: 'Demo', members: member, is_demo: true },
    { sphere_id: 'asked', name: 'Asked', members: [{ id: 'me', role: 'pending' }] },
    { sphere_id: 'theirs', name: 'Theirs', members: [] },
];

describe('shareChoices', () => {
    it("offers the viewer's other spheres on the same side of demo and real", () => {
        expect(shareChoices(spheres, { homeId: 'home', userId: 'me', isDemo: false }).map((s) => s.id)).toEqual(['hill']);
        expect(shareChoices(spheres, { homeId: 'other', userId: 'me', isDemo: true }).map((s) => s.id)).toEqual(['demo']);
    });
    it('keeps what it is shared with, to take back', () => {
        const opts = { homeId: 'home', userId: 'me', isDemo: false, already: [{ id: 'theirs', name: 'Theirs' }] };
        expect(shareChoices(spheres, opts).map((s) => s.id)).toEqual(['hill', 'theirs']);
        expect(shareChoices(spheres, { ...opts, mayAdd: false }).map((s) => s.id)).toEqual(['theirs']);
    });
    it('has nothing to offer when it is for everyone', () => {
        expect(shareChoices(spheres, { homeId: null, userId: 'me', isDemo: false })).toEqual([]);
    });
});

describe('inSphere', () => {
    it('is its own sphere or one it was shared with', () => {
        const opening = { sphereId: 'home', sharedWith: [{ id: 'hill' }] };
        expect(['home', 'hill', 'theirs', null].map((id) => inSphere(opening, id))).toEqual([true, true, false, false]);
    });
});

describe('loanLabel', () => {
    it('says which way', () => {
        expect([loanLabel('offer'), loanLabel('need')]).toEqual(['To lend', 'To borrow']);
    });
});
