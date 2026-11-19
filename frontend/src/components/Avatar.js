// Avatar — a small round user image that lazy-loads from /api/users/<id>/avatar
// and falls back to the person's initials when they have no picture (or it
// fails to load). Keeps avatar blobs out of JSON payloads: the browser fetches
// and caches each one via a plain <img>.
import React, { useState, useEffect } from 'react';
import '../styles/Avatar.css';

// The smaller copies the server makes of a picture (backend app/utils/pictures).
const SIDES = [160, 320, 640];

// The smallest copy that still looks sharp at `size` CSS pixels on this screen.
function sideFor(size) {
    const dpr = typeof window !== 'undefined' ? Math.min(window.devicePixelRatio || 1, 3) : 2;
    return SIDES.find((s) => s >= size * dpr);
}

export default function Avatar({ userId, name = '', size = 24, className = '' }) {
    const [failed, setFailed] = useState(false);
    // Reset the error state if the id changes (list re-use).
    useEffect(() => { setFailed(false); }, [userId]);

    // Words that start with a letter or digit: "Bruce (AI)" is B, not "B(".
    const initials = (name || '').trim().split(/\s+/).filter((w) => /^[\p{L}\p{N}]/u.test(w))
        .map((w) => w[0]).slice(0, 2).join('').toUpperCase() || '?';
    const style = { width: size, height: size, fontSize: Math.round(size * 0.42) };

    if (!userId || failed) {
        return (
            <span className={`avatar avatar--initials ${className}`} style={style} aria-hidden="true">
                {initials}
            </span>
        );
    }
    return (
        <img
            className={`avatar ${className}`}
            style={style}
            src={`/api/users/${userId}/avatar${sideFor(size) ? `?size=${sideFor(size)}` : ''}`}
            alt=""
            loading="lazy"
            onError={() => setFailed(true)}
        />
    );
}
