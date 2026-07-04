// EntityValueGraph — the shared value-card ("Meaning Graph") editor for
// spheres, alliances, and projects. Fetches an entity's cards, renders them
// as expandable cards, and — when `canManage` — lets a manager add or remove
// cards. Writes go through the authorised /api/entity_value_cards endpoints.
//
//   <EntityValueGraph entityId={id} canManage={canManage} entityNoun="alliance" />

import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import api from '../api';
import '../styles/EntityPage.css';
import '../styles/ValueCardChip.css';

const FRANKL_META = {
    creative:     { glyph: '✶', label: 'Creative' },
    experiential: { glyph: '❍', label: 'Experiential' },
    attitudinal:  { glyph: '△', label: 'Attitudinal' },
};

const COLOR_CSS = {
    honey: '--honey', leaf: '--leaf', terracotta: '--terracotta',
    sage: '--sage', moss: '--moss',
};

function EntityValueCard({ card, idx, canDelete, onDelete, onEdit }) {
    const [expanded, setExpanded] = useState(false);
    const [confirmDelete, setConfirmDelete] = useState(false);
    const meta = FRANKL_META[card.frankl_mode] || FRANKL_META.creative;
    const accentVar = COLOR_CSS[card.color_key] || '--honey';
    const rot = (idx % 2 === 0) ? '-0.6deg' : '0.5deg';

    return (
        <article
            className={`evc-card ${expanded ? 'evc-card--expanded' : ''}`}
            style={{ '--evc-accent': `var(${accentVar})`, '--evc-rot': rot }}
            onClick={() => { if (!confirmDelete) setExpanded(v => !v); }}
        >
            <span className="evc-punch" aria-hidden="true" />
            <div className="evc-top">
                <span className="evc-mode">{meta.glyph} {meta.label}</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '0.5em' }}>
                    {canDelete && !confirmDelete && (
                        <button className="vc-edit" onClick={e => { e.stopPropagation(); onEdit(card); }} title="Edit">✎</button>
                    )}
                    {canDelete && !confirmDelete && (
                        <button className="vc-delete" onClick={e => { e.stopPropagation(); setConfirmDelete(true); }} title="Remove">×</button>
                    )}
                    {canDelete && confirmDelete && (
                        <span className="vc-delete-confirm" onClick={e => e.stopPropagation()}>
                            <span className="vc-delete-prompt">Remove?</span>
                            <button className="vc-delete-yes" onClick={e => { e.stopPropagation(); onDelete(card.card_id); }}>Remove</button>
                            <button className="vc-delete-no" onClick={e => { e.stopPropagation(); setConfirmDelete(false); }}>Keep</button>
                        </span>
                    )}
                    <span className="evc-toggle-hint">{expanded ? '▲' : '▼'}</span>
                </div>
            </div>
            <h3 className="evc-title">{card.title}</h3>
            <div className="evc-field">
                <span className="evc-label">We care about</span>
                <p>{card.care_about}</p>
            </div>
            {expanded && (
                <>
                    {card.because && (
                        <div className="evc-field">
                            <span className="evc-label">Because</span>
                            <p>{card.because}</p>
                        </div>
                    )}
                    {card.looks_like?.length > 0 && (
                        <div className="evc-field">
                            <span className="evc-label">Looks like</span>
                            <ul className="evc-list">
                                {card.looks_like.map((s, i) => <li key={i}>{s}</li>)}
                            </ul>
                        </div>
                    )}
                    {card.drift_looks_like && (
                        <div className="evc-field evc-field--drift">
                            <span className="evc-label">Drift looks like</span>
                            <p>{card.drift_looks_like}</p>
                        </div>
                    )}
                    {card.in_conflict && (
                        <div className="evc-field">
                            <span className="evc-label">In conflict, we prioritise</span>
                            <p>{card.in_conflict}</p>
                        </div>
                    )}
                    {card.never_do && (
                        <div className="evc-field evc-field--never">
                            <span className="evc-label">Never</span>
                            <p>{card.never_do}</p>
                        </div>
                    )}
                </>
            )}
        </article>
    );
}

const BLANK_CARD = {
    title: '', care_about: '', because: '', looks_like_raw: '',
    drift_looks_like: '', in_conflict: '', never_do: '',
    frankl_mode: 'creative', color_key: 'honey',
};

function EntityCardForm({ entityId, entityNoun, onSaved, onCancel, editingCard }) {
    const [form, setForm] = useState(() => editingCard ? {
        title: editingCard.title || '',
        care_about: editingCard.care_about || '',
        because: editingCard.because || '',
        looks_like_raw: (editingCard.looks_like || []).join('\n'),
        drift_looks_like: editingCard.drift_looks_like || '',
        in_conflict: editingCard.in_conflict || '',
        never_do: editingCard.never_do || '',
        frankl_mode: editingCard.frankl_mode || 'creative',
        color_key: editingCard.color_key || 'honey',
    } : BLANK_CARD);
    const [saving, setSaving] = useState(false);
    const [err, setErr] = useState('');
    const set = k => e => setForm(p => ({ ...p, [k]: e.target.value }));

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!form.care_about.trim()) { setErr('What we care about is required.'); return; }
        setSaving(true); setErr('');
        try {
            const payload = { ...form, looks_like: form.looks_like_raw.split('\n').map(s => s.trim()).filter(Boolean) };
            delete payload.looks_like_raw;
            const res = editingCard
                ? await api.patch(`/api/entity_value_cards/${entityId}/${editingCard.card_id}`, payload)
                : await api.post(`/api/entity_value_cards/${entityId}`, payload);
            onSaved(res.data);
        } catch (e) {
            setErr(e.response?.data?.message || 'Failed to save.');
        } finally {
            setSaving(false);
        }
    };

    return (
        <form className="vc-new-form" onSubmit={handleSubmit} style={{ marginTop: '1.4rem' }}>
            <h4 className="vc-new-heading">{editingCard ? 'Edit Value Card' : 'New Value Card'}</h4>
            {err && <p className="vc-error">{err}</p>}
            <div className="vc-form-row"><label>Title</label><input type="text" value={form.title} onChange={set('title')} placeholder="e.g. Honest dialogue" /></div>
            <div className="vc-form-row"><label>We care about *</label><textarea rows={2} value={form.care_about} onChange={set('care_about')} placeholder={`What specifically does this ${entityNoun} care about?`} required /></div>
            <div className="vc-form-row"><label>Because</label><textarea rows={2} value={form.because} onChange={set('because')} placeholder="The reason underneath it" /></div>
            <div className="vc-form-row"><label>Looks like (one per line)</label><textarea rows={3} value={form.looks_like_raw} onChange={set('looks_like_raw')} placeholder="Observable behaviours that express this value" /></div>
            <div className="vc-form-two-col">
                <div className="vc-form-row"><label>Frankl mode</label>
                    <select value={form.frankl_mode} onChange={set('frankl_mode')}>
                        <option value="creative">✶ Creative</option>
                        <option value="experiential">❍ Experiential</option>
                        <option value="attitudinal">△ Attitudinal</option>
                    </select>
                </div>
                <div className="vc-form-row"><label>Card colour</label>
                    <select value={form.color_key} onChange={set('color_key')}>
                        <option value="honey">Honey</option>
                        <option value="leaf">Leaf</option>
                        <option value="terracotta">Terracotta</option>
                        <option value="sage">Sage</option>
                        <option value="moss">Moss</option>
                    </select>
                </div>
            </div>
            <div className="vc-form-actions">
                <button type="submit" className="btn btn-accent" disabled={saving}>
                    {saving ? 'Saving…' : (editingCard ? 'Save changes' : 'Add to Value Graph')}
                </button>
                <button type="button" className="btn btn-ghost" onClick={onCancel}>Cancel</button>
            </div>
        </form>
    );
}

function EntityValueGraph({ entityId, canManage = false, entityNoun = 'group' }) {
    const [cards, setCards] = useState([]);
    const [loading, setLoading] = useState(true);
    const [showAddCard, setShowAddCard] = useState(false);
    const [editingCard, setEditingCard] = useState(null);

    useEffect(() => {
        let active = true;
        if (!entityId) { setLoading(false); return undefined; }
        api.get(`/api/value_cards/${entityId}`)
            .then(r => { if (active) setCards(r.data || []); })
            .catch(() => { if (active) setCards([]); })
            .finally(() => { if (active) setLoading(false); });
        return () => { active = false; };
    }, [entityId]);

    const handleCardSaved = (card) => {
        if (editingCard) {
            setCards(prev => prev.map(c => c.card_id === editingCard.card_id ? card : c));
            setEditingCard(null);
        } else {
            setCards(prev => [...prev, card]);
        }
        setShowAddCard(false);
    };
    const handleCardDelete = async (cardId) => {
        try {
            await api.delete(`/api/entity_value_cards/${entityId}/${cardId}`);
            setCards(prev => prev.filter(c => c.card_id !== cardId));
        } catch (_) { /* keep the card if the delete was rejected */ }
    };

    if (loading) return <p className="ep-empty">Loading value graph…</p>;

    return (
        <div className="evg">
            {cards.length > 0 ? (
                <div className="ep-cards-grid">
                    {cards.map((card, i) => (
                        <EntityValueCard
                            key={card.card_id} card={card} idx={i}
                            canDelete={canManage} onDelete={handleCardDelete} onEdit={setEditingCard}
                        />
                    ))}
                </div>
            ) : (
                <p className="ep-empty">
                    No value cards yet.{canManage ? ' Add the values this group holds itself to.' : ''}
                </p>
            )}

            {canManage && !showAddCard && !editingCard && (
                <button className="btn btn-accent" style={{ marginTop: '1.2rem' }} onClick={() => setShowAddCard(true)}>
                    + Add to Value Graph
                </button>
            )}
            {canManage && (showAddCard || editingCard) && (
                <EntityCardForm
                    entityId={entityId}
                    entityNoun={entityNoun}
                    editingCard={editingCard}
                    onSaved={handleCardSaved}
                    onCancel={() => { setShowAddCard(false); setEditingCard(null); }}
                />
            )}
        </div>
    );
}

EntityValueGraph.propTypes = {
    entityId: PropTypes.string,
    canManage: PropTypes.bool,
    entityNoun: PropTypes.string,
};

export default EntityValueGraph;
