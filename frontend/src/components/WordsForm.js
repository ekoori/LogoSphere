// A few words, and the value cards they express: an acknowledgement, or the
// initiator's note. Waits for the server: nothing looks posted until it is.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import ValueCardPicker from './ValueCardPicker';
import '../styles/Acknowledgements.css';

export const MAX_WORDS = 1000;

export default function WordsForm({ placeholder, submitLabel, onSave, onCancel, counterparts = [] }) {
    const [text, setText] = useState('');
    const [cardIds, setCardIds] = useState([]);
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState('');

    const submit = async (e) => {
        e.preventDefault();
        if (busy || !text.trim()) return;
        setBusy(true);
        setProblem('');
        try {
            await onSave({ text: text.trim(), cardIds });
        } catch (err) {
            setProblem(err.response?.data?.message || "That couldn't be saved. Try again.");
            setBusy(false);
        }
    };

    return (
        <form className="words-form" onSubmit={submit} onClick={(e) => e.stopPropagation()}>
            <textarea
                className="words-form-text"
                placeholder={placeholder}
                aria-label={placeholder}
                value={text}
                maxLength={MAX_WORDS}
                rows={3}
                onChange={(e) => setText(e.target.value)}
            />
            <ValueCardPicker selectedIds={cardIds} onChange={setCardIds} counterparts={counterparts} />
            <div className="words-form-foot">
                <button type="submit" className="btn btn-primary" disabled={busy || !text.trim()}>
                    {busy ? 'Saving…' : submitLabel}
                </button>
                <button type="button" className="btn btn-ghost" onClick={onCancel} disabled={busy}>Cancel</button>
                {text.length > MAX_WORDS - 150 && <span className="words-form-left">{MAX_WORDS - text.length} characters left</span>}
            </div>
            {problem && <p className="ack-problem" role="alert">{problem}</p>}
        </form>
    );
}

WordsForm.propTypes = {
    placeholder: PropTypes.string.isRequired,
    submitLabel: PropTypes.string.isRequired,
    onSave: PropTypes.func.isRequired,
    onCancel: PropTypes.func.isRequired,
    counterparts: PropTypes.array,
};
