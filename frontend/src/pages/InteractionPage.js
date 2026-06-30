import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useLogin } from '../App';
import api from '../api';
import StatusProgression from '../components/StatusProgression';
import '../styles/Interaction.css';
import '../styles/MeaningTrail.css';

const IX_STEPS = ['Initiated', 'In Progress', 'Finished', 'Receipted', 'Additional Comments Added'];

const ixIdx = (status) => {
    const i = IX_STEPS.findIndex(s => s.toLowerCase() === (status || '').toLowerCase());
    return i >= 0 ? i : 0;
};

const fmtDate = (val) => {
    if (!val) return '';
    const d = new Date(val);
    return isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
};

const TYPE_LABEL = { completed: 'Completed', offer: 'Offer', request: 'Request' };
const TYPE_PILL  = { completed: 'pill-leaf', offer: 'pill-clay', request: 'pill-honey' };

function InteractionPage() {
    const [searchParams] = useSearchParams();
    const ixId = searchParams.get('id');
    const { userId } = useLogin();

    const [ix, setIx] = useState(null);
    const [isInitiator, setIsInitiator] = useState(false);
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState(null);

    const [gratitudeText, setGratitudeText] = useState('');
    const [userNoteText, setUserNoteText] = useState('');
    const [acknowledgementText, setAcknowledgementText] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const fetchIx = useCallback(async () => {
        if (!ixId) { setFetchError('No interaction ID provided.'); setLoading(false); return; }
        try {
            const res = await api.get(`/api/interaction/${ixId}`);
            setIx(res.data.interaction);
            setIsInitiator(res.data.is_initiator);
        } catch (e) {
            setFetchError(
                e.response?.status === 404
                    ? 'Interaction not found or you are not a participant.'
                    : 'Could not load interaction. Please try again.'
            );
        } finally {
            setLoading(false);
        }
    }, [ixId]);

    useEffect(() => { fetchIx(); }, [fetchIx]);

    if (loading) return <div className="ix-loading">Loading interaction…</div>;
    if (fetchError || !ix) return <div className="ix-error-state">{fetchError || 'Interaction not found.'}</div>;

    const isOtherUser = String(ix.other_user_id) === String(userId);
    const canModify = isInitiator || isOtherUser;
    const isCancelled = ix.interaction_status === 'Cancelled';
    const currentIdx = isCancelled ? ixIdx('Initiated') : ixIdx(ix.interaction_status);
    const nextStatus = !isCancelled && currentIdx < IX_STEPS.length - 1 ? IX_STEPS[currentIdx + 1] : null;

    const completed = ['Finished', 'Receipted', 'Additional Comments Added'].includes(ix.interaction_status);
    const ixType = completed ? 'completed' : 'offer';
    const pillClass = TYPE_PILL[ixType] || 'pill-clay';
    const typeLabel = TYPE_LABEL[ixType] || ixType;

    const steps = IX_STEPS.map((label) => ({ label, time: '' }));

    const handleAdvanceStatus = async () => {
        if (!nextStatus) return;
        try {
            await api.post(`/api/interaction/${ixId}/status`, { status: nextStatus });
            fetchIx();
        } catch (e) {
            console.error('Failed to advance status:', e);
        }
    };

    const handleCancel = async () => {
        if (!window.confirm('Cancel this interaction? This cannot be undone.')) return;
        try {
            await api.post(`/api/interaction/${ixId}/status`, { status: 'Cancelled' });
            fetchIx();
        } catch (e) {
            console.error('Failed to cancel:', e);
        }
    };

    const submitComment = async (type, text, clearFn) => {
        if (!text.trim() || submitting) return;
        setSubmitting(true);
        try {
            await api.post(`/api/interaction/${ixId}/comment`, { type, text: text.trim() });
            clearFn('');
            fetchIx();
        } catch (e) {
            console.error('Failed to add comment:', e);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="ix-page">
            {/* ── Hero ─────────────────────────────────────────────────── */}
            <div className="ix-page-hero">
                <div className="ix-page-breadcrumb">
                    <Link to="/profile">Meaning Trail</Link>
                    <span>›</span>
                    <span>{ix.interaction_description || 'Interaction'}</span>
                </div>

                <div className="ix-page-header">
                    <span className={`pill ${pillClass} type-pill`}>{typeLabel}</span>
                    <h1 className="ix-page-title">
                        {ix.interaction_description || 'An exchange of trust'}
                    </h1>
                    {isCancelled && <span className="pill pill-clay">Cancelled</span>}
                </div>

                <div className="ix-page-meta">
                    {fmtDate(ix.project_start_timestamp) && (
                        <span>{fmtDate(ix.project_start_timestamp)}</span>
                    )}
                    {ix.project_name && (
                        <>
                            <span>·</span>
                            <span>Part of <strong>{ix.project_name}</strong></span>
                        </>
                    )}
                </div>

                {isCancelled && (
                    <div className="ix-cancelled-banner">
                        This interaction was cancelled.
                    </div>
                )}
            </div>

            {/* ── Status timeline ───────────────────────────────────────── */}
            <div className="ix-page-timeline">
                <StatusProgression steps={steps} currentIndex={currentIdx} cancelled={isCancelled} />
            </div>

            {/* ── Body ─────────────────────────────────────────────────── */}
            <div className="ix-page-body">
                {/* Main content */}
                <div className="ix-page-main">
                    {/* About */}
                    <div className="ix-page-section">
                        <p className="ix-page-section-heading">About this exchange</p>
                        <p className="ix-about-text">
                            {ix.project_name
                                ? `An act of giving within the "${ix.project_name}" project.`
                                : 'A moment of trust shared in the community.'}
                        </p>
                        {ix.project_id && ix.project_name && (
                            <Link
                                to={`/project?id=${ix.project_id}`}
                                className="pill pill-leaf"
                                style={{ fontSize: '0.8rem', textDecoration: 'none' }}
                            >
                                {ix.project_name}
                            </Link>
                        )}
                    </div>

                    {/* ── Receipts ──────────────────────────────────────── */}
                    <div className="ix-page-section">
                        <div className="ix-section-label ix-section-receipt" style={{ marginBottom: '0.9em' }}>
                            <span>✓ Receipts</span>
                            <span className="ix-section-hint">verified attestations of trust</span>
                        </div>

                        {ix.gratitude_comment && (
                            <div className="receipt">
                                <div className="tf-content">
                                    <p>
                                        <strong>{ix.other_user_name || 'Other party'}:</strong>{' '}
                                        {ix.gratitude_comment}
                                    </p>
                                    {fmtDate(ix.gratitude_comment_timestamp) && (
                                        <span className="ix-date" style={{ marginTop: '0.3em', display: 'block', fontSize: '0.74rem' }}>
                                            {fmtDate(ix.gratitude_comment_timestamp)}
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {ix.user_comment && (
                            <div className="receipt" style={{ marginTop: ix.gratitude_comment ? '0.55em' : 0 }}>
                                <div className="tf-content">
                                    <p>
                                        <strong>{isInitiator ? 'You' : 'Initiator'}:</strong>{' '}
                                        {ix.user_comment}
                                    </p>
                                    {fmtDate(ix.user_comment_timestamp) && (
                                        <span className="ix-date" style={{ marginTop: '0.3em', display: 'block', fontSize: '0.74rem' }}>
                                            {fmtDate(ix.user_comment_timestamp)}
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {!ix.gratitude_comment && !ix.user_comment && (
                            <p className="ix-empty-section">No receipts yet.</p>
                        )}

                        {/* Other party adds gratitude_comment */}
                        {isOtherUser && !ix.gratitude_comment && (
                            <div className="ix-comment-area">
                                <span className="ix-comment-label">Your receipt</span>
                                <textarea
                                    className="ix-comment-input"
                                    placeholder="How did this exchange feel? What did it mean to you?"
                                    value={gratitudeText}
                                    onChange={e => setGratitudeText(e.target.value)}
                                />
                                <button
                                    className="ix-comment-submit ix-submit-receipt"
                                    disabled={submitting || !gratitudeText.trim()}
                                    onClick={() => submitComment('gratitude', gratitudeText, setGratitudeText)}
                                >
                                    + Add Receipt
                                </button>
                            </div>
                        )}

                        {/* Initiator adds user_comment */}
                        {isInitiator && !ix.user_comment && (
                            <div className="ix-comment-area">
                                <span className="ix-comment-label">Your note</span>
                                <textarea
                                    className="ix-comment-input"
                                    placeholder="Reflect on this exchange — what did you give and learn?"
                                    value={userNoteText}
                                    onChange={e => setUserNoteText(e.target.value)}
                                />
                                <button
                                    className="ix-comment-submit ix-submit-receipt"
                                    disabled={submitting || !userNoteText.trim()}
                                    onClick={() => submitComment('user', userNoteText, setUserNoteText)}
                                >
                                    + Add Note
                                </button>
                            </div>
                        )}
                    </div>

                    {/* ── Acknowledgements ─────────────────────────────────────────── */}
                    <div className="ix-page-section">
                        <div className="ix-section-label ix-section-acknowledgement" style={{ marginBottom: '0.9em' }}>
                            <span>📢 Acknowledgements</span>
                            <span className="ix-section-hint">public acknowledgements</span>
                        </div>

                        {ix.other_comment ? (
                            <div className="acknowledgement">
                                <div className="tf-content">
                                    <p>
                                        <strong>{ix.other_comment_author_name || 'A participant'}:</strong>{' '}
                                        {ix.other_comment}
                                    </p>
                                    {fmtDate(ix.other_comment_timestamp) && (
                                        <span className="ix-date" style={{ marginTop: '0.3em', display: 'block', fontSize: '0.74rem' }}>
                                            {fmtDate(ix.other_comment_timestamp)}
                                        </span>
                                    )}
                                </div>
                            </div>
                        ) : (
                            <p className="ix-empty-section">No acknowledgements yet.</p>
                        )}

                        {canModify && !ix.other_comment && (
                            <div className="ix-comment-area">
                                <span className="ix-comment-label">Add a acknowledgement</span>
                                <textarea
                                    className="ix-comment-input"
                                    placeholder="Celebrate this exchange publicly — let the community know!"
                                    value={acknowledgementText}
                                    onChange={e => setAcknowledgementText(e.target.value)}
                                />
                                <button
                                    className="ix-comment-submit ix-submit-acknowledgement"
                                    disabled={submitting || !acknowledgementText.trim()}
                                    onClick={() => submitComment('other', acknowledgementText, setAcknowledgementText)}
                                >
                                    + Add Acknowledgement
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* ── Sidebar ───────────────────────────────────────────── */}
                <div className="ix-page-sidebar">
                    {/* Actions — only for participants */}
                    {canModify && !isCancelled && (
                        <div className="ix-sidebar-card">
                            <p className="ix-sidebar-heading">Actions</p>
                            {nextStatus && (
                                <button className="ix-action-btn ix-action-advance" onClick={handleAdvanceStatus}>
                                    Mark as {nextStatus}
                                </button>
                            )}
                            {isInitiator && (
                                <button className="ix-action-btn ix-action-secondary" onClick={handleCancel}>
                                    Cancel interaction
                                </button>
                            )}
                            {!nextStatus && (
                                <p style={{ fontSize: '0.82rem', color: 'var(--ink-faint)', margin: 0, fontStyle: 'italic' }}>
                                    Interaction is complete.
                                </p>
                            )}
                        </div>
                    )}

                    {/* Participants */}
                    <div className="ix-sidebar-card">
                        <p className="ix-sidebar-heading">Participants</p>
                        <div className="ix-participants-list">
                            <div className="ix-participant">
                                <span>👤</span>
                                {isInitiator
                                    ? <span className="ix-participant-you">You</span>
                                    : <a href={`/user?id=${ix.user_id}`}>Initiator</a>
                                }
                                <span className="ix-participant-role">Initiator</span>
                            </div>
                            {ix.other_user_id && (
                                <div className="ix-participant">
                                    <span>👤</span>
                                    {isOtherUser
                                        ? <span className="ix-participant-you">You</span>
                                        : <a href={`/user?id=${ix.other_user_id}`}>{ix.other_user_name || 'Recipient'}</a>
                                    }
                                    <span className="ix-participant-role">Recipient</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Details */}
                    <div className="ix-sidebar-card">
                        <p className="ix-sidebar-heading">Details</p>
                        <div className="ix-detail-rows">
                            <div className="ix-detail-row">
                                <span className="ix-detail-label">Status</span>
                                <span className="ix-detail-value ix-status-value">
                                    {ix.interaction_status || 'Initiated'}
                                </span>
                            </div>
                            {ix.project_name && (
                                <div className="ix-detail-row">
                                    <span className="ix-detail-label">Project</span>
                                    <span className="ix-detail-value">
                                        <a href={`/project?id=${ix.project_id}`}>{ix.project_name}</a>
                                    </span>
                                </div>
                            )}
                            {fmtDate(ix.project_start_timestamp) && (
                                <div className="ix-detail-row">
                                    <span className="ix-detail-label">Initiated</span>
                                    <span className="ix-detail-value">
                                        {fmtDate(ix.project_start_timestamp)}
                                    </span>
                                </div>
                            )}
                            <div className="ix-detail-row">
                                <span className="ix-detail-label">Interaction ID</span>
                                <span className="ix-detail-mono">{ix.interaction_id}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default InteractionPage;
