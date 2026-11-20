// Light, dark, or whatever the device prefers. The choice is a per-browser
// convenience kept in localStorage (it isn't account data); index.html applies
// it before the first paint so a dark page never flashes light.
import { useEffect, useState } from 'react';

const KEY = 'logosphere-theme';
const EVENT = 'logosphere-theme';
export const THEME_CHOICES = [
    ['system', 'Same as your device'],
    ['light', 'Light'],
    ['dark', 'Dark'],
];

export function storedTheme() {
    try {
        const v = window.localStorage.getItem(KEY);
        return v === 'light' || v === 'dark' ? v : 'system';
    } catch (_) {
        return 'system';
    }
}

const deviceIsDark = () => !!(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches);

export function effectiveTheme(choice = storedTheme()) {
    if (choice === 'light' || choice === 'dark') return choice;
    return deviceIsDark() ? 'dark' : 'light';
}

function apply(choice) {
    const root = document.documentElement;
    if (choice === 'light' || choice === 'dark') root.dataset.theme = choice;
    else delete root.dataset.theme;
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.setAttribute('content', effectiveTheme(choice) === 'dark' ? '#171c13' : '#46583a');
}

export function setTheme(choice) {
    try {
        if (choice === 'system') window.localStorage.removeItem(KEY);
        else window.localStorage.setItem(KEY, choice);
    } catch (_) { /* private mode: it still applies for this page */ }
    apply(choice);
    window.dispatchEvent(new Event(EVENT));
}

/** { choice, effective, setTheme } — follows changes made elsewhere and the device's setting. */
export function useTheme() {
    const [choice, setChoice] = useState(storedTheme);
    const [effective, setEffective] = useState(() => effectiveTheme());
    useEffect(() => {
        const sync = () => {
            const c = storedTheme();
            setChoice(c);
            setEffective(effectiveTheme(c));
            apply(c);
        };
        sync();
        window.addEventListener(EVENT, sync);
        const mq = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null;
        if (mq && mq.addEventListener) mq.addEventListener('change', sync);
        return () => {
            window.removeEventListener(EVENT, sync);
            if (mq && mq.removeEventListener) mq.removeEventListener('change', sync);
        };
    }, []);
    return { choice, effective, setTheme };
}
