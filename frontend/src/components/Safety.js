// Blocking and reporting, small wherever they appear. Nobody reported or
// blocked is told.
import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { useQueryClient } from '@tanstack/react-query';
import api from '../api';
import '../styles/Messages.css';

const said = (err, fallback) => err.response?.data?.message || fallback;

/** "Report": opens a few lines to send to the administrators. */
export function ReportButton({ report, label = 'Report', noteRequired = false, about = '' }) {
    const [open, setOpen] = useState(false);
    const [note, setNote] = useState('');
    const [busy, setBusy] = useState(false);
    const [done, setDone] = useState('');
    const [error, setError] = useState('');

    // A button inside someone else's form, so never a <form> of its own.
    const send = async () => {
        setBusy(true);
        setError('');
        try {
            setDone((await api.post('/api/reports', { ...report, note: note.trim() })).data.message);
        } catch (err) {
            setError(said(err, "That didn't send. Please try again."));
        }
        setBusy(false);
    };

    if (done) return <span className="safe-said" role="status">{done}</span>;
    if (!open) {
        return <button type="button" className="safe-link" onClick={(e) => { e.stopPropagation(); setOpen(true); }}>{label}</button>;
    }
    return (
        <div className="safe-report" onClick={(e) => e.stopPropagation()}>
            <textarea rows={2} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)} autoFocus
                      aria-label="What is wrong"
                      placeholder={noteRequired ? 'What happened?' : 'What is wrong? (optional)'} />
            <p className="safe-about">{about || <>Only the platform&rsquo;s administrators see it. The person isn&rsquo;t told.</>}</p>
            {error && <p className="safe-error" role="alert">{error}</p>}
            <div className="safe-buttons">
                <button type="button" className="safe-btn" onClick={send} disabled={busy || (noteRequired && !note.trim())}>
                    {busy ? 'Sending…' : 'Send the report'}
                </button>
                <button type="button" className="safe-link" onClick={() => setOpen(false)}>Cancel</button>
            </div>
        </div>
    );
}

ReportButton.propTypes = {
    report: PropTypes.object.isRequired, label: PropTypes.string, noteRequired: PropTypes.bool, about: PropTypes.string,
};

/** Block (asks twice) or unblock. */
export function BlockButton({ personId, blocked, onChanged }) {
    const client = useQueryClient();
    const [armed, setArmed] = useState(false);
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    const press = async () => {
        if (!blocked && !armed) {
            setArmed(true);
            return;
        }
        setBusy(true);
        setError('');
        try {
            await api.post(`/api/blocks/${personId}`, { blocked: !blocked });
            setArmed(false);
            client.invalidateQueries();     // who's near, messages and follows all follow from it
            if (onChanged) await onChanged();
        } catch (err) {
            setError(said(err, "That didn't work. Please try again."));
        }
        setBusy(false);
    };

    return (
        <span className="safe-block">
            <button type="button" className={`safe-link ${armed ? 'is-danger' : ''}`} onClick={press} disabled={busy}
                    onBlur={() => setArmed(false)}>
                {blocked ? 'Unblock' : armed ? 'Really block them?' : 'Block'}
            </button>
            {armed && <span className="safe-about">No messages or follows either way. They aren&rsquo;t told.</span>}
            {error && <span className="safe-error" role="alert">{error}</span>}
        </span>
    );
}

BlockButton.propTypes = { personId: PropTypes.string.isRequired, blocked: PropTypes.bool, onChanged: PropTypes.func };

/** Settings: whom you blocked. */
export function BlockedPeople() {
    const [rows, setRows] = useState(null);
    const [failed, setFailed] = useState(false);
    useEffect(() => {
        api.get('/api/blocks').then((r) => setRows(r.data)).catch(() => setFailed(true));
    }, []);

    return (
        <section id="blocked" className="settings-card place-anchor">
            <h3>People you blocked</h3>
            <p className="settings-sub">
                While a block stands you can&rsquo;t message, follow, take up each other&rsquo;s openings, acknowledge on
                each other&rsquo;s trails, or find each other nearby. They aren&rsquo;t told.
            </p>
            {failed && <p className="settings-msg settings-msg--err">That didn&rsquo;t load.</p>}
            {rows?.length === 0 && <p className="settings-hint">Nobody.</p>}
            {rows?.length > 0 && (
                <ul className="safe-blocked">
                    {rows.map((p) => (
                        <li key={p.id}>
                            <span>{p.name}</span>
                            <BlockButton personId={p.id} blocked onChanged={() => setRows((was) => was.filter((x) => x.id !== p.id))} />
                        </li>
                    ))}
                </ul>
            )}
        </section>
    );
}
