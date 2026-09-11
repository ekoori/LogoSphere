// ValueCardChip — mini chip that expands to a full value card modal on click.
// Works in both horizontal wrap rows (entity hero) and vertical sidebar lists (UserPage).

import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import PropTypes from 'prop-types';
import api from '../api';
import { useManagedEntities } from '../utils/useManagedEntities';
import ValueCardState from './ValueCardState';
import '../styles/ValueCardChip.css';

const COLOR_MAP = {
    honey:      'var(--honey)',
    leaf:       'var(--leaf)',
    terracotta: 'var(--terracotta)',
    moss:       'var(--moss)',
    sage:       'var(--sage)',
};

const FRANKL_GLYPH  = { creative: '✶', experiential: '❍', attitudinal: '△' };
const FRANKL_LABEL  = { creative: 'creative', experiential: 'experiential', attitudinal: 'attitudinal' };

function ValueCardChip({ card, subjectLabel = 'Cares about', currentUserId = null }) {
    const [open, setOpen] = useState(false);
    const accent = COLOR_MAP[card.color_key] || 'var(--honey)';
    const glyph  = FRANKL_GLYPH[card.frankl_mode]  || '✶';
    const modeLabel = FRANKL_LABEL[card.frankl_mode] || card.frankl_mode;

    // Cloning: only offered when we know who's looking (currentUserId passed
    // in) and this isn't already their own card. `managed` is the set of
    // entities they can also clone onto (see useManagedEntities).
    const managed = useManagedEntities(currentUserId);
    const canClone = !!currentUserId && String(card.user_id) !== String(currentUserId);
    const [cloneTarget, setCloneTarget] = useState('');
    const [cloning, setCloning] = useState(false);
    const [cloneMsg, setCloneMsg] = useState(null);

    const handleClone = async () => {
        const targetId = cloneTarget || currentUserId;
        setCloning(true);
        setCloneMsg(null);
        try {
            await api.post('/api/value_cards/clone', { source: card, target_id: targetId });
            setCloneMsg({ ok: true, text: '✓ Added to Meaning Graph' });
        } catch (err) {
            setCloneMsg({ ok: false, text: err.response?.data?.message || 'Could not clone this card.' });
        } finally {
            setCloning(false);
        }
    };

    return (
        <>
            <button
                className="vc-chip"
                style={{ '--chip-accent': accent }}
                onClick={(e) => { e.stopPropagation(); setOpen(true); }}
                title={`${card.title} — click to expand`}
            >
                <span className="vc-chip-glyph" aria-hidden="true">{glyph}</span>
                <span className="vc-chip-title">{card.title}</span>
            </button>

            {open && createPortal(
                <div
                    className="vc-chip-backdrop"
                    onClick={() => setOpen(false)}
                    role="presentation"
                >
                    <div
                        className="vc-chip-modal"
                        style={{ '--vc-accent': accent }}
                        onClick={e => e.stopPropagation()}
                        role="dialog"
                        aria-modal="true"
                        aria-label={card.title}
                    >
                        <div className="vc-punch" />
                        <button
                            className="vc-chip-close"
                            onClick={() => setOpen(false)}
                            aria-label="Close"
                        >✕</button>

                        <div className="vc-top">
                            <span className="vc-mode-badge">
                                <span className="vc-mode-glyph">{glyph}</span>
                                {modeLabel}
                            </span>
                        </div>

                        <h3 className="vc-title">{card.title}</h3>
                        {('endorsed' in card) && <ValueCardState card={card} />}

                        {card.care_about && (
                            <div className="vc-field">
                                <span className="vc-label">{subjectLabel}</span>
                                <p>{card.care_about}</p>
                            </div>
                        )}

                        {card.because && (
                            <div className="vc-field">
                                <span className="vc-label">Because</span>
                                <p>{card.because}</p>
                            </div>
                        )}

                        {card.looks_like?.length > 0 && (
                            <div className="vc-field">
                                <span className="vc-label">Looks like</span>
                                <ul className="vc-list">
                                    {card.looks_like.map((l, i) => <li key={i}>{l}</li>)}
                                </ul>
                            </div>
                        )}

                        {card.drift_looks_like && (
                            <div className="vc-field vc-field--drift">
                                <span className="vc-label">Drift looks like</span>
                                <p>{card.drift_looks_like}</p>
                            </div>
                        )}

                        {card.in_conflict && (
                            <div className="vc-field">
                                <span className="vc-label">When in conflict, choose</span>
                                <p>{card.in_conflict}</p>
                            </div>
                        )}

                        {card.never_do && (
                            <div className="vc-field vc-field--never">
                                <span className="vc-label">Never do</span>
                                <p>{card.never_do}</p>
                            </div>
                        )}

                        {canClone && (
                            <div className="vc-clone">
                                <span className="vc-label">Make this yours</span>
                                <p className="vc-clone-hint">Copy this value onto your own Meaning Graph — or one you manage.</p>
                                <div className="vc-clone-row">
                                    <select
                                        value={cloneTarget}
                                        onChange={(e) => { setCloneTarget(e.target.value); setCloneMsg(null); }}
                                        aria-label="Clone destination"
                                    >
                                        <option value="">My profile</option>
                                        {managed.map((m) => (
                                            <option key={m.id} value={m.id}>{m.name} ({m.kind})</option>
                                        ))}
                                    </select>
                                    <button className="vc-clone-btn" onClick={handleClone} disabled={cloning}>
                                        {cloning ? 'Cloning…' : '+ Clone'}
                                    </button>
                                </div>
                                {cloneMsg && (
                                    <p className={`vc-clone-msg ${cloneMsg.ok ? 'vc-clone-msg--ok' : 'vc-clone-msg--err'}`}>
                                        {cloneMsg.text}
                                    </p>
                                )}
                            </div>
                        )}
                    </div>
                </div>,
                document.body
            )}
        </>
    );
}

ValueCardChip.propTypes = {
    card: PropTypes.shape({
        card_id:          PropTypes.string,
        title:            PropTypes.string.isRequired,
        care_about:       PropTypes.string,
        because:          PropTypes.string,
        looks_like:       PropTypes.arrayOf(PropTypes.string),
        drift_looks_like: PropTypes.string,
        in_conflict:      PropTypes.string,
        never_do:         PropTypes.string,
        frankl_mode:      PropTypes.string,
        color_key:        PropTypes.string,
    }).isRequired,
    subjectLabel: PropTypes.string,
    currentUserId: PropTypes.string,
};

export default ValueCardChip;
