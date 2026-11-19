// Dates from the API.
//
// The server sends UTC datetimes without a zone ("2026-11-18T20:52:14.416000").
// `new Date()` reads such a string as *local* time, so in Melbourne a
// notification written a minute ago showed as "11h ago", and a day label could
// land on the wrong side of midnight. Read zone-less datetimes as UTC; anything
// that names its zone ("…Z", "+10:00", "… GMT") is taken as written.
const ZONELESS = /^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}(?::\d{2})?)(\.\d+)?$/;

export function parseServerDate(value) {
    if (value === null || value === undefined || value === '') return null;
    if (value instanceof Date) return isNaN(value.getTime()) ? null : value;
    let text = String(value).trim();
    const m = ZONELESS.exec(text);
    // Milliseconds are as fine as Date parsing reliably goes (Python sends micros).
    if (m) text = `${m[1]}T${m[2]}${m[3] ? m[3].slice(0, 4) : ''}Z`;
    const d = new Date(text);
    return isNaN(d.getTime()) ? null : d;
}

// "5 Jul 2026" (or "5 Jul" with { year: false }); '' when there's no date.
export function formatServerDate(value, { year = true, fallback = '' } = {}) {
    const d = parseServerDate(value);
    if (!d) return fallback;
    return d.toLocaleDateString(undefined, year
        ? { month: 'short', day: 'numeric', year: 'numeric' }
        : { month: 'short', day: 'numeric' });
}

// "just now", "5m ago", "3h ago", "2d ago", then the date.
export function timeAgo(value, now = Date.now()) {
    const d = parseServerDate(value);
    if (!d) return '';
    const mins = Math.floor((now - d.getTime()) / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return formatServerDate(d, { year: false });
}
