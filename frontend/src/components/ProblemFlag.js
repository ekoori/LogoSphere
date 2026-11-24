// The little flag in the header, on every page: a few words about a problem for the
// administrators, with the page it was on. The server files it in Cassandra with the other
// reports (POST /api/problems), signed in or not. The app has the same flag on every screen.
import React, { useEffect, useRef, useState } from 'react';
import PropTypes from 'prop-types';
import { useLocation } from 'react-router-dom';
import api from '../api';
import '../styles/ProblemFlag.css';

// The server knows the same list.
const KINDS = ["Doesn't work", 'Confusing', 'Wrong or missing', 'An idea', 'Other'];
const said = (err, fallback) => err.response?.data?.message || fallback;

// In the header on wide screens; in the menu drawer (asMenuItem) on phones, where the header has no room.
export default function ProblemFlag({ signedIn = false, asMenuItem = false, className = '' }) {
    const { pathname, search } = useLocation();
    const [attached, setAttached] = useState(null);     // read when the flag was pressed
    const [kind, setKind] = useState('');
    const [note, setNote] = useState('');
    const [busy, setBusy] = useState(false);
    const [done, setDone] = useState('');
    const [error, setError] = useState('');
    const [showAttached, setShowAttached] = useState(false);
    const box = useRef(null);

    useEffect(() => {
        if (!attached) return undefined;
        const away = (e) => { if (box.current && !box.current.contains(e.target)) setAttached(null); };
        const escape = (e) => { if (e.key === 'Escape') setAttached(null); };
        document.addEventListener('mousedown', away);
        document.addEventListener('keydown', escape);
        return () => {
            document.removeEventListener('mousedown', away);
            document.removeEventListener('keydown', escape);
        };
    }, [attached]);

    const open = () => {
        // Never the address's #part: password and invitation links carry their tokens there.
        setAttached({ page: pathname + search, app: 'LogoSphere website', browser: navigator.userAgent.slice(0, 200) });
        setKind('');
        setNote('');
        setDone('');
        setError('');
        setShowAttached(false);
    };

    const send = async () => {
        setBusy(true);
        setError('');
        try {
            const res = await api.post('/api/problems', { category: kind || 'Other', note: note.trim(), context: attached });
            setDone(res.data.message);
            setNote('');
        } catch (err) {
            setError(said(err, "That didn't send. Please try again."));
        }
        setBusy(false);
    };

    return (
        <div className={['problem-flag', asMenuItem && 'problem-flag--menu', className].filter(Boolean).join(' ')} ref={box}>
            <button type="button" className={asMenuItem ? 'nav-drawer-theme' : 'problem-flag-btn'}
                    onClick={() => (attached ? setAttached(null) : open())}
                    aria-label="Report a problem" title="Report a problem" aria-expanded={!!attached}>
                <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">
                    <path d="M5 21V4M5 4h11l-2 4 2 4H5" fill="none" stroke="currentColor" strokeWidth="1.8"
                          strokeLinecap="round" strokeLinejoin="round" />
                </svg>
                {asMenuItem && <span> Report a problem</span>}
            </button>
            {attached && (
                <div className="problem-panel" role="dialog" aria-label="Report a problem">
                    <h3>Report a problem</h3>
                    {done ? (
                        <>
                            <p role="status">{done}</p>
                            <button type="button" className="problem-btn" onClick={() => setAttached(null)}>Close</button>
                        </>
                    ) : (
                        <>
                            <p>Something that doesn&rsquo;t work, or could be better? Tell LogoSphere&rsquo;s administrators.</p>
                            <div className="problem-kinds" role="radiogroup" aria-label="What kind of problem">
                                {KINDS.map((k) => (
                                    <button key={k} type="button" role="radio" aria-checked={kind === k}
                                            className={`problem-kind${kind === k ? ' is-on' : ''}`}
                                            onClick={() => setKind(kind === k ? '' : k)}>{k}</button>
                                ))}
                            </div>
                            <textarea rows={3} maxLength={1000} value={note} onChange={(e) => setNote(e.target.value)}
                                      autoFocus aria-label="What happened"
                                      placeholder="What happened, and what did you expect?" />
                            <p className="problem-about">
                                {signedIn
                                    ? 'Only the administrators see it, with your name and what is attached.'
                                    : "Only the administrators see it, with what is attached. You're not signed in, so no name goes with it."}
                                {' '}
                                <button type="button" className="problem-link" onClick={() => setShowAttached((v) => !v)}>
                                    {showAttached ? 'Hide what is attached' : 'Show what is attached'}
                                </button>
                            </p>
                            {showAttached && (
                                <pre className="problem-attached">
                                    {Object.entries(attached).map(([k, v]) => `${k}: ${v}`).join('\n')}
                                </pre>
                            )}
                            {error && <p className="problem-error" role="alert">{error}</p>}
                            <div className="problem-buttons">
                                <button type="button" className="problem-btn" onClick={send} disabled={busy || !note.trim()}>
                                    {busy ? 'Sending…' : 'Send'}
                                </button>
                                <button type="button" className="problem-link" onClick={() => setAttached(null)}>Cancel</button>
                            </div>
                        </>
                    )}
                </div>
            )}
        </div>
    );
}

ProblemFlag.propTypes = { signedIn: PropTypes.bool, asMenuItem: PropTypes.bool, className: PropTypes.string };
