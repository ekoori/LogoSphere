import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useLogin } from '../App';
import api from '../api';
import StatusProgression from '../components/StatusProgression';
import '../styles/Transaction.css';
import '../styles/MeaningTrail.css';

const TX_STEPS = ['Initiated', 'In Progress', 'Finished', 'Trustifacted', 'Additional Comments Added'];

const txIdx = (status) => {
    const i = TX_STEPS.findIndex(s => s.toLowerCase() === (status || '').toLowerCase());
    return i >= 0 ? i : 0;
};

const fmtDate = (val) => {
    if (!val) return '';
    const d = new Date(val);
    return isNaN(d.getTime()) ? '' : d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
};

const TYPE_LABEL = { completed: 'Completed', offer: 'Offer', request: 'Request' };
const TYPE_PILL  = { completed: 'pill-leaf', offer: 'pill-clay', request: 'pill-honey' };

function TransactionPage() {
    const [searchParams] = useSearchParams();
    const txId = searchParams.get('id');
    const { userId } = useLogin();

    const [tx, setTx] = useState(null);
    const [isInitiator, setIsInitiator] = useState(false);
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState(null);

    const [gratitudeText, setGratitudeText] = useState('');
    const [userNoteText, setUserNoteText] = useState('');
    const [shoutoutText, setShoutoutText] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const fetchTx = useCallback(async () => {
        if (!txId) { setFetchError('No transaction ID provided.'); setLoading(false); return; }
        try {
            const res = await api.get(`/api/transaction/${txId}`);
            setTx(res.data.transaction);
            setIsInitiator(res.data.is_initiator);
        } catch (e) {
            setFetchError(
                e.response?.status === 404
                    ? 'Transaction not found or you are not a participant.'
                    : 'Could not load transaction. Please try again.'
            );
        } finally {
            setLoading(false);
        }
    }, [txId]);

    useEffect(() => { fetchTx(); }, [fetchTx]);

    if (loading) return <div className="tx-loading">Loading transaction…</div>;
    if (fetchError || !tx) return <div className="tx-error-state">{fetchError || 'Transaction not found.'}</div>;

    const isOtherUser = String(tx.other_user_id) === String(userId);
    const canModify = isInitiator || isOtherUser;
    const isCancelled = tx.transaction_status === 'Cancelled';
    const currentIdx = isCancelled ? txIdx('Initiated') : txIdx(tx.transaction_status);
    const nextStatus = !isCancelled && currentIdx < TX_STEPS.length - 1 ? TX_STEPS[currentIdx + 1] : null;

    const completed = ['Finished', 'Trustifacted', 'Additional Comments Added'].includes(tx.transaction_status);
    const txType = completed ? 'completed' : 'offer';
    const pillClass = TYPE_PILL[txType] || 'pill-clay';
    const typeLabel = TYPE_LABEL[txType] || txType;

    const steps = TX_STEPS.map((label) => ({ label, time: '' }));

    const handleAdvanceStatus = async () => {
        if (!nextStatus) return;
        try {
            await api.post(`/api/transaction/${txId}/status`, { status: nextStatus });
            fetchTx();
        } catch (e) {
            console.error('Failed to advance status:', e);
        }
    };

    const handleCancel = async () => {
        if (!window.confirm('Cancel this transaction? This cannot be undone.')) return;
        try {
            await api.post(`/api/transaction/${txId}/status`, { status: 'Cancelled' });
            fetchTx();
        } catch (e) {
            console.error('Failed to cancel:', e);
        }
    };

    const submitComment = async (type, text, clearFn) => {
        if (!text.trim() || submitting) return;
        setSubmitting(true);
        try {
            await api.post(`/api/transaction/${txId}/comment`, { type, text: text.trim() });
            clearFn('');
            fetchTx();
        } catch (e) {
            console.error('Failed to add comment:', e);
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="tx-page">
            {/* ── Hero ─────────────────────────────────────────────────── */}
            <div className="tx-page-hero">
                <div className="tx-page-breadcrumb">
                    <Link to="/profile">Meaning Trail</Link>
                    <span>›</span>
                    <span>{tx.transaction_description || 'Transaction'}</span>
                </div>

                <div className="tx-page-header">
                    <span className={`pill ${pillClass} type-pill`}>{typeLabel}</span>
                    <h1 className="tx-page-title">
                        {tx.transaction_description || 'An exchange of trust'}
                    </h1>
                    {isCancelled && <span className="pill pill-clay">Cancelled</span>}
                </div>

                <div className="tx-page-meta">
                    {fmtDate(tx.project_start_timestamp) && (
                        <span>{fmtDate(tx.project_start_timestamp)}</span>
                    )}
                    {tx.project_name && (
                        <>
                            <span>·</span>
                            <span>Part of <strong>{tx.project_name}</strong></span>
                        </>
                    )}
                </div>

                {isCancelled && (
                    <div className="tx-cancelled-banner">
                        This transaction was cancelled.
                    </div>
                )}
            </div>

            {/* ── Status timeline ───────────────────────────────────────── */}
            <div className="tx-page-timeline">
                <StatusProgression steps={steps} currentIndex={currentIdx} cancelled={isCancelled} />
            </div>

            {/* ── Body ─────────────────────────────────────────────────── */}
            <div className="tx-page-body">
                {/* Main content */}
                <div className="tx-page-main">
                    {/* About */}
                    <div className="tx-page-section">
                        <p className="tx-page-section-heading">About this exchange</p>
                        <p className="tx-about-text">
                            {tx.project_name
                                ? `An act of giving within the "${tx.project_name}" project.`
                                : 'A moment of trust shared in the community.'}
                        </p>
                        {tx.project_id && tx.project_name && (
                            <Link
                                to={`/project?id=${tx.project_id}`}
                                className="pill pill-leaf"
                                style={{ fontSize: '0.8rem', textDecoration: 'none' }}
                            >
                                {tx.project_name}
                            </Link>
                        )}
                    </div>

                    {/* ── Trustifacts ──────────────────────────────────────── */}
                    <div className="tx-page-section">
                        <div className="tx-section-label tx-section-trustifact" style={{ marginBottom: '0.9em' }}>
                            <span>✓ Trustifacts</span>
                            <span className="tx-section-hint">verified attestations of trust</span>
                        </div>

                        {tx.gratitude_comment && (
                            <div className="trustifact">
                                <div className="tf-content">
                                    <p>
                                        <strong>{tx.other_user_name || 'Other party'}:</strong>{' '}
                                        {tx.gratitude_comment}
                                    </p>
                                    {fmtDate(tx.gratitude_comment_timestamp) && (
                                        <span className="tx-date" style={{ marginTop: '0.3em', display: 'block', fontSize: '0.74rem' }}>
                                            {fmtDate(tx.gratitude_comment_timestamp)}
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {tx.user_comment && (
                            <div className="trustifact" style={{ marginTop: tx.gratitude_comment ? '0.55em' : 0 }}>
                                <div className="tf-content">
                                    <p>
                                        <strong>{isInitiator ? 'You' : 'Initiator'}:</strong>{' '}
                                        {tx.user_comment}
                                    </p>
                                    {fmtDate(tx.user_comment_timestamp) && (
                                        <span className="tx-date" style={{ marginTop: '0.3em', display: 'block', fontSize: '0.74rem' }}>
                                            {fmtDate(tx.user_comment_timestamp)}
                                        </span>
                                    )}
                                </div>
                            </div>
                        )}

                        {!tx.gratitude_comment && !tx.user_comment && (
                            <p className="tx-empty-section">No trustifacts yet.</p>
                        )}

                        {/* Other party adds gratitude_comment */}
                        {isOtherUser && !tx.gratitude_comment && (
                            <div className="tx-comment-area">
                                <span className="tx-comment-label">Your trustifact</span>
                                <textarea
                                    className="tx-comment-input"
                                    placeholder="How did this exchange feel? What did it mean to you?"
                                    value={gratitudeText}
                                    onChange={e => setGratitudeText(e.target.value)}
                                />
                                <button
                                    className="tx-comment-submit tx-submit-trustifact"
                                    disabled={submitting || !gratitudeText.trim()}
                                    onClick={() => submitComment('gratitude', gratitudeText, setGratitudeText)}
                                >
                                    + Add Trustifact
                                </button>
                            </div>
                        )}

                        {/* Initiator adds user_comment */}
                        {isInitiator && !tx.user_comment && (
                            <div className="tx-comment-area">
                                <span className="tx-comment-label">Your note</span>
                                <textarea
                                    className="tx-comment-input"
                                    placeholder="Reflect on this exchange — what did you give and learn?"
                                    value={userNoteText}
                                    onChange={e => setUserNoteText(e.target.value)}
                                />
                                <button
                                    className="tx-comment-submit tx-submit-trustifact"
                                    disabled={submitting || !userNoteText.trim()}
                                    onClick={() => submitComment('user', userNoteText, setUserNoteText)}
                                >
                                    + Add Note
                                </button>
                            </div>
                        )}
                    </div>

                    {/* ── Shoutouts ─────────────────────────────────────────── */}
                    <div className="tx-page-section">
                        <div className="tx-section-label tx-section-shoutout" style={{ marginBottom: '0.9em' }}>
                            <span>📢 Shoutouts</span>
                            <span className="tx-section-hint">public acknowledgements</span>
                        </div>

                        {tx.other_comment ? (
                            <div className="shoutout">
                                <div className="tf-content">
                                    <p>
                                        <strong>{tx.other_comment_author_name || 'A participant'}:</strong>{' '}
                                        {tx.other_comment}
                                    </p>
                                    {fmtDate(tx.other_comment_timestamp) && (
                                        <span className="tx-date" style={{ marginTop: '0.3em', display: 'block', fontSize: '0.74rem' }}>
                                            {fmtDate(tx.other_comment_timestamp)}
                                        </span>
                                    )}
                                </div>
                            </div>
                        ) : (
                            <p className="tx-empty-section">No shoutouts yet.</p>
                        )}

                        {canModify && !tx.other_comment && (
                            <div className="tx-comment-area">
                                <span className="tx-comment-label">Add a shoutout</span>
                                <textarea
                                    className="tx-comment-input"
                                    placeholder="Celebrate this exchange publicly — let the community know!"
                                    value={shoutoutText}
                                    onChange={e => setShoutoutText(e.target.value)}
                                />
                                <button
                                    className="tx-comment-submit tx-submit-shoutout"
                                    disabled={submitting || !shoutoutText.trim()}
                                    onClick={() => submitComment('other', shoutoutText, setShoutoutText)}
                                >
                                    + Add Shoutout
                                </button>
                            </div>
                        )}
                    </div>
                </div>

                {/* ── Sidebar ───────────────────────────────────────────── */}
                <div className="tx-page-sidebar">
                    {/* Actions — only for participants */}
                    {canModify && !isCancelled && (
                        <div className="tx-sidebar-card">
                            <p className="tx-sidebar-heading">Actions</p>
                            {nextStatus && (
                                <button className="tx-action-btn tx-action-advance" onClick={handleAdvanceStatus}>
                                    Mark as {nextStatus}
                                </button>
                            )}
                            {isInitiator && (
                                <button className="tx-action-btn tx-action-secondary" onClick={handleCancel}>
                                    Cancel transaction
                                </button>
                            )}
                            {!nextStatus && (
                                <p style={{ fontSize: '0.82rem', color: 'var(--ink-faint)', margin: 0, fontStyle: 'italic' }}>
                                    Transaction is complete.
                                </p>
                            )}
                        </div>
                    )}

                    {/* Participants */}
                    <div className="tx-sidebar-card">
                        <p className="tx-sidebar-heading">Participants</p>
                        <div className="tx-participants-list">
                            <div className="tx-participant">
                                <span>👤</span>
                                {isInitiator
                                    ? <span className="tx-participant-you">You</span>
                                    : <a href={`/user?id=${tx.user_id}`}>Initiator</a>
                                }
                                <span className="tx-participant-role">Initiator</span>
                            </div>
                            {tx.other_user_id && (
                                <div className="tx-participant">
                                    <span>👤</span>
                                    {isOtherUser
                                        ? <span className="tx-participant-you">You</span>
                                        : <a href={`/user?id=${tx.other_user_id}`}>{tx.other_user_name || 'Recipient'}</a>
                                    }
                                    <span className="tx-participant-role">Recipient</span>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Details */}
                    <div className="tx-sidebar-card">
                        <p className="tx-sidebar-heading">Details</p>
                        <div className="tx-detail-rows">
                            <div className="tx-detail-row">
                                <span className="tx-detail-label">Status</span>
                                <span className="tx-detail-value tx-status-value">
                                    {tx.transaction_status || 'Initiated'}
                                </span>
                            </div>
                            {tx.project_name && (
                                <div className="tx-detail-row">
                                    <span className="tx-detail-label">Project</span>
                                    <span className="tx-detail-value">
                                        <a href={`/project?id=${tx.project_id}`}>{tx.project_name}</a>
                                    </span>
                                </div>
                            )}
                            {fmtDate(tx.project_start_timestamp) && (
                                <div className="tx-detail-row">
                                    <span className="tx-detail-label">Initiated</span>
                                    <span className="tx-detail-value">
                                        {fmtDate(tx.project_start_timestamp)}
                                    </span>
                                </div>
                            )}
                            <div className="tx-detail-row">
                                <span className="tx-detail-label">Transaction ID</span>
                                <span className="tx-detail-mono">{tx.transaction_id}</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default TransactionPage;
