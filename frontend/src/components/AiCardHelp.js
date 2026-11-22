// "Help me word it", in a value-card form. The suggestion is shown before it
// goes into the form, and saving the card is still the person's own step.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import api from '../api';
import { useAiHelp } from '../utils/useAiHelp';
import { cardForHelp, withSuggestion } from '../utils/aiHelp';
import '../styles/AiHelp.css';

const SHOWN = [
    ['title', 'Title'],
    ['care_about', 'Cares about'],
    ['because', 'Because'],
    ['looks_like', 'Looks like'],
    ['drift_looks_like', 'Drift looks like'],
    ['in_conflict', 'In conflict'],
    ['never_do', 'Never'],
];

export default function AiCardHelp({ form, onChange, brief = false, group = false }) {
    const { on, left, setLeft } = useAiHelp('value_cards');
    const [open, setOpen] = useState(false);
    const [notes, setNotes] = useState('');
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState('');
    const [suggested, setSuggested] = useState(null);
    const [question, setQuestion] = useState('');
    if (!on) return null;

    const draft = cardForHelp(form, { brief });
    const nothingYet = !notes.trim() && Object.keys(draft).length === 0;
    const spent = left < 1;

    const ask = async () => {
        if (busy || nothingYet || spent) return;
        setBusy(true);
        setProblem('');
        try {
            const res = await api.post('/api/ai/value_card', { notes, draft, brief, group });
            const hasWords = SHOWN.some(([key]) => [].concat(res.data.draft[key] || []).length > 0);
            setSuggested(hasWords ? res.data.draft : null);
            setQuestion(res.data.question || '');
            setLeft(res.data.left);
        } catch (e) {
            setProblem(e.response?.data?.message || "The help didn't come. Try again.");
        }
        setBusy(false);
    };

    const use = () => {
        onChange(withSuggestion(form, suggested, { brief }));
        setSuggested(null);
        setOpen(false);
    };

    if (!open) {
        return (
            <div className="ai-closed">
                <button type="button" className="ai-open" onClick={() => setOpen(true)}>✦ Help me word it</button>
                {question && <p className="ai-question">Something to ask yourself before saving: {question}</p>}
            </div>
        );
    }
    return (
        <div className="ai-panel">
            <label className="ai-field">
                {group ? 'What matters to the group? Any words will do.' : 'What matters to you? Any words will do.'}
                <textarea rows={3} value={notes} maxLength={1500} onChange={(e) => setNotes(e.target.value)} />
            </label>
            <p className="ai-note">
                Sends what you write here and in the card to Claude, by Anthropic, and nothing about who you are.
                Nothing is saved until you save the card.
            </p>
            {suggested && (
                <dl className="ai-suggestion">
                    {SHOWN.map(([key, label]) => {
                        const value = [].concat(suggested[key] || []).join('; ');
                        return value ? <div key={key}><dt>{label}</dt><dd>{value}</dd></div> : null;
                    })}
                </dl>
            )}
            {question && <p className="ai-question">{question}</p>}
            {spent && <p className="ai-note">That&rsquo;s all the AI help for today.</p>}
            {problem && <p className="ai-problem" role="alert">{problem}</p>}
            <div className="ai-actions">
                {suggested && <button type="button" className="ai-btn ai-btn--main" onClick={use} disabled={busy}>Put it in the card</button>}
                <button type="button" className={`ai-btn${suggested ? '' : ' ai-btn--main'}`} onClick={ask} disabled={busy || nothingYet || spent}>
                    {busy ? 'Thinking…' : suggested ? 'Try again' : 'Suggest wording'}
                </button>
                <button type="button" className="ai-btn" onClick={() => setOpen(false)} disabled={busy}>Close</button>
            </div>
        </div>
    );
}

AiCardHelp.propTypes = {
    form: PropTypes.object.isRequired,
    onChange: PropTypes.func.isRequired,
    brief: PropTypes.bool,
    group: PropTypes.bool,
};
