import { describe, expect, it } from 'vitest';
import { project, squareAround, tilesFor, unproject, zoomFor } from './mercator';
import { linkedTo, samePlace, toPayload, withWords } from './places';

describe('the map', () => {
    it('there and back again', () => {
        [[-37.7689, 145.0432], [64.1466, -21.9426], [0, 0]].forEach(([lat, lon]) => {
            const p = project(lat, lon, 13);
            const back = unproject(p.x, p.y, 13);
            expect(back.lat).toBeCloseTo(lat, 5);
            expect(back.lon).toBeCloseTo(lon, 5);
        });
    });

    it('covers the window and wraps sideways', () => {
        const tiles = tilesFor({ lat: 0, lon: 179.9, z: 3 }, 600, 300);
        expect(Math.min(...tiles.map((t) => t.left))).toBeLessThanOrEqual(0);
        expect(Math.max(...tiles.map((t) => t.left + 256))).toBeGreaterThanOrEqual(600);
        tiles.forEach((t) => {
            const [z, x, y] = t.path.split('/').map(Number);
            expect(z).toBe(3);
            expect(x >= 0 && x < 8 && y >= 0 && y < 8).toBe(true);
        });
    });

    it("draws the server's square", () => {
        // app/utils/geo.py: square_centre works the same way.
        const step = 1 / 111.32;
        const s = squareAround(-37.768934, 145.04321, 1);
        expect(s.lat).toBeCloseTo((Math.floor(-37.768934 / step) + 0.5) * step, 8);
        expect(Math.abs(s.lat + 37.768934)).toBeLessThanOrEqual(step / 2 + 1e-9);
        expect(Math.abs(s.lon - 145.04321)).toBeLessThanOrEqual(s.dLon / 2 + 1e-9);
        expect(zoomFor(null)).toBe(16);
        expect(zoomFor(100)).toBeLessThan(zoomFor(5));
    });
});

describe('a place', () => {
    const pin = { label: 'By the creek', lat: 1, lon: 2, precision: '1km' };
    const town = { label: 'Bigton', lat: 1, lon: 2, precision: 'town' };

    it('is sent as a pin, a search result, words, or nothing', () => {
        const exact = { ...pin, precision: 'exact' };
        expect(toPayload(exact)).toEqual(exact);
        expect(toPayload(pin).lat).not.toBe(pin.lat); // rounded before it leaves the device
        expect(toPayload(toPayload(pin))).toEqual(toPayload(pin)); // and stays put when rounded again
        expect(toPayload({ ...town, id: 7 })).toEqual({ id: 7, label: 'Bigton' });
        expect(toPayload({ label: ' The hills ' })).toEqual({ label: 'The hills' });
        expect(toPayload({ label: '' })).toBe(null);
        expect(toPayload(null)).toBe(null);
        expect(toPayload(town)).toBe(undefined); // stored earlier: unchanged
    });

    it('keeps a pin under new words, lets go of a town', () => {
        expect(withWords(pin, 'By the bridge')).toEqual({ ...pin, label: 'By the bridge' });
        expect(withWords(town, 'Smallton')).toEqual({ label: 'Smallton' });
    });

    it('knows when it changed', () => {
        expect(samePlace(null, { label: '' })).toBe(true);
        expect(samePlace(pin, { ...pin })).toBe(true);
        expect(samePlace(pin, { ...pin, precision: '5km' })).toBe(false);
    });

    it('says what it is linked to', () => {
        expect(linkedTo(pin)).toMatch('1 km');
        expect(linkedTo(town)).toMatch('town');
        expect(linkedTo({ label: 'x' })).toMatch("isn't on the map");
    });
});
