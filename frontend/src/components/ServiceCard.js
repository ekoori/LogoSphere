// ServiceCard — a openings offer or need card.
// Status shown via shared StatusProgression; project is a read-only indication.
// Spheres accept {id, name} pairs so links use UUID when available.

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';
import LikeTimestamp from './LikeTimestamp';
import StatusProgression from './StatusProgression';
import Avatar from './Avatar';
import { buildOpeningProgress } from '../utils/openingProgress';
import { useManagedEntities } from '../utils/useManagedEntities';
import '../styles/Openings.css';

// Spheres may be strings or {id, name} pairs — prefer UUID link when available.
const sName = (s) => (typeof s === 'string' ? s : s.name);
const sHref = (s) => {
    const id = typeof s === 'string' ? null : s.id;
    return id ? `/sphere?id=${id}` : `/sphere?name=${encodeURIComponent(sName(s))}`;
};

function ServiceCard({
    id,
    type, title, spheres, sphereId, provider, providerId, actingUser, actingUserId,
    description, project, projectId,
    imageUrl, time, status, likesCount, likedByCurrentUser, likedBy: likedByInitial = [], cadence, acceptedByName,
    postedAt, acceptedAt, inProgressAt, completedAt, activity,
    pendingAcceptances = [], myAcceptance = null,
    currentUserId, onAccept, onConfirm, onReject,
}) {
    const navigate = useNavigate();
    const [liked, setLiked] = useState(likedByCurrentUser);
    const [likes, setLikes] = useState(likesCount);
    const [likedBy, setLikedBy] = useState(likedByInitial);
    const [img, setImg] = useState(imageUrl);
    const [accepting, setAccepting] = useState(false);
    const [confirmingId, setConfirmingId] = useState(null);
    const [rejectingId, setRejectingId] = useState(null);
    // Entities (alliances/projects) the viewer manages that may accept this
    // opening: only those within the opening's sphere (or any, if it's
    // standalone). Spheres themselves can't be an accepter — you act as a
    // group inside a sphere, not as the sphere.
    const managed = useManagedEntities(currentUserId);
    const acceptAsOptions = managed.filter(
        (m) => m.kind !== 'sphere' && (!sphereId || String(m.sphere_id) === String(sphereId))
    );
    const [acceptAs, setAcceptAs] = useState('');

    // Toggle the like on this opening. Optimistic, rolled back on error.
    const handleLike = async (e) => {
        e.stopPropagation();
        if (!id) return;
        const prevLiked = liked, prevLikes = likes;
        const want = !liked;
        setLiked(want);
        setLikes((n) => (want ? n + 1 : n - 1));
        try {
            // Explicit target state - a retried request is a no-op, not a flip.
            const res = await api.post(`/api/openings/${id}/like`, { liked: want });
            setLiked(res.data.liked);
            setLikes(res.data.likes);
            setLikedBy(res.data.liked_by || []);
        } catch (err) {
            setLiked(prevLiked);
            setLikes(prevLikes);
        }
    };

    const isOwnOpening = currentUserId && providerId && currentUserId === providerId;
    // A recipient who already acted can't accept again; a single opening locked
    // to someone else can't be accepted by others either.
    const lockedToOther = status === 'Accepted' && cadence !== 'perpetual' && !myAcceptance;
    const canAccept = currentUserId && !isOwnOpening && !myAcceptance && !lockedToOther
        && status !== 'Cancelled' && status !== 'Completed';

    const handleAccept = async (e) => {
        e.stopPropagation();
        if (accepting || !onAccept) return;
        setAccepting(true);
        try {
            // Empty select value = accept as myself; otherwise as the entity.
            await onAccept(acceptAs || null);
        } finally {
            setAccepting(false);
        }
    };

    const handleConfirm = async (e, accepterId) => {
        e.stopPropagation();
        if (confirmingId || !onConfirm) return;
        setConfirmingId(accepterId);
        try {
            await onConfirm(accepterId);
        } finally {
            setConfirmingId(null);
        }
    };

    const handleReject = async (e, accepterId) => {
        e.stopPropagation();
        if (rejectingId || !onReject) return;
        setRejectingId(accepterId);
        try {
            await onReject(accepterId);
        } finally {
            setRejectingId(null);
        }
    };

    const { steps, currentIndex: idx, cancelled } = buildOpeningProgress({
        status, cadence, postedAt, acceptedAt, inProgressAt, completedAt, activity,
    });

    return (
        <div className={`service ${type}`}>
            <div className="exchange-header">
                <div className="left">
                    <small>
                        {spheres.map((sphere, index) => (
                            <React.Fragment key={index}>
                                <Link to={sHref(sphere)} onClick={(e) => e.stopPropagation()}>
                                    {sName(sphere)}
                                </Link>
                                {index < spheres.length - 1 && ', '}
                            </React.Fragment>
                        ))}
                        {project && (
                            <>
                                <span className="service-header-pipe"> | </span>
                                <Link
                                    to={projectId ? `/project?id=${projectId}` : `/project?name=${encodeURIComponent(project)}`}
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    {project}
                                </Link>
                            </>
                        )}
                    </small>
                    <h3>
                        <Link
                            className="service-title-link"
                            to={id ? `/opening?id=${id}` : '#'}
                            onClick={(e) => { e.preventDefault(); e.stopPropagation(); if (id) navigate(`/opening?id=${id}`); }}
                        >
                            {title}
                        </Link>
                        {cadence === 'perpetual' && (
                            <span className="cadence-badge cadence-badge--perpetual" title="Ongoing — can be accepted repeatedly">
                                ↻ Ongoing
                            </span>
                        )}
                    </h3>
                    {status === 'Accepted' && acceptedByName && cadence !== 'perpetual' && (
                        <div className="accepted-by-note">Accepted by {acceptedByName}</div>
                    )}
                    <div className="participants">
                        {actingUser ? (
                            // Posted on behalf of an entity — attribute the human.
                            <span className="provider-line">
                                <Avatar userId={actingUserId} name={actingUser} size={20} />
                                <Link
                                    to={actingUserId ? `/user?id=${actingUserId}` : '/user'}
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    {actingUser}
                                </Link>
                                <span className="on-behalf-of"> on behalf of </span>
                                <strong>{provider}</strong>
                            </span>
                        ) : (
                            <span className="provider-line">
                                <Avatar userId={providerId} name={provider} size={20} />
                                <Link
                                    to={providerId ? `/user?id=${providerId}` : '/user'}
                                    onClick={(e) => e.stopPropagation()}
                                >
                                    {provider}
                                </Link>
                            </span>
                        )}
                    </div>
                </div>
                <div className="right">
                    <LikeTimestamp
                        likedByCurrentUser={liked}
                        likesCount={likes}
                        likedBy={likedBy}
                        time={time}
                        onLike={handleLike}
                    />
                </div>
            </div>

            <div className="description-container">
                <img
                    src={img}
                    alt={title}
                    className="exchange-image"
                    onError={() => setImg('/static/gift_economy.png')}
                    onClick={(e) => e.stopPropagation()}
                />
                <p className="description">{description}</p>
            </div>

            <StatusProgression steps={steps} currentIndex={idx} cancelled={cancelled} />

            {/* Provider view: pending acceptances awaiting confirmation. */}
            {isOwnOpening && pendingAcceptances.length > 0 && (
                <div className="service-pending">
                    <span className="service-pending-label">Awaiting your confirmation</span>
                    {pendingAcceptances.map((p) => (
                        <div key={p.accepter_id} className="service-pending-row">
                            <span className="service-pending-name">
                                👤{' '}
                                {p.acting_user_id ? (
                                    <>
                                        {p.accepter_name}
                                        <span className="service-pending-via">
                                            {' · via '}
                                            <Link to={`/user?id=${p.acting_user_id}`} onClick={(e) => e.stopPropagation()}>
                                                {p.acting_user_name}
                                            </Link>
                                        </span>
                                    </>
                                ) : (
                                    <Link to={`/user?id=${p.accepter_id}`} onClick={(e) => e.stopPropagation()}>
                                        {p.accepter_name}
                                    </Link>
                                )}
                            </span>
                            <span className="service-pending-actions">
                                <button
                                    className="service-confirm-btn"
                                    onClick={(e) => handleConfirm(e, p.accepter_id)}
                                    disabled={confirmingId === p.accepter_id || rejectingId === p.accepter_id}
                                >
                                    {confirmingId === p.accepter_id ? 'Confirming…' : '✓ Confirm'}
                                </button>
                                <button
                                    className="service-reject-btn"
                                    onClick={(e) => handleReject(e, p.accepter_id)}
                                    disabled={confirmingId === p.accepter_id || rejectingId === p.accepter_id}
                                >
                                    {rejectingId === p.accepter_id ? 'Declining…' : 'Decline'}
                                </button>
                            </span>
                        </div>
                    ))}
                </div>
            )}

            {/* Recipient view: their own acceptance state. */}
            {!isOwnOpening && myAcceptance?.status === 'pending' && (
                <div className="service-accept-cta">
                    <span className="service-awaiting">⏳ Awaiting confirmation from {provider}</span>
                </div>
            )}
            {!isOwnOpening && myAcceptance?.status === 'confirmed' && myAcceptance.exchange_id && (
                <div className="service-accept-cta">
                    <button
                        className="service-accept-btn service-view-exchange"
                        onClick={(e) => { e.stopPropagation(); navigate(`/exchange?id=${myAcceptance.exchange_id}`); }}
                    >
                        → View your exchange
                    </button>
                </div>
            )}

            {canAccept && (
                <div className="service-accept-cta">
                    {acceptAsOptions.length > 0 && (
                        <label className="service-accept-as" onClick={(e) => e.stopPropagation()}>
                            <span className="service-accept-as-label">Accept as</span>
                            <select
                                value={acceptAs}
                                onChange={(e) => setAcceptAs(e.target.value)}
                                disabled={accepting}
                            >
                                <option value="">Myself</option>
                                {acceptAsOptions.map((m) => (
                                    <option key={m.id} value={m.id}>{m.name} ({m.kind})</option>
                                ))}
                            </select>
                        </label>
                    )}
                    <button
                        className="service-accept-btn"
                        onClick={handleAccept}
                        disabled={accepting}
                    >
                        {accepting ? 'Accepting…' : (type === 'offer' ? '✓ Accept this Offer' : '✓ Fulfil this Need')}
                    </button>
                </div>
            )}
            {!isOwnOpening && !myAcceptance && lockedToOther && (
                <div className="service-accept-cta">
                    <span className="service-awaiting">Already accepted{acceptedByName ? ` by ${acceptedByName}` : ''}</span>
                </div>
            )}
        </div>
    );
}

ServiceCard.propTypes = {
    type: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    spheres: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.object])).isRequired,
    sphereId: PropTypes.string,
    provider: PropTypes.string.isRequired,
    providerId: PropTypes.string,
    actingUser: PropTypes.string,
    actingUserId: PropTypes.string,
    description: PropTypes.string.isRequired,
    project: PropTypes.string,
    projectId: PropTypes.string,
    imageUrl: PropTypes.string,
    time: PropTypes.string.isRequired,
    status: PropTypes.string.isRequired,
    likesCount: PropTypes.number.isRequired,
    likedBy: PropTypes.array,
    likedByCurrentUser: PropTypes.bool.isRequired,
    cadence: PropTypes.string,
    acceptedByName: PropTypes.string,
    postedAt: PropTypes.string,
    acceptedAt: PropTypes.string,
    inProgressAt: PropTypes.string,
    completedAt: PropTypes.string,
    activity: PropTypes.object,
    pendingAcceptances: PropTypes.arrayOf(PropTypes.object),
    myAcceptance: PropTypes.object,
    currentUserId: PropTypes.string,
    onAccept: PropTypes.func,
    onConfirm: PropTypes.func,
    onReject: PropTypes.func,
};

export default ServiceCard;
