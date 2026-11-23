// ExchangeCard — a trust exchange in the MeaningTrail feed.
// Collapsed by default (single compact row); click anywhere to expand.
// When expanded, the title is a link to the exchange detail page.
// Receipts (verified gratitude records) and Acknowledgements (kudos) have
// distinct visual identities and live in clearly labelled sections.

import React, { useEffect, useState } from 'react';
import PropTypes from 'prop-types';
import { Picture } from './AiTag';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';
import LikeTimestamp from './LikeTimestamp';
import { DemoTag, PersonaTag } from './DemoTags';
import { Acknowledge, AcknowledgementRun } from './Acknowledgements';
import WordsForm from './WordsForm';
import StatusProgression from './StatusProgression';
import ValueCardChip from './ValueCardChip';
import Avatar from './Avatar';
import { useEntityIndex } from '../utils/useEntityIndex';
import { showsPersonaTag } from '../utils/exchangeRules';
import { hoursGiven } from '../utils/effort';
import '../styles/MeaningTrail.css';
import '../styles/ValueCardChip.css';

// Author name + avatar, linked to the profile ("You" → own profile).
function CommentAuthor({ author, authorId }) {
    const href = author === 'You' ? '/profile' : (authorId ? `/user?id=${authorId}` : null);
    return (
        <span className="tf-author">
            <Avatar userId={authorId} name={author === 'You' ? '' : author} size={20} />
            {href ? <Link to={href}><strong>{author}</strong></Link> : <strong>{author}</strong>}
        </span>
    );
}

const XC_CORE_STEPS = ['Initiated', 'In Progress', 'Finished', 'Receipted'];
const XC_FOLLOWUP_STEP = 'Follow up added';
// Legacy status value stored server-side for the same concept.
const XC_FOLLOWUP_STATUS = 'Additional Comments Added';
// The 5th step only appears once it's actually relevant — either a follow-up
// note has been added, or the status has already been advanced there.
const xcSteps = (status, hasFollowupComment) =>
    hasFollowupComment || status === XC_FOLLOWUP_STATUS
        ? [...XC_CORE_STEPS, XC_FOLLOWUP_STEP]
        : XC_CORE_STEPS;
const xcIndex = (steps, status) => {
    const i = steps.findIndex((s) => s.toLowerCase() === (status || '').toLowerCase());
    return i >= 0 ? i : 0;
};

// participants may be plain names or {id, name, kind} pairs; "You" links to own
// profile, a group (alliance/project) to its own page, a person to /user.
const P_PATH = { sphere: 'sphere', alliance: 'alliance', project: 'project' };
const pName = (p) => (typeof p === 'string' ? p : p.name);
const pHref = (p) => {
    const name = pName(p);
    if (name === 'You') return '/profile';
    const id = typeof p === 'string' ? null : p.id;
    const kind = typeof p === 'string' ? null : p.kind;
    if (!id) return '/user';
    return P_PATH[kind] ? `/${P_PATH[kind]}?id=${id}` : `/user?id=${id}`;
};

// spheres may be strings or {id, name} pairs — prefer UUID link when available.
const sName = (s) => (typeof s === 'string' ? s : s.name);
const sHref = (s) => {
    const id = typeof s === 'string' ? null : s.id;
    return id ? `/sphere?id=${id}` : `/sphere?name=${encodeURIComponent(sName(s))}`;
};

const TYPE_LABELS = { completed: 'Completed', offer: 'Offer', need: 'Need' };
const TYPE_PILL  = { completed: 'pill-leaf', offer: 'pill-clay', need: 'pill-honey' };

function ExchangeCard({
    id,
    type, title, spheres, participants, description,
    project, projectId, imageUrl, imageIsAi = false, time, status,
    likesCount, likedByCurrentUser, likedBy: likedByInitial = [], canLike = true,
    initiatedTime, inProgressTime, finishedTime, receiptedTime, additionalCommentsTime,
    hasFollowupComment,
    receipts, acknowledgements,
    ownSide = null, hasNote = false, hasReceipt = false, onChanged, isDemo = false, effortHours = null,
}) {
    const navigate = useNavigate();
    const { entityHref } = useEntityIndex();
    const [isExpanded, setIsExpanded] = useState(false);
    const [liked, setLiked] = useState(likedByCurrentUser);
    const [likes, setLikes] = useState(likesCount);
    const [likedBy, setLikedBy] = useState(likedByInitial);
    const [showNoteForm, setShowNoteForm] = useState(false);
    const [img, setImg] = useState(imageUrl);
    // A copy for optimistic likes; it follows the server's after every refetch.
    const [localReceipts, setLocalReceipts] = useState(receipts || []);
    const written = JSON.stringify(receipts || []);
    useEffect(() => { setLocalReceipts(JSON.parse(written)); }, [written]);

    // Toggle the like on the exchange itself. Optimistic, rolled back on error.
    const handleLike = async (e) => {
        e.stopPropagation();
        if (!id) return;
        const prevLiked = liked, prevLikes = likes;
        setLiked((v) => !v);
        setLikes((n) => (liked ? n - 1 : n + 1));
        try {
            const res = await api.post(`/api/exchange/${id}/like`, { comment_type: 'exchange' });
            setLiked(res.data.liked);
            setLikes(res.data.count);
            setLikedBy(res.data.by || []);
        } catch (err) {
            setLiked(prevLiked);
            setLikes(prevLikes);
        }
    };

    // Toggle a like on one of the exchange's comments (gratitude / user / other).
    // Likes are keyed by (exchange_id, comment_type). An acknowledgement's are
    // its own (see Acknowledgements.js).
    const handleCommentLike = async (commentType) => {
        if (!id || !commentType) return;
        const apply = (fn) => setLocalReceipts((prev) => prev.map((it) =>
            it.commentType === commentType ? fn(it) : it));
        // optimistic
        apply((it) => ({
            ...it,
            likedByCurrentUser: !it.likedByCurrentUser,
            likesCount: (it.likesCount || 0) + (it.likedByCurrentUser ? -1 : 1),
        }));
        try {
            const res = await api.post(`/api/exchange/${id}/like`, { comment_type: commentType });
            apply((it) => ({ ...it, likedByCurrentUser: res.data.liked, likesCount: res.data.count, likedBy: res.data.by || [] }));
        } catch (err) {
            apply((it) => ({
                ...it,
                likedByCurrentUser: !it.likedByCurrentUser,
                likesCount: (it.likesCount || 0) + (it.likedByCurrentUser ? -1 : 1),
            }));
        }
    };

    const handleTitleClick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (id) navigate(`/exchange?id=${id}`);
    };

    // Shown once the server has it: these used to look posted on pages that saved nothing.
    const saveNote = async ({ text, cardIds }) => {
        await api.post(`/api/exchange/${id}/comment`, { type: 'user', text, card_ids: cardIds });
        setShowNoteForm(false);
        await onChanged();
    };
    const counterparts = (participants || [])
        .filter((p) => p && typeof p === 'object' && p.id && p.name !== 'You')
        .map((p) => ({ id: p.id, label: `${p.name}'s values` }));

    const cancelled = status === 'Cancelled';
    const hasFollowup = !!hasFollowupComment || status === XC_FOLLOWUP_STATUS;
    const xcStepLabels = xcSteps(status, hasFollowupComment);
    // When a follow-up exists it's the terminal step (the stored status may still
    // read "Receipted", so point the marker at the follow-up explicitly).
    const stepIdx = hasFollowup ? xcStepLabels.length - 1 : xcIndex(xcStepLabels, status);
    const stepTimes = [initiatedTime, inProgressTime, finishedTime, receiptedTime, additionalCommentsTime];
    const steps = xcStepLabels.map((label, i) => ({ label, time: stepTimes[i] || '' }));

    const hasReceipts = localReceipts.length > 0;
    const pillClass = TYPE_PILL[type] || 'pill-clay';
    // Where it has got to, in the words of its progress strip.
    const typeLabel = cancelled ? 'Cancelled' : (xcStepLabels[stepIdx] || TYPE_LABELS[type] || type);

    return (
        <div
            className={`xc-card ${type} ${isExpanded ? 'expanded' : 'collapsed'}`}
            onClick={() => !isExpanded && setIsExpanded(true)}
        >
            {/* ── Summary row — always visible ────────────────────────────── */}
            <div className="xc-summary" onClick={() => setIsExpanded(!isExpanded)}>
                <span className={`pill ${pillClass} type-pill`}>{typeLabel}</span>

                <div className="xc-title-col">
                    {isExpanded ? (
                        <Link
                            className="xc-title xc-title-link"
                            to={id ? `/exchange?id=${id}` : '#'}
                            onClick={handleTitleClick}
                            title="View full exchange"
                        >
                            {title}
                        </Link>
                    ) : (
                        <span className="xc-title">{title}</span>
                    )}
                    {isExpanded && isDemo && <DemoTag />}
                    {!isExpanded && (
                        <span className="xc-meta-inline">
                            {participants.map((p, i) => (
                                <React.Fragment key={i}>
                                    <Link to={pHref(p)} onClick={(e) => e.stopPropagation()}>{pName(p)}</Link>
                                    {showsPersonaTag(p) && <PersonaTag compact />}
                                    {i < participants.length - 1 && <span className="xc-dot" aria-hidden="true">·</span>}
                                </React.Fragment>
                            ))}
                            {effortHours > 0 && <span>· {hoursGiven(effortHours, { short: true })}</span>}
                            {isDemo && <DemoTag />}
                        </span>
                    )}
                </div>

                <div className="xc-summary-meta" onClick={(e) => e.stopPropagation()}>
                    {time && <span className="xc-date">{time}</span>}
                    <LikeTimestamp
                        likedByCurrentUser={liked}
                        likesCount={likes}
                        likedBy={likedBy}
                        time=""
                        onLike={handleLike}
                        canLike={canLike}
                    />
                </div>

                <button
                    className="xc-expand-btn"
                    onClick={(e) => { e.stopPropagation(); setIsExpanded(!isExpanded); }}
                    aria-label={isExpanded ? 'Collapse' : 'Expand'}
                >
                    {isExpanded ? '▲' : '▼'}
                </button>
            </div>

            {/* ── Expanded body ─────────────────────────────────────────── */}
            {isExpanded && (
                <div className="xc-body" onClick={(e) => e.stopPropagation()}>
                    {/* Context: participants, spheres, project */}
                    <div className="xc-context">
                        <div className="participants">
                            {participants.map((p, i) => (
                                <span key={i}>
                                    <Link to={pHref(p)}>{pName(p)}</Link>
                                    {showsPersonaTag(p) && <PersonaTag compact />}
                                    {i < participants.length - 1 ? ' · ' : ''}
                                </span>
                            ))}
                        </div>
                        {spheres.length > 0 && (
                            <div className="xc-spheres">
                                {spheres.map((s, i) => (
                                    <Link key={i} to={sHref(s)} className="pill pill-leaf xc-sphere-pill">
                                        {sName(s)}
                                    </Link>
                                ))}
                            </div>
                        )}
                        {project && (
                            <div className="xc-project-ref">
                                <span className="muted">Part of</span>{' '}
                                <Link to={entityHref('project', project, projectId)}>
                                    {project}
                                </Link>
                            </div>
                        )}
                    </div>

                    {/* Description + image */}
                    {(img || description) && (
                        <div className="description-container">
                            {img && (
                                <Picture
                                    isAi={imageIsAi}
                                    short
                                    src={img}
                                    alt={title}
                                    className="exchange-image"
                                    onError={() => setImg(null)}
                                />
                            )}
                            <p className="description">{description}</p>
                        </div>
                    )}

                    {/* Status progression */}
                    <div className="status">
                        <StatusProgression steps={steps} currentIndex={stepIdx} cancelled={cancelled} />
                    </div>

                    {/* ── Receipts ───────────────────────────────────── */}
                    <div className="xc-section">
                        <div className="xc-section-label xc-section-receipt">
                            <span>✓ Receipts</span>
                            <span className="xc-section-hint">verified attestations of trust</span>
                        </div>
                        {hasReceipts ? (
                            <div className="receipts">
                                {localReceipts.map((tf, i) => (
                                    <div key={i} className="receipt">
                                        <div className="tf-content">
                                            <p className="tf-author-line"><CommentAuthor author={tf.author} authorId={tf.authorId} /> {tf.text}</p>
                                            {tf.cards?.length > 0 && (
                                                <div className="comment-value-chips">
                                                    <span className="comment-vc-label">values</span>
                                                    {tf.cards.map((c, ci) => (
                                                        <ValueCardChip key={c.card_id || ci} card={c} subjectLabel="Cares about" />
                                                    ))}
                                                </div>
                                            )}
                                        </div>
                                        <LikeTimestamp
                                            likedByCurrentUser={tf.likedByCurrentUser}
                                            likesCount={tf.likesCount}
                                            likedBy={tf.likedBy}
                                            time={tf.time}
                                            onLike={(e) => { e.stopPropagation(); handleCommentLike(tf.commentType); }}
                                            canLike={tf.canLike !== false}
                                        />
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="xc-empty-section">No receipts yet.</p>
                        )}
                        {!cancelled && ownSide === 'initiator' && !hasNote && (showNoteForm ? (
                            <WordsForm
                                placeholder="What did you give, and what did it mean to you?"
                                submitLabel="Save my note"
                                counterparts={counterparts}
                                onSave={saveNote}
                                onCancel={() => setShowNoteForm(false)}
                            />
                        ) : (
                            <button
                                className="xc-add-btn xc-add-receipt"
                                onClick={(e) => { e.stopPropagation(); setShowNoteForm(true); }}
                            >
                                + Add your note
                            </button>
                        ))}
                        {/* The receipt is written on the exchange's page, where its photos are taken. */}
                        {!cancelled && ownSide === 'recipient' && !hasReceipt && (
                            <Link className="xc-add-btn xc-add-receipt" to={`/exchange?id=${id}`}>Write your receipt →</Link>
                        )}
                    </div>

                    {/* ── Acknowledgements ─────────────────────────────────────── */}
                    <div className="xc-section">
                        <div className="xc-section-label xc-section-acknowledgement">
                            <span>📢 Acknowledgements</span>
                            <span className="xc-section-hint">public acknowledgements</span>
                        </div>
                        <AcknowledgementRun trailId={id} items={acknowledgements || []} onChanged={onChanged} />
                        <Acknowledge trailId={id} counterparts={counterparts} onChanged={onChanged} />
                    </div>
                </div>
            )}
        </div>
    );
}

ExchangeCard.propTypes = {
    id: PropTypes.string,
    isDemo: PropTypes.bool,
    effortHours: PropTypes.number,
    type: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    spheres: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.object])).isRequired,
    participants: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.object])).isRequired,
    description: PropTypes.string.isRequired,
    project: PropTypes.string,
    projectId: PropTypes.string,
    imageUrl: PropTypes.string,
    imageIsAi: PropTypes.bool,
    time: PropTypes.string.isRequired,
    status: PropTypes.string.isRequired,
    likesCount: PropTypes.number.isRequired,
    likedByCurrentUser: PropTypes.bool.isRequired,
    initiatedTime: PropTypes.string,
    inProgressTime: PropTypes.string,
    finishedTime: PropTypes.string,
    receiptedTime: PropTypes.string,
    additionalCommentsTime: PropTypes.string,
    hasFollowupComment: PropTypes.bool,
    receipts: PropTypes.array,
    acknowledgements: PropTypes.array,
    ownSide: PropTypes.oneOf(['initiator', 'recipient']),
    hasNote: PropTypes.bool,
    hasReceipt: PropTypes.bool,
    onChanged: PropTypes.func.isRequired,
};

export default ExchangeCard;
