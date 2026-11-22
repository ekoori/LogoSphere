// Where something is, as others may know it: the words, a banded distance, and
// the spot itself only where its people chose to show it exactly.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import SlippyMap from './SlippyMap';
import '../styles/Places.css';

export function WhereLine({ location, distance }) {
    if (!location && !distance) return null;
    return (
        <span className="where-line">
            {location && <span>📍 {location}</span>}
            {distance && <span className="where-distance">{distance.text}</span>}
        </span>
    );
}

WhereLine.propTypes = { location: PropTypes.string, distance: PropTypes.shape({ text: PropTypes.string }) };

/** "See the spot on a map": the map loads only when asked for. */
export function ExactSpot({ point }) {
    const [view, setView] = useState(null);
    if (!point) return null;
    return (
        <div className="exact-spot">
            <button type="button" className="place-btn" aria-expanded={!!view}
                    onClick={() => setView(view ? null : { lat: point.lat, lon: point.lon, z: 15 })}>
                {view ? 'Close the map' : 'See the spot on a map'}
            </button>
            {view && <div className="place-map"><SlippyMap view={view} onView={setView} pin={point} /></div>}
        </div>
    );
}

ExactSpot.propTypes = { point: PropTypes.shape({ lat: PropTypes.number, lon: PropTypes.number }) };
