// File: ./frontend/src/components/ServiceCard.js
// A marketplace offer/request card. Status is shown via the shared
// StatusProgression control; the project is an indication only.

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import LikeTimestamp from './LikeTimestamp';
import StatusProgression from './StatusProgression';
import '../styles/Marketplace.css';

const SERVICE_STEPS = ['Posted', 'Accepted', 'In Progress', 'Completed'];

function serviceIndex(status) {
    const i = SERVICE_STEPS.findIndex((s) => s.toLowerCase() === (status || '').toLowerCase());
    return i >= 0 ? i : 0;
}

function ServiceCard({
    type, title, spheres, provider, providerId, description, project,
    imageUrl, time, status, likesCount, likedByCurrentUser, onAccept, onConfirm,
}) {
    const [liked, setLiked] = useState(likedByCurrentUser);
    const [likes, setLikes] = useState(likesCount);
    const [img, setImg] = useState(imageUrl);

    const handleLike = () => {
        setLiked(!liked);
        setLikes(liked ? likes - 1 : likes + 1);
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
                                <a href={`/sphere?name=${encodeURIComponent(sphere)}`} onClick={(e) => e.stopPropagation()}>{sphere}</a>
                                {index < spheres.length - 1 && ', '}
                            </React.Fragment>
                        ))}
                    </small>
                    <h3>{title}</h3>
                    <div className="participants">
                        <span>👤 <a href={providerId ? `/user?id=${providerId}` : '/user'} onClick={(e) => e.stopPropagation()}>{provider}</a></span>
                    </div>
                </div>
                <div className="right">
                    <LikeTimestamp
                        likedByCurrentUser={liked}
                        likesCount={likes}
                        time={time}
                        onLike={(e) => { e.stopPropagation(); handleLike(); }}
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
                        ? <><span className="muted">Part of</span><br /><a href={`/project?name=${encodeURIComponent(project)}`} onClick={(e) => e.stopPropagation()}>{project}</a></>
                        : <span className="muted">Standalone gift</span>}
                </div>
            </div>

            <StatusProgression steps={steps} currentIndex={idx} cancelled={cancelled} />
        </div>
    );
}

ServiceCard.propTypes = {
    type: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    spheres: PropTypes.arrayOf(PropTypes.string).isRequired,
    provider: PropTypes.string.isRequired,
    providerId: PropTypes.string,
    description: PropTypes.string.isRequired,
    project: PropTypes.string,
    imageUrl: PropTypes.string,
    time: PropTypes.string.isRequired,
    status: PropTypes.string.isRequired,
    likesCount: PropTypes.number.isRequired,
    likedByCurrentUser: PropTypes.bool.isRequired,
    onAccept: PropTypes.func,
    onConfirm: PropTypes.func,
};

export default ServiceCard;
