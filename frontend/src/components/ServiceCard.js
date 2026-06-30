// ServiceCard — a marketplace offer or request card.
// Status shown via shared StatusProgression; project is a read-only indication.
// Spheres accept {id, name} pairs so links use UUID when available.

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { useNavigate } from 'react-router-dom';
import LikeTimestamp from './LikeTimestamp';
import StatusProgression from './StatusProgression';
import '../styles/Marketplace.css';

const SERVICE_STEPS = ['Posted', 'Accepted', 'In Progress', 'Completed'];

function serviceIndex(status) {
    const i = SERVICE_STEPS.findIndex((s) => s.toLowerCase() === (status || '').toLowerCase());
    return i >= 0 ? i : 0;
}

// Spheres may be strings or {id, name} pairs — prefer UUID link when available.
const sName = (s) => (typeof s === 'string' ? s : s.name);
const sHref = (s) => {
    const id = typeof s === 'string' ? null : s.id;
    return id ? `/sphere?id=${id}` : `/sphere?name=${encodeURIComponent(sName(s))}`;
};

function ServiceCard({
    type, title, spheres, provider, providerId, description, project,
    imageUrl, time, status, likesCount, likedByCurrentUser,
}) {
    const navigate = useNavigate();
    const [liked, setLiked] = useState(likedByCurrentUser);
    const [likes, setLikes] = useState(likesCount);
    const [img, setImg] = useState(imageUrl);

    const handleLike = (e) => {
        e.stopPropagation();
        setLiked((v) => !v);
        setLikes((n) => liked ? n - 1 : n + 1);
    };

    const cancelled = status === 'Cancelled';
    const idx = cancelled ? 1 : serviceIndex(status);
    const steps = SERVICE_STEPS.map((label, i) => ({ label, time: i === idx ? time : '' }));

    return (
        <div className={`service ${type}`}>
            <div className="transaction-header">
                <div className="left">
                    <small>
                        {spheres.map((sphere, index) => (
                            <React.Fragment key={index}>
                                <a href={sHref(sphere)} onClick={(e) => e.stopPropagation()}>
                                    {sName(sphere)}
                                </a>
                                {index < spheres.length - 1 && ', '}
                            </React.Fragment>
                        ))}
                    </small>
                    <h3>{title}</h3>
                    <div className="participants">
                        <span>
                            👤{' '}
                            <a
                                href={providerId ? `/user?id=${providerId}` : '/user'}
                                onClick={(e) => e.stopPropagation()}
                            >
                                {provider}
                            </a>
                        </span>
                    </div>
                </div>
                <div className="right">
                    <LikeTimestamp
                        likedByCurrentUser={liked}
                        likesCount={likes}
                        time={time}
                        onLike={handleLike}
                    />
                </div>
            </div>

            <div className="description-container">
                <img
                    src={img}
                    alt={title}
                    className="transaction-image"
                    onError={() => setImg('/static/gift_economy.png')}
                    onClick={(e) => e.stopPropagation()}
                />
                <p className="description">{description}</p>
                <div className="service-project">
                    {project
                        ? (
                            <>
                                <span className="muted">Part of</span>
                                <br />
                                <span className="service-project-name">{project}</span>
                            </>
                        )
                        : <span className="muted">Standalone gift</span>}
                </div>
            </div>

            <StatusProgression steps={steps} currentIndex={idx} cancelled={cancelled} />

            <div className="service-create-cta">
                <button
                    className="service-create-btn"
                    onClick={(e) => { e.stopPropagation(); navigate('/marketplace?new=1'); }}
                >
                    + Offer or Request
                </button>
            </div>
        </div>
    );
}

ServiceCard.propTypes = {
    type: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    spheres: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.object])).isRequired,
    provider: PropTypes.string.isRequired,
    providerId: PropTypes.string,
    description: PropTypes.string.isRequired,
    project: PropTypes.string,
    imageUrl: PropTypes.string,
    time: PropTypes.string.isRequired,
    status: PropTypes.string.isRequired,
    likesCount: PropTypes.number.isRequired,
    likedByCurrentUser: PropTypes.bool.isRequired,
};

export default ServiceCard;
