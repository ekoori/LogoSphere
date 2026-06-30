import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useLogin } from '../App';
import api from '../api';
import StatusProgression from '../components/StatusProgression';
import '../styles/Exchange.css';
import '../styles/MeaningTrail.css';

const XC_STEPS = ['Initiated', 'In Progress', 'Finished', 'Receipted', 'Additional Comments Added'];

const xcIdx = (status) => {
    const i = XC_STEPS.findIndex(s => s.toLowerCase() === (status || '').toLowerCase());
    return i >= 0 ? i : 0;
};

const fmtDate = (val) => {
    if (!val) return '';
    const d = new Date(val);
    return isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
};

const TYPE_LABEL = { completed: 'Completed', offer: 'Offer', need: 'Need' };
const TYPE_PILL  = { completed: 'pill-leaf', offer: 'pill-clay', need: 'pill-honey' };

function ExchangePage() {
    const [searchParams] = useSearchParams();
    const xcId = searchParams.get('id');
    const { userId } = useLogin();

    const [xc, setXc] = useState(null);
    const [isInitiator, setIsInitiator] = useState(false);
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState(null);

    const [gratitudeText, setGratitudeText] = useState('');
    const [userNoteText, setUserNoteText] = useState('');
    const [acknowledgementText, setAcknowledgementText] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const fetchXc = useCallback(async () => {
        if (!xcId) { setFetchError('No exchange ID provided.'); setLoading(false); return; }
        try {
            const res = await api.get(`/api/exchange/${xcId}`);
            setXc(res.data.exchange);
            setIsInitiator(res.data.is_initiator);
        } catch (e) {
            setFetchError(
                e.response?.status === 404
                    ? 'Exchange not found or you are not a participant.'
                    : 'Could not load exchange. Please try again.'
            );
        } finally {
            setLoading(false);
        }
    }, [xcId]);

    useEffect(() => { fetchXc(); }, [fetchXc]);

    if (loading) return <div className="xc-loading">Loading exchange…</div>;
    if (fetchError || !xc) return <div className="xc-error-state">{fetchError || 'Exchange not found.'}</div>;

    const isOtherUser = String(xc.other_user_id) === String(userId);
    const canModify = isInitiator || isOtherUser;
    const isCancelled = xc.exchange_status === 'Cancelled';
    const currentIdx = isCancelled ? xcIdx('Initiated') : xcIdx(xc.exchange_status);
    const nextStatus = !isCancelled && currentIdx < XC_STEPS.length - 1 ? XC_STEPS[currentIdx + 1] : null;

    const completed = ['Finished', 'Receipted', 'Additional Comments Added'].includes(xc.exchange_status);
    const xcType = completed ? 'completed' : 'offer';
    const pillClass = TYPE_PILL[xcType] || 'pill-clay';
    const typeLabel = TYPE_LABEL[xcType] || xcType;

    const steps = XC_STEPS.map((label) => ({ label, time: '' }));

    const handleAdvanceStatus = async () => {
        if (!nextStatus) return;
        try {
            await api.post(`/api/exchange/${xcId}/status`, { status: nextStatus });
            fetchXc();
        } catch (e) {
            console.error('Failed to advance status:', e);
        }
    };

    const handleCancel = async () => {
        if (!window.confirm('Cancel this exchange? This cannot be undone.')) return;
        try {
            await api.post(`/api/exchange/${xcId}/status`, { status: 'Cancelled' });
            fetchXc();
        } catch (e) {
            console.error('Failed to cancel:', e);
        }
    };

    const submitComment = async (type, text, clearFn) => {
        if (!text.trim() || submitting) return;
        setSubmitting(true);
        try {
            await api.post(`/api/exchange/${xcId}/comment`, { type, text: text.trim() });
            clearFn('');
            fetchXc();
        } catch (e) {
            console.error('Failed to add comment:', e);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="xc-page">
            {/* ── Hero ─────────────────────────────────────────────────── */}
            <div className="xc-page-hero">
                <div className="xc-page-breadcrumb">
                    <Link to="/profile">Meaning Trail</Link>
                    <span>›</span>
                    <span>{xc.exchange_description || 'Exchange'}</span>
                </div>

                <div className="xc-page-header">
                    <span className={`pill ${pillClass} type-pill`}>{typeLabel}</span>
                    <h1 className="xc-page-title">
                        {xc.exchange_description || 'An exchange of trust'}
                    </h1>
                    {isCancelled && <span className="pill pill-clay">Cancelled</span>}
                </div>

                <div className="xc-page-meta">
                    {fmtDate(xc.project_start_timestamp) && (
                        <span>{fmtDate(xc.project_start_timestamp)}</span>
                    )}
                    {xc.project_name && (
                        <>
                            <span>·</span>
                            <span>Part of <strong>{xc.project_name}</strong></span>
                        </>
                    )}
                </div>

                {isCancelled && (
                    <div className="xc-cancelled-banner">
                        This exchange was cancelled.
                    </div>
                )}
            </div>

            {/* ── Status timeline ───────────────────────────────────────── */}
            <div className="xc-page-timeline">
                <StatusProgression steps={steps} currentIndex={currentIdx} cancelled={isCancelled} />
            </div>

            {/* ── Body ─────────────────────────────────────────────────── */}
            <div className="xc-page-body">
                {/* Main content */}
                <div className="xc-page-main">
                    {/* About */}
                    <div className="xc-page-section">
                        <p className="xc-page-section-heading">About this exchange</p>
                        <p className="xc-about-text">
                            {xc.project_name
                                ? `An act of giving within the "${xc.project_name}" project.`
                                : 'A moment of trust shared in the community.'}
                        </p>
                        {xc.project_id && xc.project_name && (
                            <Link
                                to={`/project?id=${xc.project_id}`}
                                className="pill pill-leaf"
                                style={{ fontSize: '0.8rem', textDecoration: 'none' }}
                            >
                                {xc.project_name}
                            </Link>
                        )}
                    </div>

                    {/* ── Receipts ──────────────────────────────────────── */}
                    <div className="xc-page-section">
                        <div className="xc-section-label xc-section-receipt" style={{ marginBottom: '0.9em' }}>
                            <span>✓ Receipts</span>
                            <span className="xc-section-hint">verified attestations of trust</span>
                        </div>

                        {xc.gratitude_comment && (
                            <div className="receipt">
                                <div className="tf-content">
                                    <p>
                                        <strong>{xc.other_user_name || 'Other party'}:</strong>{' '}
                                        {xc.gratitude_comment}
                                    </p>
                                    {fmtDate(xc.gratitude_comment_timestamp) && (
                                        <span className="xc-date" style={{ marginTop: '0.3em', display: 'block', fontSize: '0.74rem' }}>
                                            {fmtDate(xc.gratitude_comment_timestamp)}
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {xc.user_comment && (
                            <div className="receipt" style={{ marginTop: xc.gratitude_comment ? '0.55em' : 0 }}>
                                <div className="tf-content">
                                    <p>
                                        <strong>{isInitiator ? 'You' : 'Initiator'}:</strong>{' '}
                                        {xc.user_comment}
                                    </p>
                                    {fmtDate(xc.user_comment_timestamp) && (
                                        <span className="xc-date" style={{ marginTop: '0.3em', display: 'block', fontSize: '0.74rem' }}>
                                            {fmtDate(xc.user_comment_timestamp)}
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {!xc.gratitude_comment && !xc.user_comment && (
                            <p className="xc-empty-section">No receipts yet.</p>
                        )}

                        {/* Other party adds gratitude_comment */}
                        {isOtherUser && !xc.gratitude_comment && (
                            <div className="xc-comment-area">
                                <span className="xc-comment-label">Your receipt</span>
                                <textarea
                                    className="xc-comment-input"
                                    placeholder="How did this exchange feel? What did it mean to you?"
                                    value={gratitudeText}
                                    onChange={e => setGratitudeText(e.target.value)}
                                />
                                <button
                                    className="xc-comment-submit xc-submit-receipt"
                                    disabled={submitting || !gratitudeText.trim()}
                                    onClick={() => submitComment('gratitude', gratitudeText, setGratitudeText)}
                                >
                                    + Add Receipt
                                </button>
                            </div>
                        )}

                        {/* Initiator adds user_comment */}
                        {isInitiator && !xc.user_comment && (
                            <div className="xc-comment-area">
                                <span className="xc-comment-label">Your note</span>
                                <textarea
                                    className="xc-comment-input"
                                    placeholder="Reflect on this exchange — what did you give and learn?"
                                    value={userNoteText}
                                    onChange={e => setUserNoteText(e.target.value)}
                                />
                                <button
                                    className="xc-comment-submit xc-submit-receipt"
                                    disabled={submitting || !userNoteText.trim()}
                                    onClick={() => submitComment('user', userNoteText, setUserNoteText)}
                                >
                                    + Add Note
                                </button>
                            </div>
                        )}
                    </div>

                    {/* ── Acknowledgements ─────────────────────────────────────────── */}
                    <div className="xc-page-section">
                        <div className="xc-section-label xc-section-acknowledgement" style={{ marginBottom: '0.9em' }}>
                            <span>📢 Acknowledgements</span>
                            <span className="xc-section-hint">public acknowledgements</span>
                        </div>

                        {xc.other_comment ? (
                            <div className="acknowledgement">
                                <div className="tf-content">
                                    <p>
                                        <strong>{xc.other_comment_author_name || 'A participant'}:</strong>{' '}
                                        {xc.other_comment}
                                    </p>
                                    {fmtDate(xc.other_comment_timestamp) && (
                                        <span className="xc-date" style={{ marginTop: '0.3em', display: 'block', fontSize: '0.74rem' }}>
                                            {fmtDate(xc.other_comment_timestamp)}
                                        </span>
                                    )}
                                </div>
                            </div>
                        ) : (
                            <p className="xc-empty-section">No acknowledgements yet.</p>
                        )}

                        {canModify && !xc.other_comment && (
                            <div className="xc-comment-area">
                                <span className="xc-comment-label">Add a acknowledgement</span>
                                <textarea
                                    className="xc-comment-input"
                                    placeholder="Celebrate this exchange publicly — let the community know!"
                                    value={acknowledgementText}
                                    onChange={e => setAcknowledgementText(e.target.value)}
                                />
                                <button
                                    className="xc-comment-submit xc-submit-acknowledgement"
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
                <div className="xc-page-sidebar">
                    {/* Actions — only for participants */}
                    {canModify && !isCancelled && (
                        <div className="xc-sidebar-card">
                            <p className="xc-sidebar-heading">Actions</p>
                            {nextStatus && (
                                <button className="xc-action-btn xc-action-advance" onClick={handleAdvanceStatus}>
                                    Mark as {nextStatus}
                                </button>
                            )}
                            {isInitiator && (
                                <button className="xc-action-btn xc-action-secondary" onClick={handleCancel}>
                                    Cancel exchange
                                </button>
                            )}
                            {!nextStatus && (
                                <p style={{ fontSize: '0.82rem', color: 'var(--ink-faint)', margin: 0, fontStyle: 'italic' }}>
                                    Exchange is complete.
                                </p>
                            )}
                        </div>
                    )}

                    {/* Participants */}
                    <div className="xc-sidebar-card">
                        <p className="xc-sidebar-heading">Participants</p>
                        <div className="xc-participants-list">
                            <div className="xc-participant">
                                <span>👤</span>
                                {isInitiator
                                    ? <span className="xc-participant-you">You</span>
                                    : <a href={`/user?id=${xc.user_id}`}>Initiator</a>
                                }
                                <span className="xc-participant-role">Initiator</span>
                            </div>
                            {xc.other_user_id && (
                                <div className="xc-participant">
                                    <span>👤</span>
                                    {isOtherUser
                                        ? <span className="xc-participant-you">You</span>
                                        : <a href={`/user?id=${xc.other_user_id}`}>{xc.other_user_name || 'Recipient'}</a>
                                    }
                                    <span className="xc-participant-role">Recipient</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Details */}
                    <div className="xc-sidebar-card">
                        <p className="xc-sidebar-heading">Details</p>
                        <div className="xc-detail-rows">
                            <div className="xc-detail-row">
                                <span className="xc-detail-label">Status</span>
                                <span className="xc-detail-value xc-status-value">
                                    {xc.exchange_status || 'Initiated'}
                                </span>
                            </div>
                            {xc.project_name && (
                                <div className="xc-detail-row">
                                    <span className="xc-detail-label">Project</span>
                                    <span className="xc-detail-value">
                                        <a href={`/project?id=${xc.project_id}`}>{xc.project_name}</a>
                                    </span>
                                </div>
                            )}
                            {fmtDate(xc.project_start_timestamp) && (
                                <div className="xc-detail-row">
                                    <span className="xc-detail-label">Initiated</span>
                                    <span className="xc-detail-value">
                                        {fmtDate(xc.project_start_timestamp)}
                                    </span>
                                </div>
                            )}
                            <div className="xc-detail-row">
                                <span className="xc-detail-label">Exchange ID</span>
                                <span className="xc-detail-mono">{xc.exchange_id}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ExchangePage;
