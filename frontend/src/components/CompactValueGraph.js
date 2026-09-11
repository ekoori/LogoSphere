// CompactValueGraph — a compact, read-only value-card display for entity page
// sidebars (Sphere/Alliance/Project). Small wrapping chips that expand to a
// full card on click. Editing happens on the entity's management page, linked
// via `manageHref`. Pass `cards` when the caller already has them (the detail
// endpoints embed them); it only fetches when they're not supplied.
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import api from '../api';
import ValueCardChip from './ValueCardChip';
import '../styles/ValueCardChip.css';

function CompactValueGraph({ entityId, cards: given, manageHref, currentUserId }) {
    const [fetched, setFetched] = useState(null);

    useEffect(() => {
        if (given || !entityId) return undefined;
        let active = true;
        api.get(`/api/value_cards/${entityId}`)
            .then((r) => { if (active) setFetched(r.data || []); })
            .catch(() => { if (active) setFetched([]); });
        return () => { active = false; };
    }, [entityId, given]);

    const cards = given || fetched;
    if (!cards) return null;

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
                <Link to={manageHref} className="cvg-manage-link">Manage value graph →</Link>
            )}
        </div>
    );
}

CompactValueGraph.propTypes = {
    entityId: PropTypes.string,
    cards: PropTypes.array,
    manageHref: PropTypes.string,
    currentUserId: PropTypes.string,
};

export default CompactValueGraph;
