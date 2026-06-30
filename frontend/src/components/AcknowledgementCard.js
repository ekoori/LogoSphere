// File: ./frontend/src/components/AcknowledgementCard.js

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import LikeTimestamp from './LikeTimestamp';
import '../styles/App.css';

const AcknowledgementCard = ({ acknowledgement }) => {
    const [liked, setLiked] = useState(acknowledgement.likedByCurrentUser);
    const [likes, setLikes] = useState(acknowledgement.likesCount);

    const handleLike = () => {
        setLiked(!liked);
        setLikes(liked ? likes - 1 : likes + 1);
        // Implement further logic to update like status in the backend if necessary
    };

    return (
        <div className="acknowledgement-card">
            <div className="acknowledgement-header">
                <div className="left">
                    <span>👤 <a href="/user">{acknowledgement.author}</a></span>
                </div>
                <p className="acknowledgement-text">{acknowledgement.text}</p>
                <div className="right">
                    <LikeTimestamp
                        likedByCurrentUser={liked}
                        likesCount={likes}
                        time={acknowledgement.time}
                        onLike={(e) => {
                            e.stopPropagation();
                            handleLike();
                        }}
                    />
                </div>
            </div>

        </div>
    );
};

AcknowledgementCard.propTypes = {
    acknowledgement: PropTypes.shape({
        author: PropTypes.string.isRequired,
        text: PropTypes.string.isRequired,
        time: PropTypes.string.isRequired,
        likesCount: PropTypes.number.isRequired,
        likedByCurrentUser: PropTypes.bool.isRequired,
    }).isRequired,
};

export default AcknowledgementCard;
