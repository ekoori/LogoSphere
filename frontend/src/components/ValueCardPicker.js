// ValueCardPicker — compact multi-select chip grid for naming the value cards
// a Receipt or Acknowledgement expressed. Offers the writer's own cards and,
// when the form is about an exchange with someone, the other party's cards
// too ("this expressed *their* value of X"). Mounts lazily (only when the form
// is open) so it fetches at that point.
import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { useLogin } from '../App';
import api from '../api';
import '../styles/ValueCardChip.css';

const COLOR_MAP = {
    honey: 'var(--honey)', leaf: 'var(--leaf)',
    terracotta: 'var(--terracotta)', moss: 'var(--moss)', sage: 'var(--sage)',
};
const FRANKL_GLYPH = { creative: '✶', experiential: '❍', attitudinal: '△' };

function ValueCardPicker({ selectedIds, onChange, counterparts = [] }) {
    const { userId } = useLogin();
    const [groups, setGroups] = useState([]);

    useEffect(() => {
        if (!userId) return undefined;
        let alive = true;
        const owners = [{ id: userId, label: 'Your values' },
            ...counterparts.filter((c) => c && c.id && String(c.id) !== String(userId))];
        Promise.all(owners.map((o) =>
            api.get(`/api/value_cards/${o.id}`)
                .then((r) => ({ ...o, cards: r.data || [] }))
                .catch(() => ({ ...o, cards: [] }))
        )).then((gs) => { if (alive) setGroups(gs.filter((g) => g.cards.length)); });
        return () => { alive = false; };
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, [userId, counterparts.map((c) => c?.id).join(',')]);

    const allCards = groups.flatMap((g) => g.cards);
    if (!allCards.length) return null;

    const toggle = (cardId) => {
        const next = selectedIds.includes(cardId)
            ? selectedIds.filter((id) => id !== cardId)
            : [...selectedIds, cardId];
        onChange(next, allCards.filter((c) => next.includes(c.card_id)));
    };

    return (
        <div className="vc-picker">
            <span className="vc-picker-label">Which values did this express?</span>
            {groups.map((g) => (
                <div key={g.id} className="vc-picker-group">
                    {groups.length > 1 && <span className="vc-picker-group-label">{g.label}</span>}
                    <div className="vc-picker-chips">
                        {g.cards.map((card) => {
                            const on = selectedIds.includes(card.card_id);
                            const accent = COLOR_MAP[card.color_key] || 'var(--honey)';
                            const glyph = FRANKL_GLYPH[card.frankl_mode] || '✶';
                            return (
                                <button
                                    key={card.card_id}
                                    type="button"
                                    className={`vc-picker-chip${on ? ' vc-picker-chip--on' : ''}`}
                                    style={{ '--chip-accent': accent }}
                                    onClick={() => toggle(card.card_id)}
                                    title={on ? 'Remove' : 'This expressed this value'}
                                >
                                    <span className="vc-chip-glyph">{glyph}</span>
                                    <span className="vc-chip-title">{card.title}</span>
                                    {on && <span className="vc-picker-check" aria-label="selected">✓</span>}
                                </button>
                            );
                        })}
                    </div>
                </div>
            ))}
        </div>
    );
}

ValueCardPicker.propTypes = {
    selectedIds: PropTypes.arrayOf(PropTypes.string).isRequired,
    onChange: PropTypes.func.isRequired,
    // Other parties whose cards may be named, e.g. the exchange's counterpart:
    // [{ id, label }]
    counterparts: PropTypes.arrayOf(PropTypes.shape({ id: PropTypes.string, label: PropTypes.string })),
};

export default ValueCardPicker;
