// InteractionCard — a trust interaction in the MeaningTrail feed.
// Collapsed by default (single compact row); click anywhere to expand.
// When expanded, the title is a link to the interaction detail page.
// Trustifacts (verified gratitude records) and Shoutouts (kudos) have
// distinct visual identities and live in clearly labelled sections.

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useNavigate } from 'react-router-dom';
import LikeTimestamp from './LikeTimestamp';
import NewShoutoutForm from './NewShoutoutForm';
import StatusProgression from './StatusProgression';
import '../styles/MeaningTrail.css';

const IX_STEPS = ['Initiated', 'In Progress', 'Finished', 'Trustifacted', 'Additional Comments Added'];
const ixIndex = (status) => {
    const i = IX_STEPS.findIndex((s) => s.toLowerCase() === (status || '').toLowerCase());
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

const TYPE_LABELS = { completed: 'Completed', offer: 'Offer', request: 'Request' };
const TYPE_PILL  = { completed: 'pill-leaf', offer: 'pill-clay', request: 'pill-honey' };

function InteractionCard({
    id,
    type, title, spheres, participants, description,
    project, projectId, imageUrl, time, status,
    likesCount, likedByCurrentUser,
    initiatedTime, inProgressTime, finishedTime, trustifactedTime, additionalCommentsTime,
    trustifacts, shoutouts,
    onAddTrustifact, onAddShoutout, onModifyInteraction, canModify,
}) {
    const navigate = useNavigate();
    const [isExpanded, setIsExpanded] = useState(false);
    const [liked, setLiked] = useState(likedByCurrentUser);
    const [likes, setLikes] = useState(likesCount);
    const [showShoutoutForm, setShowShoutoutForm] = useState(false);
    const [img, setImg] = useState(imageUrl);
    // Local copies so newly submitted entries appear immediately without a refetch.
    const [localTrustifacts, setLocalTrustifacts] = useState(trustifacts || []);
    const [localShoutouts, setLocalShoutouts] = useState(shoutouts || []);

    const handleLike = (e) => {
        e.stopPropagation();
        setLiked((v) => !v);
        setLikes((n) => liked ? n - 1 : n + 1);
    };

    const handleTitleClick = (e) => {
        e.preventDefault();
        e.stopPropagation();
        if (id) navigate(`/interaction?id=${id}`);
    };

    const handleAddTrustifact = () => {
        const text = window.prompt('Enter your trustifact:');
        if (text && text.trim()) {
            const entry = { author: 'You', text: text.trim(), time: 'just now', likesCount: 0, likedByCurrentUser: false, imageUrl: null };
            setLocalTrustifacts((prev) => [...prev, entry]);
            onAddTrustifact();
        }
    };

    const handleAddShoutout = (shoutout) => {
        const entry = { author: 'You', text: shoutout.text, time: 'just now', likesCount: 0, likedByCurrentUser: false };
        setLocalShoutouts((prev) => [...prev, entry]);
        onAddShoutout(shoutout);
        setShowShoutoutForm(false);
    };

    const cancelled = status === 'Cancelled';
    const stepIdx = ixIndex(status);
    const steps = IX_STEPS.map((label, i) => ({
        label,
        time: [initiatedTime, inProgressTime, finishedTime, trustifactedTime, additionalCommentsTime][i] || '',
    }));

    const hasTrustifacts = localTrustifacts.length > 0;
    const hasShoutouts = localShoutouts.length > 0;
    const pillClass = TYPE_PILL[type] || 'pill-clay';
    const typeLabel = TYPE_LABELS[type] || type;

    return (
        <div
            className={`interaction ${type} ${isExpanded ? 'expanded' : 'collapsed'}`}
            onClick={() => !isExpanded && setIsExpanded(true)}
        >
            {/* ── Summary row — always visible ────────────────────────────── */}
            <div className="ix-summary" onClick={() => setIsExpanded(!isExpanded)}>
                <span className={`pill ${pillClass} type-pill`}>{typeLabel}</span>

                <div className="ix-title-col">
                    {isExpanded ? (
                        <a
                            className="ix-title ix-title-link"
                            href={id ? `/interaction?id=${id}` : '#'}
                            onClick={handleTitleClick}
                            title="View full interaction"
                        >
                            {title}
                        </a>
                    ) : (
                        <span className="ix-title">{title}</span>
                    )}
                    {!isExpanded && participants.length > 0 && (
                        <span className="ix-participants-inline">
                            {participants.map((p, i) => (
                                <React.Fragment key={i}>
                                    <a href={pHref(p)} onClick={(e) => e.stopPropagation()}>{pName(p)}</a>
                                    {i < participants.length - 1 ? ' · ' : ''}
                                </React.Fragment>
                            ))}
                        </span>
                    )}
                </div>

                <div className="ix-summary-meta" onClick={(e) => e.stopPropagation()}>
                    {time && <span className="ix-date">{time}</span>}
                    <LikeTimestamp
                        likedByCurrentUser={liked}
                        likesCount={likes}
                        time=""
                        onLike={handleLike}
                    />
                </div>

                <button
                    className="ix-expand-btn"
                    onClick={(e) => { e.stopPropagation(); setIsExpanded(!isExpanded); }}
                    aria-label={isExpanded ? 'Collapse' : 'Expand'}
                >
                    {isExpanded ? '▲' : '▼'}
                </button>
            </div>

            {/* ── Expanded body ─────────────────────────────────────────── */}
            {isExpanded && (
                <div className="ix-body" onClick={(e) => e.stopPropagation()}>
                    {/* Context: participants, spheres, project */}
                    <div className="ix-context">
                        <div className="participants">
                            {participants.map((p, i) => (
                                <span key={i}>
                                    <a href={pHref(p)}>{pName(p)}</a>
                                    {i < participants.length - 1 ? ' · ' : ''}
                                </span>
                            ))}
                        </div>
                        {spheres.length > 0 && (
                            <div className="ix-spheres">
                                {spheres.map((s, i) => (
                                    <a key={i} href={sHref(s)} className="pill pill-leaf ix-sphere-pill">
                                        {sName(s)}
                                    </a>
                                ))}
                            </div>
                        )}
                        {project && (
                            <div className="ix-project-ref">
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
                                    className="interaction-image"
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

                    {/* ── Trustifacts ───────────────────────────────────── */}
                    <div className="ix-section">
                        <div className="ix-section-label ix-section-trustifact">
                            <span>✓ Trustifacts</span>
                            <span className="ix-section-hint">verified attestations of trust</span>
                        </div>
                        {hasTrustifacts ? (
                            <div className="trustifacts">
                                {localTrustifacts.map((tf, i) => (
                                    <div key={i} className="trustifact">
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
                            <p className="ix-empty-section">No trustifacts yet.</p>
                        )}
                        <button
                            className="ix-add-btn ix-add-trustifact"
                            onClick={(e) => { e.stopPropagation(); handleAddTrustifact(); }}
                        >
                            + Add Trustifact
                        </button>
                    </div>

                    {/* ── Shoutouts ─────────────────────────────────────── */}
                    <div className="ix-section">
                        <div className="ix-section-label ix-section-shoutout">
                            <span>📢 Shoutouts</span>
                            <span className="ix-section-hint">public acknowledgements</span>
                        </div>
                        {hasShoutouts && (
                            <div className="shoutouts">
                                {localShoutouts.map((s, i) => (
                                    <div key={i} className="shoutout">
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
                        {!showShoutoutForm ? (
                            <button
                                className="ix-add-btn ix-add-shoutout"
                                onClick={(e) => { e.stopPropagation(); setShowShoutoutForm(true); }}
                            >
                                + Add Shoutout
                            </button>
                        ) : (
                            <NewShoutoutForm
                                onSave={handleAddShoutout}
                                onCancel={() => setShowShoutoutForm(false)}
                            />
                        )}
                    </div>
                </div>
            )}
        </div>
    );
}

InteractionCard.propTypes = {
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
    trustifactedTime: PropTypes.string,
    additionalCommentsTime: PropTypes.string,
    trustifacts: PropTypes.array,
    shoutouts: PropTypes.array,
    onAddTrustifact: PropTypes.func.isRequired,
    onAddShoutout: PropTypes.func.isRequired,
    onModifyInteraction: PropTypes.func.isRequired,
    canModify: PropTypes.bool.isRequired,
};

export default InteractionCard;
