// An opening in more spheres than its own.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import api from '../api';
import { useEntityList, useInvalidate } from '../utils/queries';
import { shareChoices } from '../utils/sharing';
import '../styles/Sharing.css';

/** Which spheres, as tick boxes. */
export function SharePicker({ choices, value, onChange }) {
    const toggle = (id) => onChange(value.includes(id) ? value.filter((v) => v !== id) : [...value, id]);
    return (
        <fieldset className="share-picker">
            <legend>Share it with your other spheres too</legend>
            {choices.map((s) => (
                <label key={s.id} className="share-choice">
                    <input type="checkbox" checked={value.includes(s.id)} onChange={() => toggle(s.id)} />
                    <span>{s.name}</span>
                </label>
            ))}
            <p className="share-note">
                People there will see the opening, who posted it and which sphere it comes from. Never that sphere&rsquo;s
                other people.
            </p>
        </fieldset>
    );
}

SharePicker.propTypes = { choices: PropTypes.array.isRequired, value: PropTypes.array.isRequired, onChange: PropTypes.func.isRequired };

/** On an opening's page: where else it is, and changing that for whoever runs it. */
export function ShareOpening({ opening, userId, isOwn, canEdit, onSaved }) {
    const [value, setValue] = useState(null);       // null: not changing it
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState('');
    const invalidate = useInvalidate();
    const already = opening.sharedWith || [];
    const mayChange = canEdit && !!opening.sphereId;
    const spheres = useEntityList('sphere', { enabled: mayChange && isOwn });
    const choices = mayChange
        ? shareChoices(spheres.data, { homeId: opening.sphereId, userId, isDemo: opening.isDemo, already, mayAdd: isOwn })
        : [];
    if (!already.length && !choices.length) return null;

    const save = async () => {
        setBusy(true);
        setProblem('');
        try {
            await api.post(`/api/openings/${opening.id}/spheres`, { sphere_ids: value });
            setValue(null);
            invalidate.openings();
            await onSaved();
        } catch (err) {
            setProblem(err.response?.data?.message || "That didn't save. Please try again.");
        }
        setBusy(false);
    };

    return (
        <div className="xc-sidebar-card share-card">
            <p className="xc-sidebar-heading">{already.length ? 'Also shared with' : 'Sharing'}</p>
            {value === null ? (
                <>
                    {already.length > 0 && (
                        <ul className="share-list">
                            {already.map((s) => <li key={s.id}><Link to={`/sphere?id=${s.id}`}>{s.name}</Link></li>)}
                        </ul>
                    )}
                    {choices.length > 0 && (
                        <button type="button" className="share-btn" onClick={() => setValue(already.map((s) => String(s.id)))}>
                            {already.length ? 'Change' : 'Share with more spheres'}
                        </button>
                    )}
                </>
            ) : (
                <>
                    <SharePicker choices={choices} value={value} onChange={setValue} />
                    {problem && <p className="share-problem" role="alert">{problem}</p>}
                    <div className="share-actions">
                        <button type="button" className="share-btn share-btn--main" onClick={save} disabled={busy}>
                            {busy ? 'Saving…' : 'Save'}
                        </button>
                        <button type="button" className="share-btn" onClick={() => { setValue(null); setProblem(''); }} disabled={busy}>
                            Cancel
                        </button>
                    </div>
                </>
            )}
        </div>
    );
}

ShareOpening.propTypes = {
    opening: PropTypes.object.isRequired,
    userId: PropTypes.string,
    isOwn: PropTypes.bool,
    canEdit: PropTypes.bool,
    onSaved: PropTypes.func.isRequired,
};
