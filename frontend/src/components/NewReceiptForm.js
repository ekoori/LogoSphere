import React, { useState } from 'react';
import PropTypes from 'prop-types';
import ValueCardPicker from './ValueCardPicker';

const NewReceiptForm = ({ onSave, onCancel }) => {
    const [text, setText] = useState('');
    const [error, setError] = useState(false);
    const [selectedIds, setSelectedIds] = useState([]);
    const [selectedCards, setSelectedCards] = useState([]);

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
        onSave({ text: text.trim(), cardIds: selectedIds, cards: selectedCards });
    };

    return (
        <div id="receipt-entry">
            <textarea
                placeholder="How did this exchange feel? What did it mean to you?"
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
            <ValueCardPicker selectedIds={selectedIds} onChange={handlePickerChange} />
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
};

export default NewReceiptForm;
