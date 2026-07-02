// ValueCardChip — mini chip that expands to a full value card modal on click.
// Works in both horizontal wrap rows (entity hero) and vertical sidebar lists (UserPage).

import React, { useState } from 'react';
import { createPortal } from 'react-dom';
import PropTypes from 'prop-types';
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

function ValueCardChip({ card, subjectLabel = 'Cares about' }) {
    const [open, setOpen] = useState(false);
    const accent = COLOR_MAP[card.color_key] || 'var(--honey)';
    const glyph  = FRANKL_GLYPH[card.frankl_mode]  || '✶';
    const modeLabel = FRANKL_LABEL[card.frankl_mode] || card.frankl_mode;

    return (
        <>
            <button
                className="vc-chip"
                style={{ '--chip-accent': accent }}
                onClick={() => setOpen(true)}
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
};

export default ValueCardChip;
