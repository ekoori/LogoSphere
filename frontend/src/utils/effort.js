// How long help took, as a receipt says it (backend: routes/meaning_trail.py, effort_hours).

/** "About 2 hours", "About 45 minutes": never a score, only what the receipt said. */
export function hoursGiven(hours, { short = false } = {}) {
    const h = Number(hours);
    if (!Number.isFinite(h) || h <= 0) return '';
    if (short) return h < 1 ? `${Math.round(h * 60)} min` : `${+h.toFixed(2)} h`;
    if (h < 1) return `About ${Math.round(h * 60)} minutes`;
    return `About ${+h.toFixed(2)} hour${h === 1 ? '' : 's'}`;
}
