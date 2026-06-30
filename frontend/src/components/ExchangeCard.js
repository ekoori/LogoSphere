// ExchangeCard — a trust exchange in the MeaningTrail feed.
// Collapsed by default (single compact row); click anywhere to expand.
// When expanded, the title is a link to the exchange detail page.
// Receipts (verified gratitude records) and Acknowledgements (kudos) have
// distinct visual identities and live in clearly labelled sections.

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useNavigate } from 'react-router-dom';
import LikeTimestamp from './LikeTimestamp';
import NewAcknowledgementForm from './NewAcknowledgementForm';
import NewReceiptForm from './NewReceiptForm';
import StatusProgression from './StatusProgression';
import '../styles/MeaningTrail.css';

const XC_STEPS = ['Initiated', 'In Progress', 'Finished', 'Receipted', 'Additional Comments Added'];
const xcIndex = (status) => {
    const i = XC_STEPS.findIndex((s) => s.toLowerCase() === (status || '').toLowerCase());
    return i >= 0 ? i : 0;
};

// participants may be plain names or {id, name} pairs; "You" links to own profile.
const pName = (p) => (typeof p === 'string' ? p : p.name);
const pHref = (p) => {
    const name = pName(p);
    if (name === 'You') return '/profile';
    const id = typeof p === 'string' ? null : p.id;
    return id ? `/user?id=${id}` : '/user';
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
    project, projectId, imageUrl, time, status,
    likesCount, likedByCurrentUser,
    initiatedTime, inProgressTime, finishedTime, receiptedTime, additionalCommentsTime,
    receipts, acknowledgements,
    onAddReceipt, onAddAcknowledgement, onModifyExchange, canModify,
}) {
    const navigate = useNavigate();
    const [isExpanded, setIsExpanded] = useState(false);
    const [liked, setLiked] = useState(likedByCurrentUser);
    const [likes, setLikes] = useState(likesCount);
    const [showAcknowledgementForm, setShowAcknowledgementForm] = useState(false);
    const [showReceiptForm, setShowReceiptForm] = useState(false);
    const [img, setImg] = useState(imageUrl);
    // Local copies so newly submitted entries appear immediately without a refetch.
    const [localReceipts, setLocalReceipts] = useState(receipts || []);
    const [localAcknowledgements, setLocalAcknowledgements] = useState(acknowledgements || []);

    const handleLike = (e) => {
        e.stopPropagation();
        setLiked((v) => !v);
        setLikes((n) => liked ? n - 1 : n + 1);
    };

    const handleTitleClick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (id) navigate(`/exchange?id=${id}`);
    };

    const handleAddReceipt = (receipt) => {
        const entry = { author: 'You', text: receipt.text, time: 'just now', likesCount: 0, likedByCurrentUser: false, imageUrl: null };
        setLocalReceipts((prev) => [...prev, entry]);
        onAddReceipt();
        setShowReceiptForm(false);
    };

    const handleAddAcknowledgement = (acknowledgement) => {
        const entry = { author: 'You', text: acknowledgement.text, time: 'just now', likesCount: 0, likedByCurrentUser: false };
        setLocalAcknowledgements((prev) => [...prev, entry]);
        onAddAcknowledgement(acknowledgement);
        setShowAcknowledgementForm(false);
    };

    const cancelled = status === 'Cancelled';
    const stepIdx = xcIndex(status);
    const steps = XC_STEPS.map((label, i) => ({
        label,
        time: [initiatedTime, inProgressTime, finishedTime, receiptedTime, additionalCommentsTime][i] || '',
    }));

    const hasReceipts = localReceipts.length > 0;
    const hasAcknowledgements = localAcknowledgements.length > 0;
    const pillClass = TYPE_PILL[type] || 'pill-clay';
    const typeLabel = TYPE_LABELS[type] || type;

    return (
        <div
            className={`exchange ${type} ${isExpanded ? 'expanded' : 'collapsed'}`}
            onClick={() => !isExpanded && setIsExpanded(true)}
        >
            {/* ── Summary row — always visible ────────────────────────────── */}
            <div className="xc-summary" onClick={() => setIsExpanded(!isExpanded)}>
                <span className={`pill ${pillClass} type-pill`}>{typeLabel}</span>

                <div className="xc-title-col">
                    {isExpanded ? (
                        <a
                            className="xc-title xc-title-link"
                            href={id ? `/exchange?id=${id}` : '#'}
                            onClick={handleTitleClick}
                            title="View full exchange"
                        >
                            {title}
                        </a>
                    ) : (
                        <span className="xc-title">{title}</span>
                    )}
                    {!isExpanded && participants.length > 0 && (
                        <span className="xc-participants-inline">
                            {participants.map((p, i) => (
                                <React.Fragment key={i}>
                                    <a href={pHref(p)} onClick={(e) => e.stopPropagation()}>{pName(p)}</a>
                                    {i < participants.length - 1 ? ' · ' : ''}
                                </React.Fragment>
                            ))}
                        </span>
                    )}
                </div>

                <div className="xc-summary-meta" onClick={(e) => e.stopPropagation()}>
                    {time && <span className="xc-date">{time}</span>}
                    <LikeTimestamp
                        likedByCurrentUser={liked}
                        likesCount={likes}
                        time=""
                        onLike={handleLike}
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
                                    <a href={pHref(p)}>{pName(p)}</a>
                                    {i < participants.length - 1 ? ' · ' : ''}
                                </span>
                            ))}
                        </div>
                        {spheres.length > 0 && (
                            <div className="xc-spheres">
                                {spheres.map((s, i) => (
                                    <a key={i} href={sHref(s)} className="pill pill-leaf xc-sphere-pill">
                                        {sName(s)}
                                    </a>
                                ))}
                            </div>
                        )}
                        {project && (
                            <div className="xc-project-ref">
                                <span className="muted">Part of</span>{' '}
                                <a href={projectId ? `/project?id=${projectId}` : `/project?name=${encodeURIComponent(project)}`}>
                                    {project}
                                </a>
                            </div>
                        )}
                    </div>

                    {/* Description + image */}
                    {(img || description) && (
                        <div className="description-container">
                            {img && (
                                <img
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
                                            <p><strong>{tf.author}:</strong> {tf.text}</p>
                                        </div>
                                        <LikeTimestamp
                                            likedByCurrentUser={tf.likedByCurrentUser}
                                            likesCount={tf.likesCount}
                                            time={tf.time}
                                            onLike={(e) => e.stopPropagation()}
                                        />
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="xc-empty-section">No receipts yet.</p>
                        )}
                        {!showReceiptForm ? (
                            <button
                                className="xc-add-btn xc-add-receipt"
                                onClick={(e) => { e.stopPropagation(); setShowReceiptForm(true); }}
                            >
                                + Add Receipt
                            </button>
                        ) : (
                            <NewReceiptForm
                                onSave={handleAddReceipt}
                                onCancel={() => setShowReceiptForm(false)}
                            />
                        )}
                    </div>

                    {/* ── Acknowledgements ─────────────────────────────────────── */}
                    <div className="xc-section">
                        <div className="xc-section-label xc-section-acknowledgement">
                            <span>📢 Acknowledgements</span>
                            <span className="xc-section-hint">public acknowledgements</span>
                        </div>
                        {hasAcknowledgements && (
                            <div className="acknowledgements">
                                {localAcknowledgements.map((s, i) => (
                                    <div key={i} className="acknowledgement">
                                        <div className="tf-content">
                                            <p><strong>{s.author}:</strong> {s.text}</p>
                                        </div>
                                        <LikeTimestamp
                                            likedByCurrentUser={s.likedByCurrentUser}
                                            likesCount={s.likesCount}
                                            time={s.time}
                                            onLike={(e) => e.stopPropagation()}
                                        />
                                    </div>
                                ))}
                            </div>
                        )}
                        {!showAcknowledgementForm ? (
                            <button
                                className="xc-add-btn xc-add-acknowledgement"
                                onClick={(e) => { e.stopPropagation(); setShowAcknowledgementForm(true); }}
                            >
                                + Add Acknowledgement
                            </button>
                        ) : (
                            <NewAcknowledgementForm
                                onSave={handleAddAcknowledgement}
                                onCancel={() => setShowAcknowledgementForm(false)}
                            />
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

ExchangeCard.propTypes = {
    id: PropTypes.string,
    type: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    spheres: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.object])).isRequired,
    participants: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.object])).isRequired,
    description: PropTypes.string.isRequired,
    project: PropTypes.string,
    projectId: PropTypes.string,
    imageUrl: PropTypes.string,
    time: PropTypes.string.isRequired,
    status: PropTypes.string.isRequired,
    likesCount: PropTypes.number.isRequired,
    likedByCurrentUser: PropTypes.bool.isRequired,
    initiatedTime: PropTypes.string,
    inProgressTime: PropTypes.string,
    finishedTime: PropTypes.string,
    receiptedTime: PropTypes.string,
    additionalCommentsTime: PropTypes.string,
    receipts: PropTypes.array,
    acknowledgements: PropTypes.array,
    onAddReceipt: PropTypes.func.isRequired,
    onAddAcknowledgement: PropTypes.func.isRequired,
    onModifyExchange: PropTypes.func.isRequired,
    canModify: PropTypes.bool.isRequired,
};

export default ExchangeCard;
