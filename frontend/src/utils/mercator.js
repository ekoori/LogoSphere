// Map arithmetic for the small map (components/SlippyMap.js): Web Mercator in
// 256 px tiles, and the square a pin is rounded to (app/utils/geo.py's twin,
// so the square drawn is the one that will be stored).
export const TILE = 256;
export const MIN_ZOOM = 2;
export const MAX_ZOOM = 18;
const MAX_LAT = 85.05112878;
const KM_A_DEGREE = 111.32;
const rad = (deg) => (deg * Math.PI) / 180;
const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));

/** A point in world pixels at a zoom. */
export function project(lat, lon, z) {
    const size = TILE * 2 ** z;
    const phi = rad(clamp(lat, -MAX_LAT, MAX_LAT));
    return {
        x: ((lon + 180) / 360) * size,
        y: ((1 - Math.log(Math.tan(phi) + 1 / Math.cos(phi)) / Math.PI) / 2) * size,
    };
}

export function unproject(x, y, z) {
    const size = TILE * 2 ** z;
    const t = Math.PI * (1 - (2 * clamp(y, 0, size)) / size);
    const around = ((x / size) % 1 + 1) % 1; // the world repeats sideways
    return { lat: (Math.atan(Math.sinh(t)) * 180) / Math.PI, lon: around * 360 - 180 };
}

/** The tiles covering a width x height window about the centre. */
export function tilesFor(view, width, height) {
    const n = 2 ** view.z;
    const centre = project(view.lat, view.lon, view.z);
    const left = centre.x - width / 2;
    const top = centre.y - height / 2;
    const out = [];
    for (let col = Math.floor(left / TILE); col * TILE < left + width; col += 1) {
        for (let row = Math.max(0, Math.floor(top / TILE)); row * TILE < top + height && row < n; row += 1) {
            out.push({
                key: `${view.z}/${col}/${row}`,
                path: `${view.z}/${((col % n) + n) % n}/${row}`,
                left: Math.round(col * TILE - left),
                top: Math.round(row * TILE - top),
            });
        }
    }
    return out;
}

/** The centre and spans (degrees) of the km-square a point is rounded into. */
export function squareAround(lat, lon, km) {
    const step = km / KM_A_DEGREE;
    const centreLat = clamp((Math.floor(lat / step) + 0.5) * step, -89.9, 89.9);
    const stepLon = Math.min(360, step / Math.cos(rad(centreLat)));
    const centreLon = Math.min(180, (Math.floor((lon + 180) / stepLon) + 0.5) * stepLon - 180);
    return { lat: centreLat, lon: centreLon, dLat: step, dLon: stepLon };
}

/** A zoom at which that square is easy to see. */
export function zoomFor(km) {
    if (!km) return 16;
    return clamp(Math.round(14.5 - Math.log2(km)), MIN_ZOOM, 16);
}
