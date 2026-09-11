// LikeTimestamp — the "appreciated by" control on openings and exchanges.
//
// Deliberately shows *who* appreciated something rather than a number: a bare
// like count is exactly the thin proxy the platform argues against (see About).
// `likedBy` is [{id, name}]; when a caller only has a count, it falls back to
// a neutral phrase rather than a leaderboard-style integer.
import React from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import '../styles/App.css';

function describe(likedBy, likesCount, likedByCurrentUser) {
    if (likedBy && likedBy.length) {
        const names = likedBy.map((p) => p.name);
        if (names.length === 1) return names;
        if (names.length === 2) return names;
        return [...names.slice(0, 2), `${names.length - 2} other${names.length - 2 === 1 ? '' : 's'}`];
    }
    if (likesCount > 0) return [likedByCurrentUser && likesCount === 1 ? 'you' : 'members'];
    return [];
}

function LikeTimestamp({ likedByCurrentUser, likesCount = 0, likedBy = null, time, onLike }) {
    const parts = describe(likedBy, likesCount, likedByCurrentUser);
    return (
        <div className="like-timestamp">
            <button
                className={`like-btn ${likedByCurrentUser ? 'liked' : ''}`}
                onClick={onLike}
                aria-pressed={likedByCurrentUser}
                title={likedByCurrentUser ? 'You appreciated this' : 'Appreciate this'}
            >
                {likedByCurrentUser ? '❤️' : '🖤'}
            </button>
            {parts.length > 0 && (
                <span className="likes-by">
                    Appreciated by{' '}
                    {likedBy && likedBy.length ? likedBy.slice(0, 2).map((p, i) => (
                        <React.Fragment key={p.id}>
                            <Link to={`/user?id=${p.id}`}>{p.name}</Link>
                            {i < Math.min(likedBy.length, 2) - 1 ? (likedBy.length > 2 ? ', ' : ' and ') : ''}
                        </React.Fragment>
                    )) : parts[0]}
                    {likedBy && likedBy.length > 2 && ` and ${parts[2]}`}
                </span>
            )}
            {time && <span className="time">{time}</span>}
        </div>
    );
}

LikeTimestamp.propTypes = {
    likedByCurrentUser: PropTypes.bool.isRequired,
    likesCount: PropTypes.number,
    likedBy: PropTypes.arrayOf(PropTypes.shape({ id: PropTypes.string, name: PropTypes.string })),
    time: PropTypes.string,
    onLike: PropTypes.func.isRequired,
};

export default LikeTimestamp;
