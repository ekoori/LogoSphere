// "Message everyone who responded": a private message to each, so respondents
// don't learn who else responded and answers come to the sender alone.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import api from '../api';
import '../styles/Messages.css';

export default function MessageRespondents({ openingId }) {
    const [open, setOpen] = useState(false);
    const [text, setText] = useState('');
    const [busy, setBusy] = useState(false);
    const [note, setNote] = useState(null);

    const send = async (e) => {
        e.preventDefault();
        setBusy(true);
        setNote(null);
        try {
            const { data } = await api.post(`/api/openings/${openingId}/message_respondents`, { text: text.trim() });
            const left = data.skipped ? ` ${data.skipped} couldn't be written to (AI personas don't read messages).` : '';
            setNote({ ok: true, text: `Sent to ${data.sent}, each privately: their answers come to you alone.${left}` });
            setText('');
            setOpen(false);
        } catch (err) {
            setNote({ ok: false, text: err.response?.data?.message || "That didn't send. Please try again." });
        }
        setBusy(false);
    };

    return (
        <div className="msg-respondents">
            {open ? (
                <form onSubmit={send}>
                    <textarea rows={3} maxLength={2000} value={text} onChange={(e) => setText(e.target.value)} autoFocus
                              aria-label="Message to everyone who responded" placeholder="Write to everyone who responded…" />
                    <p className="safe-about">Each gets it privately. They don&rsquo;t see who else responded.</p>
                    <div className="safe-buttons">
                        <button type="submit" className="safe-btn" disabled={busy || !text.trim()}>
                            {busy ? 'Sending…' : 'Send to each'}
                        </button>
                        <button type="button" className="safe-link" onClick={() => setOpen(false)}>Cancel</button>
                    </div>
                </form>
            ) : (
                <button type="button" className="xc-action-btn" onClick={() => { setOpen(true); setNote(null); }}>
                    Message everyone who responded
                </button>
            )}
            {note && <p className={note.ok ? 'safe-said' : 'safe-error'} role="status">{note.text}</p>}
        </div>
    );
}

MessageRespondents.propTypes = { openingId: PropTypes.string.isRequired };
