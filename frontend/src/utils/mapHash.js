// "#lat,lon,km" (any of it may be left out) for the app's map page.
export function coordinatesFromHash(hash) {
    const [a, b, c] = (hash || '').replace(/^#/, '').split(',');
    const number = (text) => (text && Number.isFinite(Number(text)) ? Number(text) : null);
    const lat = number(a);
    const lon = number(b);
    const km = number(c);
    const onEarth = lat !== null && lon !== null && Math.abs(lat) <= 90 && Math.abs(lon) <= 180;
    return { lat: onEarth ? lat : null, lon: onEarth ? lon : null, km: km && km > 0 && km <= 100 ? km : null };
}
