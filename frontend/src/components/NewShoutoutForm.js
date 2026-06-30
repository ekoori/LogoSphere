import React, { useState } from 'react';
import PropTypes from 'prop-types';

const NewShoutoutForm = ({ onSave, onCancel }) => {
    const [text, setText] = useState('');
    const [error, setError] = useState(false);

    const handleSubmit = (e) => {
        e.preventDefault();
        if (!text.trim()) {
            setError(true);
            return;
        }
        onSave({ text: text.trim() });
    };

    return (
        <div id="shoutout-entry">
            <textarea
                placeholder="Write your shoutout here…"
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
            <div style={{ display: 'flex', gap: '0.5em' }}>
                <button id="save-shoutout-btn" onClick={handleSubmit}>Save</button>
                <button id="cancel-shoutout-btn" onClick={onCancel}>Cancel</button>
            </div>
        </div>
    );
};

NewShoutoutForm.propTypes = {
    onSave: PropTypes.func.isRequired,
    onCancel: PropTypes.func.isRequired,
};

export default NewShoutoutForm;
