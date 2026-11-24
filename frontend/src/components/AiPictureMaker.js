// "Draw one with AI", beside a picture field: for openings, groups and events,
// never receipts. Nothing is sent until "Draw", nothing saved until it's used.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import api from '../api';
import { useAiHelp } from '../utils/useAiHelp';
import { pictureFile } from '../utils/aiHelp';
import { Picture } from './AiTag';
import { ReportButton } from './Safety';
import '../styles/AiHelp.css';

const AI_ABOUT = "Only the platform's administrators see it, with what the AI gave you.";

export default function AiPictureMaker({ purpose, title, description = '', onUse }) {
    const { on, left, setLeft } = useAiHelp('pictures');
    const [open, setOpen] = useState(false);
    const [hint, setHint] = useState('');
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState('');
    const [made, setMade] = useState(null);
    if (!on) return null;

    const named = !!title?.trim();
    const spent = left < 1;

    const draw = async () => {
        if (busy || !named || spent) return;
        setBusy(true);
        setProblem('');
        try {
            const res = await api.post('/api/ai/picture', { purpose, title, description, hint });
            setMade({
                src: `data:${res.data.content_type};base64,${res.data.image}`,
                file: pictureFile(res.data.image, res.data.content_type),
            });
            setLeft(res.data.left);
        } catch (e) {
            setProblem(e.response?.data?.message || "The picture didn't come. Try again.");
        }
        setBusy(false);
    };

    const use = async () => {
        if (busy) return;
        setBusy(true);
        setProblem('');
        try {
            await onUse(made.file);
            setMade(null);
            setOpen(false);
        } catch (e) {
            setProblem(e.response?.data?.message || "That didn't save. Try again.");
        }
        setBusy(false);
    };

    if (!open) {
        return <button type="button" className="ai-open" onClick={() => setOpen(true)}>✦ Draw one with AI</button>;
    }
    return (
        <div className="ai-panel">
            {!named && <p className="ai-note">Give it a title first, so there is something to draw.</p>}
            <label className="ai-field">
                Anything it should show? (optional)
                <input
                    type="text"
                    value={hint}
                    maxLength={300}
                    placeholder="e.g. autumn light, an old wheelbarrow"
                    onChange={(e) => setHint(e.target.value)}
                    onKeyDown={(e) => {
                        if (e.key !== 'Enter') return;
                        e.preventDefault(); // it sits inside other forms
                        draw();
                    }}
                />
            </label>
            <p className="ai-note">
                Sends the title, the description and your words to OpenAI, and nothing about who you are.
                AI pictures are labelled, and outside demo spheres they can&rsquo;t be evidence.
            </p>
            {made && <div className="ai-preview"><Picture isAi src={made.src} alt="Drawn for you" /></div>}
            {busy && !made && <p className="ai-note" role="status">Drawing. It takes about ten seconds…</p>}
            {spent && !made && <p className="ai-note">That&rsquo;s all the AI pictures for today.</p>}
            {problem && <p className="ai-problem" role="alert">{problem}</p>}
            <div className="ai-actions">
                {made && <button type="button" className="ai-btn ai-btn--main" onClick={use} disabled={busy}>Use this picture</button>}
                <button type="button" className={`ai-btn${made ? '' : ' ai-btn--main'}`} onClick={draw} disabled={busy || !named || spent}>
                    {made ? 'Draw another' : 'Draw'}
                </button>
                <button type="button" className="ai-btn" onClick={() => { setOpen(false); setMade(null); }} disabled={busy}>Close</button>
            </div>
            {made && (
                // The picture itself is never kept, so the report says what it was asked to show.
                <ReportButton report={{ kind: 'ai', id: 'picture', excerpt: [`Title: ${title}`, description && `Description: ${description}`,
                                        hint && `Asked to show: ${hint}`].filter(Boolean).join('\n') }}
                              label="Report this picture" about={AI_ABOUT} />
            )}
        </div>
    );
}

AiPictureMaker.propTypes = {
    purpose: PropTypes.oneOf(['opening', 'sphere', 'alliance', 'project', 'event']).isRequired,
    title: PropTypes.string,
    description: PropTypes.string,
    onUse: PropTypes.func.isRequired,
};
