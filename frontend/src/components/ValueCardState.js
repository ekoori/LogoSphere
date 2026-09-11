// ValueCardState — the endorsement / review row on a value card.
//
// CLEAR's "E" and "R": a card is *endorsed* by a deliberate, reflective step
// separate from writing it, and *reviewed* on a cadence (the backend flags
// needs_review after 90 days). Read-only for everyone; the owner (or an
// entity's manager) gets the buttons when `endpoints` is supplied.
import React, { useState } from 'react';
import PropTypes from 'prop-types';
import api from '../api';
import '../styles/ValueCardChip.css';

function ValueCardState({ card, endpoints = null, onUpdated }) {
    const [busy, setBusy] = useState(false);
    const [err, setErr] = useState('');

    const act = async (which) => {
        if (!endpoints || busy) return;
        setBusy(true);
        setErr('');
        try {
            const res = await api.post(endpoints[which]);
            if (onUpdated) onUpdated(res.data);
        } catch (e) {
            setErr(e.response?.data?.message || 'Could not update the card.');
        } finally {
            setBusy(false);
        }
    };

    const endorsedOn = card.endorsed_at ? new Date(card.endorsed_at) : null;
    const reviewedOn = card.reviewed_at ? new Date(card.reviewed_at) : null;
    const fmt = (d) => d.toLocaleDateString(undefined, { month: 'short', year: 'numeric' });

    return (
        <div className="vc-state-row" onClick={(e) => e.stopPropagation()}>
            {card.endorsed ? (
                <span className="vc-state vc-state--endorsed" title={endorsedOn ? `Endorsed ${fmt(endorsedOn)}` : 'Endorsed'}>
                    ✓ Endorsed{endorsedOn ? ` · ${fmt(endorsedOn)}` : ''}
                </span>
            ) : (
                <span className="vc-state" title="Written, but not yet endorsed on reflection">Draft</span>
            )}
            {card.needs_review && (
                <span className="vc-state vc-state--review" title="It's been a while - does this still hold?">Due for review</span>
            )}
            {endpoints && !card.endorsed && (
                <button type="button" className="vc-state-btn" disabled={busy} onClick={() => act('endorse')}
                        title="Re-read it. If it still holds after reflection, endorse it.">
                    {busy ? '…' : 'Endorse on reflection'}
                </button>
            )}
            {endpoints && card.endorsed && card.needs_review && (
                <button type="button" className="vc-state-btn" disabled={busy} onClick={() => act('review')}>
                    {busy ? '…' : 'Still holds - mark reviewed'}
                </button>
            )}
            {endpoints && card.endorsed && !card.needs_review && reviewedOn && (
                <span className="vc-state" title="Last reviewed">Reviewed {fmt(reviewedOn)}</span>
            )}
            {err && <span className="vc-clone-msg vc-clone-msg--err">{err}</span>}
        </div>
    );
}

ValueCardState.propTypes = {
    card: PropTypes.object.isRequired,
    endpoints: PropTypes.shape({ endorse: PropTypes.string, review: PropTypes.string }),
    onUpdated: PropTypes.func,
};

export default ValueCardState;
