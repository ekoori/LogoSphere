// Labels for the demonstration. Demo spheres sit beside real ones, so
// anything from a demo sphere says "Demo", and AI persona accounts (famous
// names playing everyday neighbours) say "AI persona" wherever they appear.
import React from 'react';
import PropTypes from 'prop-types';
import '../styles/DemoTags.css';

export function DemoTag({ title = 'From a demo sphere: the people here are AI personas' }) {
    return <span className="demo-tag" title={title}>Demo</span>;
}

DemoTag.propTypes = { title: PropTypes.string };

export function PersonaTag({ compact = false }) {
    return (
        <span className="persona-tag" title="An AI persona: a famous name playing an everyday neighbour in the demo">
            {compact ? 'AI' : 'AI persona'}
        </span>
    );
}

PersonaTag.propTypes = { compact: PropTypes.bool };
