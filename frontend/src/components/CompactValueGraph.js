// CompactValueGraph — a compact, read-only value-card display for entity page
// sidebars (Sphere/Alliance/Project). Mirrors UserPage's "Values" block: small
// wrapping chips that expand to a full card on click, not the large
// full-size evc-card grid (which was overflowing the narrow aside). Editing
// happens on the entity's management page, linked via `manageHref`.
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import api from '../api';
import ValueCardChip from './ValueCardChip';
import '../styles/ValueCardChip.css';

function CompactValueGraph({ entityId, manageHref, currentUserId }) {
    const [cards, setCards] = useState([]);
    const [loaded, setLoaded] = useState(false);

    useEffect(() => {
        if (!entityId) { setLoaded(true); return undefined; }
        let active = true;
        api.get(`/api/value_cards/${entityId}`)
            .then((r) => { if (active) setCards(r.data || []); })
            .catch(() => { if (active) setCards([]); })
            .finally(() => { if (active) setLoaded(true); });
        return () => { active = false; };
    }, [entityId]);

    if (!loaded) return null;

    return (
        <div className="cvg">
            {cards.length > 0 ? (
                <div className="vc-chips-row">
                    {cards.map((card, i) => (
                        <ValueCardChip key={card.card_id || i} card={card} subjectLabel="We care about" currentUserId={currentUserId} />
                    ))}
                </div>
            ) : (
                <p className="ep-empty">No value cards yet.</p>
            )}
            {manageHref && (
                <Link to={manageHref} className="cvg-manage-link">
                    Manage value graph →
                </Link>
            )}
        </div>
    );
}

CompactValueGraph.propTypes = {
    entityId: PropTypes.string,
    manageHref: PropTypes.string,
    currentUserId: PropTypes.string,
};

export default CompactValueGraph;
