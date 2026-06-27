// File: ./frontend/src/components/TransactionCard.js
// Description: A React component that displays a transaction card with various details, allowing for modifications and interactions.
// Props:
//    type - The type of transaction.
//    title - The title of the transaction.
//    spheres - The spheres associated with the transaction.
//    participants - The participants involved in the transaction.
//    description - The description of the transaction.
//    project - The project associated with the transaction.
//    imageUrl - The image URL for the transaction.
//    time - The time the transaction occurred.
//    status - The current status of the transaction.
//    likesCount - The number of likes for the transaction.
//    likedByCurrentUser - Whether the current user has liked the transaction.
//    originService - The service from which the transaction originated.
//    initiatedTime - The time the transaction was initiated.
//    inProgressTime - The time the transaction was marked as in progress.
//    finishedTime - The time the transaction was marked as finished.
//    trustifactedTime - The time the transaction was marked as trustifacted.
//    additionalCommentsTime - The time additional comments were added.
//    trustifacts - An array of trustifacts associated with the transaction.
//    shoutouts - An array of shoutouts associated with the transaction.
//    onAddTrustifact - Function to call when a new trustifact is added.
//    onAddShoutout - Function to call when a new shoutout is added.
//    onModifyTransaction - Function to call when the transaction is modified.
//    canModify - Whether the transaction can be modified.

import React, { useState } from 'react';
import PropTypes from 'prop-types';
import LikeTimestamp from './LikeTimestamp';
import NewShoutoutForm from './NewShoutoutForm';
import StatusProgression from './StatusProgression';
import '../styles/TrustTrail.css';

// Lifecycle phases for a trust transaction (shared chevron control).
const TX_STEPS = ['Initiated', 'In Progress', 'Finished', 'Trustifacted', 'Additional Comments Added'];
const txIndex = (status) => {
    const i = TX_STEPS.findIndex((s) => s.toLowerCase() === (status || '').toLowerCase());
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

function TransactionCard({
    type,
    title,
    spheres,
    participants,
    description,
    project,
    imageUrl,
    time,
    status,
    likesCount,
    likedByCurrentUser,
    originService,
    initiatedTime,
    inProgressTime,
    finishedTime,
    trustifactedTime,
    additionalCommentsTime,
    trustifacts,
    shoutouts,
    onAddTrustifact,
    onAddShoutout,
    onModifyTransaction,
    canModify
}) {
    const [editableTitle, setEditableTitle] = useState(title);
    const [editableDescription, setEditableDescription] = useState(description);
    const [editableProject, setEditableProject] = useState(project);
    const [editableImageUrl, setEditableImageUrl] = useState(imageUrl || 'placeholder.jpg');
    const [showShoutoutForm, setShowShoutoutForm] = useState(false);

    const handleTitleChange = (e) => setEditableTitle(e.target.innerText);
    const handleDescriptionChange = (e) => setEditableDescription(e.target.innerText);

    const handleKeyPress = (e, field) => {
        if (e.key === 'Enter') {
            e.preventDefault();
            onModifyTransaction(field, e.target.innerText);
        }
    };

    const handleAddShoutout = (shoutout) => {
        onAddShoutout(shoutout);
        setShowShoutoutForm(false);
    };

    return (
        <div className={`transaction ${type}`} >
            <div className="transaction-header">
                <div className="left">
                    <small>
                        {spheres.map((sphere, index) => (
                            <a href={`/sphere?name=${encodeURIComponent(sphere)}`} onClick={(e) => e.stopPropagation()} key={index}>
                                {sphere}{index < spheres.length - 1 ? ', ' : ''}
                            </a>
                        ))}
                    </small>
                    <h3
                        contentEditable={canModify}
                        suppressContentEditableWarning={true}
                        onBlur={handleTitleChange}
                        onKeyPress={(e) => handleKeyPress(e, 'title')}
                        className={canModify ? 'editable' : ''}
                    >
                        {editableTitle}
                    </h3>
                    <div className="participants">
                        {participants.map((participant, index) => (
                            <span key={index}>👤 <a href={pHref(participant)} onClick={(e) => e.stopPropagation()}>{pName(participant)}</a>{index < participants.length - 1 ? ', ' : ''}</span>
                        ))}
                    </div>
                    {originService && (
                        <div className="origin-service">
                            <small><button onClick={(e) => e.stopPropagation()} className="link-button">{originService}</button></small>
                        </div>
                    )}
                </div>
                <div className="right">
                    <LikeTimestamp
                        likedByCurrentUser={likedByCurrentUser}
                        likesCount={likesCount}
                        time={time}
                        onLike={(e) => {
                            e.stopPropagation();
                            // Handle like functionality here
                        }}
                    />
                </div>
            </div>
            <div className="description-container">
                {editableImageUrl ? (
                    <img
                        src={editableImageUrl}
                        alt={editableTitle}
                        className="transaction-image"
                        onClick={(e) => e.stopPropagation()}
                        onMouseEnter={() => canModify && setEditableImageUrl('')}
                    />
                ) : (
                    <div
                        className="image-placeholder"
                        onClick={(e) => canModify && document.getElementById('image-upload').click()}
                    >
                        Image Placeholder
                        <input
                            type="file"
                            id="image-upload"
                            style={{ display: 'none' }}
                            onChange={(e) => {
                                const file = e.target.files[0];
                                if (file) {
                                    setEditableImageUrl(URL.createObjectURL(file));
                                }
                            }}
                        />
                    </div>
                )}
                <p
                    contentEditable={canModify}
                    suppressContentEditableWarning={true}
                    onBlur={handleDescriptionChange}
                    onKeyPress={(e) => handleKeyPress(e, 'description')}
                    className={`description ${canModify ? 'editable' : ''}`}
                >
                    {editableDescription}
                </p>
                <div className="project-link" onMouseEnter={() => canModify && setEditableProject('')}>
                    {editableProject ? (
                        <button onClick={(e) => e.stopPropagation()} className="link-button">{editableProject}</button>
                    ) : (
                        <select onChange={(e) => setEditableProject(e.target.value)}>
                            <option value="Project 1">Project 1</option>
                            <option value="Project 2">Project 2</option>
                        </select>
                    )}
                </div>
            </div>
            <div className="status">
                <StatusProgression
                    currentIndex={txIndex(status)}
                    steps={TX_STEPS.map((label, i) => ({
                        label,
                        time: [initiatedTime, inProgressTime, finishedTime, trustifactedTime, additionalCommentsTime][i] || '',
                    }))}
                />
            </div>
            <hr />
            {trustifacts && trustifacts.length > 0 ? (
                <div className="trustifacts">
                    {trustifacts.map((trustifact, index) => (
                        <div key={index} className="trustifact">
                            <div className="left">
                                {trustifact.imageUrl && <img src={trustifact.imageUrl} alt={trustifact.text} className="trustifact-image" onClick={(e) => e.stopPropagation()} />}
                                <p><strong>{trustifact.author}:</strong> {trustifact.text}</p>
                            </div>
                            <div className="right">
                                <LikeTimestamp
                                    likedByCurrentUser={trustifact.likedByCurrentUser}
                                    likesCount={trustifact.likesCount}
                                    time={trustifact.time}
                                    onLike={(e) => {
                                        e.stopPropagation();
                                        // Handle like functionality here
                                    }}
                                />
                            </div>
                        </div>
                    ))}
                </div>
            ) : (
                <div id="trustifact-entry">
                    <button id="save-trustifact-btn" onClick={onAddTrustifact}>Add Trustifact</button>
                </div>
            )}
            <hr />
            <div className="shoutouts">
                {!showShoutoutForm ? (
                    <div id="shoutout-entry">
                        <button
                            id="save-shoutout-btn"
                            className={!showShoutoutForm ? '' : 'btn-purple'}
                            onClick={() => setShowShoutoutForm(true)}
                        >
                            Add Shoutout
                        </button>
                    </div>
                ) : (
                    <NewShoutoutForm onSave={handleAddShoutout} onCancel={() => setShowShoutoutForm(false)} />
                )}
                {shoutouts && shoutouts.length > 0 && shoutouts.map((shoutout, index) => (
                    <div key={index} className="shoutout">
                        <div className="left">
                            <p><strong>{shoutout.author}:</strong> {shoutout.text}</p>
                        </div>
                        <div className="right">
                            <LikeTimestamp
                                likedByCurrentUser={shoutout.likedByCurrentUser}
                                likesCount={shoutout.likesCount}
                                time={shoutout.time}
                                onLike={(e) => {
                                    e.stopPropagation();
                                    // Handle like functionality here
                                }}
                            />
                        </div>
                    </div>
                ))}
            </div>
        </div>
    );
}

TransactionCard.propTypes = {
    type: PropTypes.string.isRequired,
    title: PropTypes.string.isRequired,
    spheres: PropTypes.arrayOf(PropTypes.string).isRequired,
    participants: PropTypes.arrayOf(PropTypes.oneOfType([PropTypes.string, PropTypes.object])).isRequired,
    description: PropTypes.string.isRequired,
    project: PropTypes.string,
    imageUrl: PropTypes.string,
    time: PropTypes.string.isRequired,
    status: PropTypes.string.isRequired,
    likesCount: PropTypes.number.isRequired,
    likedByCurrentUser: PropTypes.bool.isRequired,
    originService: PropTypes.string,
    initiatedTime: PropTypes.string,
    inProgressTime: PropTypes.string,
    finishedTime: PropTypes.string,
    trustifactedTime: PropTypes.string,
    additionalCommentsTime: PropTypes.string,
    trustifacts: PropTypes.arrayOf(PropTypes.shape({
        author: PropTypes.string.isRequired,
        text: PropTypes.string.isRequired,
        time: PropTypes.string.isRequired,
        likesCount: PropTypes.number.isRequired,
        likedByCurrentUser: PropTypes.bool.isRequired,
        imageUrl: PropTypes.string
    })),
    shoutouts: PropTypes.arrayOf(PropTypes.shape({
        author: PropTypes.string.isRequired,
        text: PropTypes.string.isRequired,
        time: PropTypes.string.isRequired,
        likesCount: PropTypes.number.isRequired,
        likedByCurrentUser: PropTypes.bool.isRequired
    })),
    onAddTrustifact: PropTypes.func.isRequired,
    onAddShoutout: PropTypes.func.isRequired,
    onModifyTransaction: PropTypes.func.isRequired,
    canModify: PropTypes.bool.isRequired
};

export default TransactionCard;
