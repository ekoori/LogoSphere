// "AI picture", on every picture known to be AI-made.
import React from 'react';
import PropTypes from 'prop-types';
import '../styles/AiHelp.css';

export function AiTag({ short = false, className = '' }) {
    return (
        <span className={`ai-tag ${className}`} title="This picture was made with AI">
            {short ? 'AI' : 'AI picture'}
        </span>
    );
}

AiTag.propTypes = { short: PropTypes.bool, className: PropTypes.string };

/** An <img>, with the tag on it when the picture is AI-made. */
export function Picture({ isAi = false, short = false, alt = '', ...img }) {
    if (!isAi) return <img alt={alt} {...img} />;
    return (
        <span className="ai-pic">
            <img alt={alt ? `${alt} (AI picture)` : 'AI picture'} {...img} />
            <AiTag short={short} className="ai-tag--on" />
        </span>
    );
}

Picture.propTypes = { isAi: PropTypes.bool, short: PropTypes.bool, alt: PropTypes.string };
