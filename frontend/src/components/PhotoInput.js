// Photos for a receipt: choose some, or on a phone or tablet take one. Adds up
// to `max`. There is deliberately no AI option here: a receipt is evidence.
import React, { useEffect, useMemo, useRef } from 'react';
import PropTypes from 'prop-types';

const touchScreen = () => !!window.matchMedia?.('(pointer: coarse)').matches;

export default function PhotoInput({ photos, onChange, max = 3 }) {
    const choose = useRef(null);
    const take = useRef(null);
    const previews = useMemo(() => photos.map((p) => URL.createObjectURL(p)), [photos]);
    useEffect(() => () => previews.forEach((u) => URL.revokeObjectURL(u)), [previews]);

    const add = (e) => {
        const picked = Array.from(e.target.files || []);
        e.target.value = '';
        if (picked.length) onChange([...photos, ...picked].slice(0, max));
    };
    const full = photos.length >= max;

    return (
        <div className="xc-photo-input">
            {photos.length > 0 && (
                <ul className="xc-photo-previews">
                    {previews.map((url, i) => (
                        <li key={url}>
                            <img src={url} alt={`Receipt ${i + 1} to upload`} />
                            <button type="button" aria-label={`Remove photo ${i + 1}`}
                                    onClick={() => onChange(photos.filter((_, j) => j !== i))}>×</button>
                        </li>
                    ))}
                </ul>
            )}
            <div className="xc-photo-buttons">
                {touchScreen() && (
                    <button type="button" className="btn btn-ghost" disabled={full} onClick={() => take.current.click()}>
                        Take a photo
                    </button>
                )}
                <button type="button" className="btn btn-ghost" disabled={full} onClick={() => choose.current.click()}>
                    Choose photos
                </button>
            </div>
            <input ref={take} type="file" accept="image/*" capture="environment" hidden onChange={add} />
            <input ref={choose} type="file" accept="image/*" multiple hidden onChange={add} />
        </div>
    );
}

PhotoInput.propTypes = {
    photos: PropTypes.array.isRequired,
    onChange: PropTypes.func.isRequired,
    max: PropTypes.number,
};
