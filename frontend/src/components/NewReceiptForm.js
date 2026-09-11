// NewReceiptForm — the receiver's thank-you for an exchange. A receipt is the
// load-bearing record here (see About): it names the value card(s) the act
// expressed and which of Frankl's three kinds of meaning it was, alongside
// the words themselves.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import ValueCardPicker from './ValueCardPicker';

const MODES = [
    { key: 'creative', glyph: '✶', label: 'Creative', gloss: 'something was made or given' },
    { key: 'experiential', glyph: '❍', label: 'Experiential', gloss: 'something was received or shared' },
    { key: 'attitudinal', glyph: '△', label: 'Attitudinal', gloss: 'a stance taken under constraint' },
];

const NewReceiptForm = ({ onSave, onCancel, counterparts = [] }) => {
    const [text, setText] = useState('');
    const [error, setError] = useState(false);
    const [selectedIds, setSelectedIds] = useState([]);
    const [selectedCards, setSelectedCards] = useState([]);
    const [franklMode, setFranklMode] = useState('');

    const handlePickerChange = (ids, cards) => {
        setSelectedIds(ids);
        setSelectedCards(cards);
    };

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!text.trim()) {
            setError(true);
            return;
        }
        onSave({ text: text.trim(), cardIds: selectedIds, cards: selectedCards, franklMode: franklMode || null });
    };

    return (
        <div id="receipt-entry">
            <textarea
                placeholder="What happened, and what did it mean to you?"
                value={text}
                onChange={(e) => { setText(e.target.value); setError(false); }}
                rows={3}
                style={{
                    width: '100%', boxSizing: 'border-box',
                    border: error ? '1px solid var(--danger)' : '1px solid var(--border)',
                    borderRadius: 'var(--r-sm)', padding: '0.55em 0.7em',
                    fontFamily: 'var(--font-body)', fontSize: '0.92rem',
                    resize: 'vertical', marginBottom: '0.5em',
                    background: 'var(--surface)',
                }}
            />
            {error && <p style={{ color: 'var(--danger)', fontSize: '0.8rem', margin: '0 0 0.4em' }}>Please write something first.</p>}

            <div className="vc-picker">
                <span className="vc-picker-label">What kind of meaning was this?</span>
                <div className="vc-picker-chips">
                    {MODES.map((m) => (
                        <button
                            key={m.key}
                            type="button"
                            className={`vc-picker-chip${franklMode === m.key ? ' vc-picker-chip--on' : ''}`}
                            onClick={() => setFranklMode(franklMode === m.key ? '' : m.key)}
                            title={m.gloss}
                        >
                            <span className="vc-chip-glyph">{m.glyph}</span>
                            <span className="vc-chip-title">{m.label}</span>
                        </button>
                    ))}
                </div>
            </div>

            <ValueCardPicker selectedIds={selectedIds} onChange={handlePickerChange} counterparts={counterparts} />
            <div style={{ display: 'flex', gap: '0.5em', marginTop: '0.6em' }}>
                <button id="save-receipt-btn" onClick={handleSubmit}>Save</button>
                <button id="cancel-receipt-btn" onClick={onCancel}>Cancel</button>
            </div>
        </div>
    );
};

NewReceiptForm.propTypes = {
    onSave: PropTypes.func.isRequired,
    onCancel: PropTypes.func.isRequired,
    counterparts: PropTypes.array,
};

export default NewReceiptForm;
