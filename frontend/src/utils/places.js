// A place as the forms hold it, and as it is sent (app/utils/places.py).
import { squareAround } from './mercator';

export const PIN_PRECISIONS = [
    { key: 'exact', km: null, label: 'The exact spot' },
    { key: '1km', km: 1, label: 'About 1 km' },
    { key: '5km', km: 5, label: 'About 5 km' },
    { key: '10km', km: 10, label: 'About 10 km (a town)' },
    { key: '100km', km: 100, label: 'About 100 km (a region)' },
];
export const NEAR_KM = [5, 10, 25, 50, 100, 250];

const NAMED = { postcode: 'postcode', town: 'town', region: 'region', country: 'country' };
const KEYS = PIN_PRECISIONS.map((p) => p.key);

export const hasPoint = (place) => typeof place?.lat === 'number' && typeof place?.lon === 'number';
export const isPin = (place) => hasPoint(place) && !NAMED[place.precision];
export const isNamed = (place) => hasPoint(place) && !!NAMED[place.precision];
export const squareKm = (precision) => PIN_PRECISIONS.find((p) => p.key === precision)?.km ?? null;
/** A country is on the map, but says nothing about what's near. */
export const canMeasure = (place) => hasPoint(place) && place.precision !== 'country';
export const isFiner = (next, was) => KEYS.indexOf(next) < KEYS.indexOf(was);

const sixPlaces = (x) => Math.round(x * 1e6) / 1e6;

/** A point no finer than `km`, so nothing more exact leaves the device than was chosen. */
export function coarsened(lat, lon, km) {
    const at = km ? squareAround(lat, lon, km) : { lat, lon };
    return { lat: sixPlaces(at.lat), lon: sixPlaces(at.lon) };
}

/** What it is linked to, in words. */
export function linkedTo(place) {
    if (isNamed(place)) {
        return place.precision === 'country'
            ? "On the map, as a country: too rough to show what's near"
            : `On the map, as a ${NAMED[place.precision]}`;
    }
    if (!isPin(place)) return place?.label?.trim() ? "Only words so far: it isn't on the map" : '';
    return place.precision === 'exact' ? 'On the map, at the exact spot' : `On the map, to about ${squareKm(place.precision)} km`;
}

/** Why it can't be saved yet, or null. */
export function placeProblem(place) {
    return isPin(place) && !place.label?.trim()
        ? 'Give the pin a name in a few words: that is what others see.'
        : null;
}

/**
 * The body's `place`. Undefined means "can't be sent again": a place from the
 * search that was stored earlier has no id any more, and is unchanged anyway.
 */
export function toPayload(place) {
    if (!place) return null;
    const label = (place.label || '').trim();
    if (place.id !== undefined && place.id !== null) return { id: place.id, label };
    if (isPin(place)) {
        return { ...coarsened(place.lat, place.lon, squareKm(place.precision)), precision: place.precision, label };
    }
    if (isNamed(place)) return undefined;
    return label ? { label } : null;
}

/** Typing over a place found by name lets go of its point: the words would no longer say it. */
export function withWords(place, label) {
    return isPin(place) ? { ...place, label } : { label };
}

export const samePlace = (one, other) => ['label', 'lat', 'lon', 'precision', 'id']
    .every((key) => (one?.[key] ?? null) === (other?.[key] ?? null) || (key === 'label' && !one?.label && !other?.label));
