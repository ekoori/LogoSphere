// An event's times in words (backend app/utils/recurrence.py decides them).
// They are shown on the event's own clock: that is the one on the hall's wall.
import { parseServerDate } from './dates';

export const GOING = 'going';
export const MAYBE = 'maybe';
export const CANT = 'no';
export const ANSWERS = [[GOING, 'Going'], [MAYBE, 'Maybe'], [CANT, "Can't"]];
export const REPEATS = ['never', 'weekly', 'fortnightly', 'monthly', 'monthly_weekday'];

const LENGTHS = [30, 60, 90, 120, 150, 180, 240, 300, 360, 480, 720, 1440, 2880, 4320, 10080];
const NTH = ['first', 'second', 'third', 'fourth', 'last'];

export function deviceZone() {
    try {
        const zone = Intl.DateTimeFormat().resolvedOptions().timeZone;
        return zone && zone !== 'Etc/Unknown' ? zone : 'UTC';
    } catch (_) {
        return 'UTC';
    }
}

/** Every zone this browser knows, and `chosen` whether it does or not. */
export function zoneChoices(chosen) {
    let known = [];
    try {
        known = Intl.supportedValuesOf('timeZone');
    } catch (_) { /* an older browser: its own zone will do */ }
    return [...new Set([chosen, deviceZone(), 'UTC', ...known])].filter(Boolean).sort();
}

function dayParts(day) {
    const found = /^(\d{4})-(\d{2})-(\d{2})$/.exec(day || '');
    return found ? { year: +found[1], month: +found[2], date: +found[3] } : null;
}

/** "19th" */
export function ordinal(n) {
    const tens = n % 100;
    if (tens >= 11 && tens <= 13) return `${n}th`;
    return `${n}${['th', 'st', 'nd', 'rd'][n % 10] || 'th'}`;
}

/** What "repeats" means for an event that first happens on `day`. */
export function repeatText(repeats, day) {
    if (!repeats || repeats === 'never') return "Doesn't repeat";
    const parts = dayParts(day);
    if (!parts) {
        return {
            weekly: 'Every week', fortnightly: 'Every two weeks', monthly: 'Every month, same date',
            monthly_weekday: 'Every month, same day of the week',
        }[repeats] || '';
    }
    const weekday = new Date(Date.UTC(parts.year, parts.month - 1, parts.date))
        .toLocaleDateString('en', { weekday: 'long', timeZone: 'UTC' });
    if (repeats === 'weekly') return `Every ${weekday}`;
    if (repeats === 'fortnightly') return `Every second ${weekday}, fortnightly`;
    if (repeats === 'monthly') {
        return `Every month on the ${ordinal(parts.date)}${parts.date > 28 ? ", or the month's last day" : ''}`;
    }
    if (repeats === 'monthly_weekday') return `Every month on the ${NTH[Math.floor((parts.date - 1) / 7)]} ${weekday}`;
    return '';
}

export function lengthText(minutes) {
    if (minutes % 1440 === 0) return minutes === 1440 ? '1 day' : `${minutes / 1440} days`;
    const hours = Math.floor(minutes / 60);
    const over = minutes % 60;
    if (!hours) return `${minutes} minutes`;
    if (over === 30) return `${hours}½ hours`;
    return `${hours} ${hours === 1 ? 'hour' : 'hours'}${over ? ` ${over} minutes` : ''}`;
}

export const lengthChoices = (current) => [...new Set([...LENGTHS, current].filter(Boolean))].sort((a, b) => a - b);

/** The date tile: {date: "24", month: "Nov"}. */
export function tileOf(day, locale = undefined) {
    const parts = dayParts(day);
    if (!parts) return { date: '', month: '' };
    return {
        date: String(parts.date),
        month: new Date(Date.UTC(parts.year, parts.month - 1, parts.date))
            .toLocaleDateString(locale, { month: 'short', timeZone: 'UTC' }),
    };
}

function formatted(date, options, locale, timeZone) {
    try {
        return new Intl.DateTimeFormat(locale, { ...options, timeZone }).format(date);
    } catch (_) {
        return new Intl.DateTimeFormat(locale, options).format(date);    // a zone this browser doesn't know
    }
}

/**
 * "Tue 24 Nov, 19:00–21:00", on the event's clock; `zoneNote` names that clock
 * when the reader's shows something else.
 */
export function whenText(time, tz, { locale = undefined, viewerZone = deviceZone(), now = new Date() } = {}) {
    const start = parseServerDate(time?.starts_at);
    const end = parseServerDate(time?.ends_at);
    if (!start) return { text: '', zoneNote: '' };
    const dayOptions = { weekday: 'short', day: 'numeric', month: 'short' };
    if (start.getFullYear() !== now.getFullYear()) dayOptions.year = 'numeric';
    const day = (d) => formatted(d, dayOptions, locale, tz);
    const clock = (d, zone = tz) => formatted(d, { hour: '2-digit', minute: '2-digit', hourCycle: 'h23' }, locale, zone);

    let text = `${day(start)}, ${clock(start)}`;
    if (end) text += day(end) === day(start) ? `–${clock(end)}` : ` – ${day(end)}, ${clock(end)}`;
    const whole = { day: 'numeric', hour: '2-digit', minute: '2-digit', hourCycle: 'h23' };
    const differs = formatted(start, whole, locale, tz) !== formatted(start, whole, locale, viewerZone);
    return { text, zoneNote: differs ? `${tz.replace(/_/g, ' ')} time` : '' };
}

export const hasEnded = (time, now = Date.now()) => (parseServerDate(time?.ends_at)?.getTime() ?? Infinity) <= now;

export function comingText(time) {
    const bits = [];
    if (time?.going) bits.push(`${time.going} going`);
    if (time?.maybe) bits.push(`${time.maybe} maybe`);
    return bits.join(' · ');
}
