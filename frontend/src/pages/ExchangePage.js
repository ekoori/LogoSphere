import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { useLogin } from '../App';
import api from '../api';
import StatusProgression from '../components/StatusProgression';
import ValueCardChip from '../components/ValueCardChip';
import ValueCardPicker from '../components/ValueCardPicker';
import { hoursGiven } from '../utils/effort';
import Avatar from '../components/Avatar';
import PhotoInput from '../components/PhotoInput';
import { useSimple } from '../utils/useSimple';
import { Picture } from '../components/AiTag';
import { Acknowledge, AcknowledgementRun } from '../components/Acknowledgements';
import { forUpload } from '../utils/pictures';
import * as rules from '../utils/exchangeRules';
import { XC_STEPS, XC_FOLLOWUP_STEP, XC_FOLLOWUP_STATUS } from '../utils/exchangeRules';
import { formatServerDate } from '../utils/dates';
import { DemoTag, PersonaTag } from '../components/DemoTags';
import { messagesHref } from '../utils/thread';
import '../styles/Sharing.css';
import '../styles/Exchange.css';
import '../styles/MeaningTrail.css';
import '../styles/ValueCardChip.css';
import '../styles/Messages.css';

const fmtDate = (val) => formatServerDate(val);

// Author name + avatar, linked to the profile ("You" → own profile).
const AuthorTag = ({ name, id }) => {
    const href = name === 'You' ? '/profile' : (id ? `/user?id=${id}` : null);
    return (
        <span className="tf-author">
            <Avatar userId={id} name={name === 'You' ? '' : name} size={20} />
            {href ? <Link to={href}><strong>{name}</strong></Link> : <strong>{name}</strong>}
        </span>
    );
};

const TYPE_LABEL = { completed: 'Completed', offer: 'Offer', need: 'Need' };
const TYPE_PILL  = { completed: 'pill-leaf', offer: 'pill-clay', need: 'pill-honey' };

// Link a participant to their page — a person to /user, a group to its own page.
const ENTITY_PATH = { sphere: 'sphere', alliance: 'alliance', project: 'project' };
const partHref = (kind, id) => {
    if (!id) return null;
    return ENTITY_PATH[kind] ? `/${ENTITY_PATH[kind]}?id=${id}` : `/user?id=${id}`;
};
const KIND_GLYPH = { sphere: '✦', alliance: '◈', project: '◻' };

// "Message" for whoever is on a side, shown only to the other: the human there, if any.
function MessageOtherSide({ xc, isInitiator, isOther, userId }) {
    if (!isInitiator && !isOther) return null;
    const other = isInitiator
        ? { id: xc.recipient_acting_user_id || (xc.other_kind === 'user' ? xc.other_user_id : null), agent: xc.other_is_agent }
        : { id: xc.initiator_acting_user_id || (xc.initiator_kind === 'user' ? xc.user_id : null), agent: xc.initiator_is_agent };
    if (!other.id || other.agent || String(other.id) === String(userId)) return null;
    return <Link className="msg-link" to={messagesHref(other.id, xc.source_service_id)}>Send a message</Link>;
}

// One participant row: differentiates a person from a group, shows "You" only
// for the viewer when they're a person, and "· via <human>" when a person acted
// on a group's behalf.
const ParticipantRow = ({ kind, id, name, actingId, actingName, role, isYou, isAgent }) => {
    const isEntity = kind && kind !== 'user';
    const href = partHref(kind, id);
    return (
        <div className="xc-participant">
            <span>{isEntity ? (KIND_GLYPH[kind] || '◻') : '👤'}</span>
            {isYou
                ? <Link to="/profile" className="xc-participant-you">You</Link>
                : (href ? <Link to={href}>{name}</Link> : <span>{name}</span>)}
            {/* The persona label goes next to a person: for a group, the one acting for it. */}
            {isAgent && !isEntity && !isYou && <PersonaTag compact />}
            {isEntity && actingName && (
                <span className="xc-participant-via">
                    {' · via '}
                    {actingId ? <Link to={`/user?id=${actingId}`}>{actingName}</Link> : actingName}
                    {isAgent && <PersonaTag compact />}
                </span>
            )}
            <span className="xc-participant-role">{role}</span>
        </div>
    );
};

function ExchangePage() {
    const simple = useSimple();
    const [searchParams] = useSearchParams();
    const xcId = searchParams.get('id');
    const { userId } = useLogin();

    const [xc, setXc] = useState(null);
    const [isInitiator, setIsInitiator] = useState(false);
    const [isOther, setIsOther] = useState(false);
    const [loading, setLoading] = useState(true);
    const [fetchError, setFetchError] = useState(null);

    const [gratitudeText, setGratitudeText] = useState('');
    const [userNoteText, setUserNoteText] = useState('');
    const [commentText, setCommentText] = useState('');
    const [submitting, setSubmitting] = useState(false);

    const [gratitudeCardIds, setGratitudeCardIds] = useState([]);
    const [gratitudeCards, setGratitudeCards] = useState([]);
    // Which of Frankl's three kinds of meaning the receipt records.
    const [gratitudeMode, setGratitudeMode] = useState('');
    const [userNoteCardIds, setUserNoteCardIds] = useState([]);
    const [userNoteCards, setUserNoteCards] = useState([]);

    // Receipt context (Time/Effort/Care/...) + up to 3 photos.
    const [gratitudeContext, setGratitudeContext] = useState('');
    const [gratitudeHours, setGratitudeHours] = useState('');
    const [gratitudePhotos, setGratitudePhotos] = useState([]);
    const [receiptError, setReceiptError] = useState('');
    const [canAcknowledge, setCanAcknowledge] = useState(false);
    // Two-step cancel: first click asks, second confirms (no modal dialogs).
    const [confirmCancel, setConfirmCancel] = useState(false);
    // The server's reason when a status change is refused, shown in Actions.
    const [actionError, setActionError] = useState(null);

    // Exchange edit (title / description / image), allowed until finished.
    const [editing, setEditing] = useState(false);
    const [editTitle, setEditTitle] = useState('');
    const [editDesc, setEditDesc] = useState('');
    const [editImage, setEditImage] = useState(null);
    const [editError, setEditError] = useState('');

    const openEdit = () => {
        setEditTitle(xc?.exchange_description || '');
        setEditDesc(xc?.exchange_long_description || '');
        setEditImage(null);
        setEditError('');
        setEditing(true);
    };
    const handleEditSubmit = async (e) => {
        e.preventDefault();
        if (submitting) return;
        setSubmitting(true);
        try {
            const fd = new FormData();
            fd.append('title', editTitle);
            fd.append('description', editDesc);
            if (editImage) fd.append('image', await forUpload(editImage));
            await api.post(`/api/exchange/${xcId}/edit`, fd);
            setEditing(false);
            await fetchXc();
        } catch (err) {
            setEditError(err.response?.data?.message || "Your changes couldn't be saved. Try again.");
        } finally {
            setSubmitting(false);
        }
    };

    // Receipt submit that also carries the Context note and up to 3 photos.
    const submitGratitude = async () => {
        if (!gratitudeText.trim() || submitting) return;
        setSubmitting(true);
        setReceiptError('');
        let posted = false;
        try {
            const photos = await Promise.all(gratitudePhotos.slice(0, 3).map(forUpload));
            await api.post(`/api/exchange/${xcId}/comment`, {
                type: 'gratitude', text: gratitudeText.trim(),
                card_ids: gratitudeCardIds, cards: gratitudeCards,
                frankl_mode: (!simple && gratitudeMode) || null,
                context: (!simple && gratitudeContext.trim()) || null,
                hours: gratitudeHours === '' ? null : Number(gratitudeHours),
            });
            posted = true;
            if (photos.length > 0) {
                const fd = new FormData();
                photos.forEach((p) => fd.append('photos', p));
                await api.post(`/api/exchange/${xcId}/receipt_photos`, fd);
            }
            setGratitudeText(''); setGratitudeContext(''); setGratitudeHours(''); setGratitudePhotos([]);
            setGratitudeCardIds([]); setGratitudeCards([]); setGratitudeMode('');
            await fetchXc();
        } catch (err) {
            console.error('Failed to add receipt:', err);
            const why = err.response?.data?.message;
            setReceiptError(posted
                ? `Your receipt was saved, but not its photos.${why ? ` ${why}` : ''}`
                : (why || "Your receipt couldn't be saved. Try again."));
            if (posted) await fetchXc();
        } finally {
            setSubmitting(false);
        }
    };

    const fetchXc = useCallback(async () => {
        if (!xcId) { setFetchError('No exchange ID provided.'); setLoading(false); return; }
        try {
            const res = await api.get(`/api/exchange/${xcId}`);
            setXc(res.data.exchange);
            setCanAcknowledge(!!res.data.can_acknowledge);
            setIsInitiator(res.data.is_initiator);
            setIsOther(res.data.is_other);
        } catch (e) {
            setFetchError(
                e.response?.status === 404
                    ? 'Exchange not found.'
                    : 'Could not load exchange. Please try again.'
            );
        } finally {
            setLoading(false);
        }
    }, [xcId]);

    useEffect(() => { fetchXc(); }, [fetchXc]);

    if (loading) return <div className="xc-loading">Loading exchange…</div>;
    if (fetchError || !xc) return <div className="xc-error-state">{fetchError || 'Exchange not found.'}</div>;

    // Use the backend's flag (not a raw id match) so a human acting for an
    // entity recipient is recognised as the "other" side and can add the receipt.
    const isOtherUser = isOther;
    const canModify = isInitiator || isOtherUser;
    // Both sides have receipted → the receipt affordance becomes a lighter comment.
    const bothReceipted = !!(xc.gratitude_comment && xc.user_comment);
    // What may happen next (utils/exchangeRules.js — the backend's transitions).
    const isCancelled = rules.isCancelled(xc);
    const currentIdx = isCancelled ? 0 : rules.stepIndex(xc.exchange_status);
    const nextStatus = rules.nextStatus(xc);
    const canCancel = rules.canCancel(xc, isInitiator);
    const awaitingReceipt = rules.awaitingReceipt(xc);

    const completed = ['Finished', 'Receipted', XC_FOLLOWUP_STATUS].includes(xc.exchange_status);
    const xcType = completed ? 'completed' : 'offer';
    const pillClass = TYPE_PILL[xcType] || 'pill-clay';
    const typeLabel = TYPE_LABEL[xcType] || xcType;

    // The follow-up step only appears once a follow-up note has been left; when
    // present it's the terminal state.
    const hasFollowup = rules.hasFollowup(xc);
    const stepLabels = hasFollowup ? [...XC_STEPS, XC_FOLLOWUP_STEP] : XC_STEPS;
    // Each stage shows the date it was reached (Initiated = when the exchange
    // was created; the rest from the per-stage transition timestamps).
    const STAGE_TIME = {
        'Initiated': xc.project_start_timestamp,
        'In Progress': xc.in_progress_at,
        'Finished': xc.finished_at,
        'Receipted': xc.receipted_at,
        [XC_FOLLOWUP_STEP]: xc.initiator_comment_timestamp || xc.recipient_comment_timestamp,
    };
    const steps = stepLabels.map((label) => ({ label, time: fmtDate(STAGE_TIME[label]) }));
    const progressIdx = hasFollowup ? stepLabels.length - 1 : currentIdx;

    const handleAdvanceStatus = async () => {
        if (!nextStatus) return;
        setActionError(null);
        try {
            await api.post(`/api/exchange/${xcId}/status`, { status: nextStatus });
            fetchXc();
        } catch (e) {
            setActionError(e.response?.data?.message || 'Could not update the status. Please try again.');
        }
    };

    const handleCancel = async () => {
        if (!confirmCancel) { setConfirmCancel(true); return; }
        setConfirmCancel(false);
        setActionError(null);
        try {
            await api.post(`/api/exchange/${xcId}/status`, { status: 'Cancelled' });
            fetchXc();
        } catch (e) {
            setActionError(e.response?.data?.message || 'Could not cancel the exchange. Please try again.');
        }
    };

    const submitComment = async (type, text, clearFn, cardIds = [], clearCardsFn = null, cards = [], clearFullCardsFn = null) => {
        if (!text.trim() || submitting) return;
        setSubmitting(true);
        try {
            await api.post(`/api/exchange/${xcId}/comment`, { type, text: text.trim(), card_ids: cardIds, cards });
            clearFn('');
            if (clearCardsFn) clearCardsFn([]);
            if (clearFullCardsFn) clearFullCardsFn([]);
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
                    {xc.is_demo && <DemoTag />}
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
                <StatusProgression steps={steps} currentIndex={progressIdx} cancelled={isCancelled} />
            </div>

            {/* ── Body ─────────────────────────────────────────────────── */}
            <div className="xc-page-body">
                {/* Main content */}
                <div className="xc-page-main">
                    {/* About */}
                    <div className="xc-page-section">
                        <div className="xc-about-head">
                            <p className="xc-page-section-heading">About this exchange</p>
                            {canModify && !xc.is_finished && !isCancelled && !editing && (
                                <button className="xc-add-btn xc-edit-btn" onClick={openEdit}>✎ Edit</button>
                            )}
                        </div>

                        {editing ? (
                            <form className="xc-edit-form" onSubmit={handleEditSubmit}>
                                <label>Title</label>
                                <input type="text" value={editTitle} onChange={(e) => setEditTitle(e.target.value)} />
                                <label>Description</label>
                                <textarea rows={3} value={editDesc} onChange={(e) => setEditDesc(e.target.value)} />
                                <label>Banner image</label>
                                <input type="file" accept="image/*" onChange={(e) => setEditImage(e.target.files?.[0] || null)} />
                                {editError && <p className="xc-receipt-error" role="alert">{editError}</p>}
                                <div className="xc-edit-actions">
                                    <button type="submit" className="btn btn-primary" disabled={submitting}>
                                        {submitting ? 'Saving…' : 'Save changes'}
                                    </button>
                                    <button type="button" className="btn btn-ghost" onClick={() => setEditing(false)}>Cancel</button>
                                </div>
                            </form>
                        ) : (
                            <>
                                {xc.has_image && (
                                    <Picture isAi={!!xc.image_is_ai} src={`/api/exchange/${xcId}/image`} alt="" className="xc-exchange-image" />
                                )}
                                {/* Only what the people wrote - no stand-in text. */}
                                {xc.exchange_long_description && (
                                    <p className="xc-about-text">{xc.exchange_long_description}</p>
                                )}
                                {xc.borrow && (
                                    <p className="loan-note">
                                        {['Initiated', 'In Progress'].includes(xc.exchange_status || 'Initiated')
                                            ? "A loan. Mark the exchange finished when it's back."
                                            : 'This was a loan.'}
                                    </p>
                                )}
                                {xc.is_finished && (
                                    <p className="xc-finished-note">✓ This exchange is finished — its details are now locked.</p>
                                )}
                                {xc.project_id && xc.project_name && (
                                    <Link
                                        to={`/project?id=${xc.project_id}`}
                                        className="pill pill-leaf"
                                        style={{ fontSize: '0.8rem', textDecoration: 'none' }}
                                    >
                                        {xc.project_name}
                                    </Link>
                                )}
                            </>
                        )}
                    </div>

                    {/* ── Receipts ──────────────────────────────────────── */}
                    <div className="xc-page-section">
                        <div className="xc-section-label xc-section-receipt" style={{ marginBottom: '0.9em' }}>
                            <span>✓ Receipts</span>
                            <span className="xc-section-hint">{simple ? 'thanks, in their own words' : 'verified attestations of trust'}</span>
                        </div>

                        {xc.gratitude_comment && (
                            <div className="receipt">
                                <div className="tf-content">
                                    <p className="tf-author-line">
                                        <AuthorTag name={xc.other_user_name || 'Other party'} id={xc.other_user_id} />{' '}
                                        {!simple && xc.gratitude_frankl_mode && (
                                            <span className="vc-receipt-mode" title={`${xc.gratitude_frankl_mode} meaning`}>
                                                {{ creative: '✶', experiential: '❍', attitudinal: '△' }[xc.gratitude_frankl_mode]} {xc.gratitude_frankl_mode}
                                            </span>
                                        )}
                                        {xc.gratitude_comment}
                                    </p>
                                    {xc.gratitude_comment_cards?.length > 0 && (
                                        <div className="comment-value-chips">
                                            <span className="comment-vc-label">values</span>
                                            {xc.gratitude_comment_cards.map((c, ci) => (
                                                <ValueCardChip key={c.card_id || ci} card={c} subjectLabel="Cares about" />
                                            ))}
                                        </div>
                                    )}
                                    {xc.effort_hours > 0 && <p className="xc-hours-given">{hoursGiven(xc.effort_hours)}</p>}
                                    {xc.gratitude_comment_context && (
                                        <div className="xc-context-block">
                                            <span className="xc-context-label">Context</span>
                                            <pre className="xc-context-text">{xc.gratitude_comment_context}</pre>
                                        </div>
                                    )}
                                    {xc.receipt_photo_count > 0 && (
                                        <div className="xc-receipt-photos">
                                            {Array.from({ length: xc.receipt_photo_count }).map((_, i) => (
                                                <a key={i} href={`/api/exchange/${xcId}/receipt_photo/${i}`} target="_blank" rel="noreferrer">
                                                    <img src={`/api/exchange/${xcId}/receipt_photo/${i}`} alt={`Receipt ${i + 1}`} className="xc-receipt-photo" />
                                                </a>
                                            ))}
                                        </div>
                                    )}
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
                                    <p className="tf-author-line">
                                        <AuthorTag name={isInitiator ? 'You' : (xc.initiator_name || 'Initiator')} id={xc.initiator_id || xc.user_id} />{' '}
                                        {xc.user_comment}
                                    </p>
                                    {xc.user_comment_cards?.length > 0 && (
                                        <div className="comment-value-chips">
                                            <span className="comment-vc-label">values</span>
                                            {xc.user_comment_cards.map((c, ci) => (
                                                <ValueCardChip key={c.card_id || ci} card={c} subjectLabel="Cares about" />
                                            ))}
                                        </div>
                                    )}
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
                                {!simple && <div className="vc-picker">
                                    <span className="vc-picker-label">What kind of meaning was this?</span>
                                    <div className="vc-picker-chips">
                                        {[['creative', '✶', 'Creative', 'something was made or given'],
                                          ['experiential', '❍', 'Experiential', 'something was received or shared'],
                                          ['attitudinal', '△', 'Attitudinal', 'a stance taken under constraint']].map(([k, g, l, t]) => (
                                            <button key={k} type="button" title={t}
                                                    className={`vc-picker-chip${gratitudeMode === k ? ' vc-picker-chip--on' : ''}`}
                                                    onClick={() => setGratitudeMode(gratitudeMode === k ? '' : k)}>
                                                <span className="vc-chip-glyph">{g}</span>
                                                <span className="vc-chip-title">{l}</span>
                                            </button>
                                        ))}
                                    </div>
                                </div>}
                                <ValueCardPicker
                                    selectedIds={gratitudeCardIds}
                                    onChange={(ids, cards) => { setGratitudeCardIds(ids); setGratitudeCards(cards); }}
                                    counterparts={(xc.initiator_id || xc.user_id) ? [{ id: xc.initiator_id || xc.user_id, label: `${xc.initiator_name || 'Their'} values` }] : []}
                                />
                                <label className="xc-comment-label xc-hours" style={{ marginTop: '0.6em' }}>
                                    <span>About how many hours did it take? <span className="xc-optional">Optional</span></span>
                                    <input type="number" inputMode="decimal" min="0.25" max="100" step="0.25"
                                           className="xc-hours-input" value={gratitudeHours}
                                           onChange={(e) => setGratitudeHours(e.target.value)} />
                                </label>
                                {!simple && (<>
                                <label className="xc-comment-label" style={{ marginTop: '0.6em' }}>Context (optional)</label>
                                <textarea
                                    className="xc-comment-input xc-context-input"
                                    placeholder={'Effort: moderate physical effort\nCare: high\nSkill: everyday\nConstraint: weekend morning'}
                                    rows={5}
                                    value={gratitudeContext}
                                    onChange={e => setGratitudeContext(e.target.value)}
                                />
                                </>)}
                                <label className="xc-comment-label" style={{ marginTop: '0.6em' }}>Photos (up to 3)</label>
                                <PhotoInput photos={gratitudePhotos} onChange={setGratitudePhotos} />
                                {!xc.is_demo && <small className="xc-section-hint">A receipt is evidence: real photos only, no AI pictures.</small>}
                                <button
                                    className="xc-comment-submit xc-submit-receipt"
                                    disabled={submitting || !gratitudeText.trim()}
                                    onClick={submitGratitude}
                                >
                                    + Add Receipt
                                </button>
                            </div>
                        )}

                        {receiptError && <p className="xc-receipt-error" role="alert">{receiptError}</p>}

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
                                <ValueCardPicker
                                    selectedIds={userNoteCardIds}
                                    onChange={(ids, cards) => { setUserNoteCardIds(ids); setUserNoteCards(cards); }}
                                />
                                <button
                                    className="xc-comment-submit xc-submit-receipt"
                                    disabled={submitting || !userNoteText.trim()}
                                    onClick={() => submitComment('user', userNoteText, setUserNoteText, userNoteCardIds, setUserNoteCardIds, userNoteCards, setUserNoteCards)}
                                >
                                    + Add Note
                                </button>
                            </div>
                        )}

                        {/* ── Follow-up comments — once both sides have receipted,
                            each may leave one lighter, less formal note. ─────── */}
                        {(xc.initiator_comment || xc.recipient_comment
                          || (bothReceipted && canModify)) && (
                            <div className="xc-followups">
                                <span className="xc-followups-label">Follow-up</span>
                                {xc.initiator_comment && (
                                    <div className="xc-followup">
                                        <strong>{isInitiator ? 'You' : (xc.initiator_name || 'Initiator')}:</strong>{' '}
                                        {xc.initiator_comment}
                                        {fmtDate(xc.initiator_comment_timestamp) && (
                                            <span className="xc-followup-date">{fmtDate(xc.initiator_comment_timestamp)}</span>
                                        )}
                                    </div>
                                )}
                                {xc.recipient_comment && (
                                    <div className="xc-followup">
                                        <strong>{isOtherUser ? 'You' : (xc.other_user_name || 'Recipient')}:</strong>{' '}
                                        {xc.recipient_comment}
                                        {fmtDate(xc.recipient_comment_timestamp) && (
                                            <span className="xc-followup-date">{fmtDate(xc.recipient_comment_timestamp)}</span>
                                        )}
                                    </div>
                                )}

                                {/* One comment per side. */}
                                {bothReceipted
                                    && ((isInitiator && !xc.initiator_comment) || (isOtherUser && !xc.recipient_comment)) && (
                                    <div className="xc-followup-add">
                                        <textarea
                                            className="xc-followup-input"
                                            placeholder="Add a brief follow-up comment…"
                                            value={commentText}
                                            onChange={e => setCommentText(e.target.value)}
                                        />
                                        <button
                                            className="xc-followup-submit"
                                            disabled={submitting || !commentText.trim()}
                                            onClick={() => submitComment('comment', commentText, setCommentText)}
                                        >
                                            Add comment
                                        </button>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>

                    {/* ── Acknowledgements ─────────────────────────────────────────── */}
                    <div className="xc-page-section">
                        <div className="xc-section-label xc-section-acknowledgement" style={{ marginBottom: '0.9em' }}>
                            <span>📢 Acknowledgements</span>
                            <span className="xc-section-hint">public acknowledgements</span>
                        </div>

                        {(xc.acknowledgements || []).length > 0
                            ? <AcknowledgementRun trailId={xc.exchange_id} items={xc.acknowledgements} onChanged={fetchXc} />
                            : <p className="xc-empty-section">No acknowledgements yet.</p>}
                        {canAcknowledge && (
                            <Acknowledge
                                trailId={xc.exchange_id}
                                onChanged={fetchXc}
                                counterparts={[
                                    { id: xc.user_id, label: `${xc.initiator_name || 'Their'} values` },
                                    { id: xc.other_user_id, label: `${xc.other_user_name || 'Their'} values` },
                                ].filter((c) => c.id)}
                            />
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
                            {canCancel && (
                                <>
                                    {confirmCancel && (
                                        <button type="button" className="xc-action-btn" onClick={() => setConfirmCancel(false)}>
                                            Keep it
                                        </button>
                                    )}
                                    <button className="xc-action-btn xc-action-secondary" onClick={handleCancel}>
                                        {confirmCancel ? 'Yes, cancel this exchange' : 'Cancel exchange'}
                                    </button>
                                </>
                            )}
                            {!nextStatus && (
                                <p style={{ fontSize: '0.82rem', color: 'var(--ink-faint)', margin: 0, fontStyle: 'italic' }}>
                                    {awaitingReceipt ? 'Finished — waiting for the receipt.' : 'Exchange is complete.'}
                                </p>
                            )}
                            {actionError && (
                                <p className="form-error" role="alert" style={{ margin: 0 }}>{actionError}</p>
                            )}
                        </div>
                    )}

                    {/* Participants */}
                    <div className="xc-sidebar-card">
                        <p className="xc-sidebar-heading">Participants</p>
                        <div className="xc-participants-list">
                            <ParticipantRow
                                kind={xc.initiator_kind}
                                id={xc.user_id}
                                name={xc.initiator_name || 'Initiator'}
                                actingId={xc.initiator_acting_user_id}
                                actingName={xc.initiator_acting_user_name}
                                role="Initiator"
                                isAgent={!!xc.initiator_is_agent}
                                isYou={xc.initiator_kind === 'user' && String(xc.user_id) === String(userId)}
                            />
                            {xc.other_user_id && (
                                <ParticipantRow
                                    kind={xc.other_kind}
                                    id={xc.other_user_id}
                                    name={xc.other_user_name || 'Recipient'}
                                    actingId={xc.recipient_acting_user_id}
                                    actingName={xc.recipient_acting_user_name}
                                    role="Recipient"
                                    isAgent={!!xc.other_is_agent}
                                    isYou={xc.other_kind === 'user' && String(xc.other_user_id) === String(userId)}
                                />
                            )}
                        </div>
                        <MessageOtherSide xc={xc} isInitiator={isInitiator} isOther={isOther} userId={userId} />
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
                                        <Link to={`/project?id=${xc.project_id}`}>{xc.project_name}</Link>
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
                            {xc.source_service_id && (
                                <div className="xc-detail-row">
                                    <span className="xc-detail-label">From opening</span>
                                    <span className="xc-detail-value">
                                        <Link to={`/opening?id=${xc.source_service_id}`}>View opening →</Link>
                                    </span>
                                </div>
                            )}
                            {!simple && (
                                <div className="xc-detail-row">
                                    <span className="xc-detail-label">Exchange ID</span>
                                    <span className="xc-detail-mono">{xc.exchange_id}</span>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </div>
        </div>
    );
}

export default ExchangePage;
