// ValueCardPicker — compact multi-select chip grid for associating value cards
// with a Receipt or Acknowledgement comment. Mounts lazily (only when the form
// is open) so it fetches cards at that point — one request per form open.

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

function ValueCardPicker({ selectedIds, onChange }) {
    const { userId } = useLogin();
    const [cards, setCards] = useState([]);

    useEffect(() => {
        if (!userId) return;
        api.get(`/api/value_cards/${userId}`)
            .then(res => setCards(res.data || []))
            .catch(() => {});
    }, [userId]);

    if (!cards.length) return null;

    const toggle = (cardId) => {
        const next = selectedIds.includes(cardId)
            ? selectedIds.filter(id => id !== cardId)
            : [...selectedIds, cardId];
        onChange(next, cards.filter(c => next.includes(c.card_id)));
    };

    return (
        <div className="vc-picker">
            <span className="vc-picker-label">Associate values</span>
            <div className="vc-picker-chips">
                {cards.map(card => {
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
                            title={on ? 'Remove' : 'Associate this value'}
                        >
                            <span className="vc-chip-glyph">{glyph}</span>
                            <span className="vc-chip-title">{card.title}</span>
                            {on && <span className="vc-picker-check" aria-label="selected">✓</span>}
                        </button>
                    );
                })}
            </div>
        </div>
    );
}

ValueCardPicker.propTypes = {
    selectedIds: PropTypes.arrayOf(PropTypes.string).isRequired,
    onChange: PropTypes.func.isRequired,
};

export default ValueCardPicker;
