// SpherePage — sphere detail with value cards charter and linked entities.
import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import '../styles/EntityPage.css';
import api from '../api';

const FRANKL_META = {
    creative:     { glyph: '✶', label: 'Creative' },
    experiential: { glyph: '❍', label: 'Experiential' },
    attitudinal:  { glyph: '△', label: 'Attitudinal' },
};

const COLOR_CSS = {
    honey: '--honey', leaf: '--leaf', terracotta: '--terracotta',
    sage: '--sage', moss: '--moss',
};

function EntityValueCard({ card, idx }) {
    const [expanded, setExpanded] = useState(false);
    const meta = FRANKL_META[card.frankl_mode] || FRANKL_META.creative;
    const accentVar = COLOR_CSS[card.color_key] || '--honey';
    const rot = (idx % 2 === 0) ? '-0.6deg' : '0.5deg';

    return (
        <article
            className={`evc-card ${expanded ? 'evc-card--expanded' : ''}`}
            style={{ '--evc-accent': `var(${accentVar})`, '--evc-rot': rot }}
            onClick={() => setExpanded(v => !v)}
        >
            <span className="evc-punch" aria-hidden="true" />
            <div className="evc-top">
                <span className="evc-mode">{meta.glyph} {meta.label}</span>
                <span className="evc-toggle-hint">{expanded ? '▲' : '▼'}</span>
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

function SpherePage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const name = params.get('name');
    const [sphere, setSphere] = useState(null);
    const [valueCards, setValueCards] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;
        (async () => {
            try {
                const res = await api.get('/api/spheres');
                const list = res.data || [];
                const found = list.find((s) =>
                    (id && s.sphere_id === id) ||
                    (name && s.name === name)
                );
                if (active && found) {
                    setSphere(found);
                    try {
                        const vcRes = await api.get(`/api/value_cards/${found.sphere_id}`);
                        if (active) setValueCards(vcRes.data || []);
                    } catch (_) {}
                } else if (active) {
                    setSphere(null);
                }
            } catch (e) {
                console.error('Error loading sphere:', e);
            } finally {
                if (active) setLoading(false);
            }
        })();
        return () => { active = false; };
    }, [id, name]);

    if (loading) return <div className="ep-loading">Loading…</div>;
    if (!sphere) return (
        <div className="ep-page">
            <p className="ep-not-found">Sphere not found.</p>
        </div>
    );

    const participants = sphere.participants || [];
    const alliances = sphere.alliances || [];
    const projects = sphere.projects || [];
    const values = sphere.values || [];

    return (
        <div className="ep-page ep-page--sphere">

            {/* Hero */}
            <header className="ep-hero ep-hero--sphere">
                <div className="ep-hero-inner">
                    <div className="ep-meta-row">
                        <span className="ep-eyebrow">Sphere</span>
                        {sphere.location && (
                            <span className="ep-location-chip">
                                {sphere.location}
                            </span>
                        )}
                        {participants.length > 0 && (
                            <span className="ep-location-chip">
                                {participants.length} member{participants.length !== 1 ? 's' : ''}
                            </span>
                        )}
                    </div>
                    <h1 className="ep-title">{sphere.name}</h1>
                    <p className="ep-description">{sphere.description}</p>
                    {values.length > 0 && (
                        <div className="ep-tags">
                            {values.map((v, i) => (
                                <span key={i} className="ep-tag">#{v}</span>
                            ))}
                        </div>
                    )}
                </div>
            </header>

            <div className="ep-body">

                {/* Alliances */}
                {alliances.length > 0 && (
                    <section className="ep-section ep-section--projects">
                        <h2 className="ep-section-title">
                            <span className="ep-section-glyph">◎</span> Alliances
                        </h2>
                        <ul className="ep-project-list">
                            {alliances.map((a, i) => (
                                <li key={i}>
                                    <Link to={`/alliance?name=${encodeURIComponent(a)}`} className="ep-project-link">
                                        {a}
                                        <span className="ep-project-arrow">→</span>
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </section>
                )}

                {/* Projects */}
                {projects.length > 0 && (
                    <section className="ep-section ep-section--projects">
                        <h2 className="ep-section-title">
                            <span className="ep-section-glyph">◎</span> Projects
                        </h2>
                        <ul className="ep-project-list">
                            {projects.map((p, i) => (
                                <li key={i}>
                                    <Link to={`/project?name=${encodeURIComponent(p)}`} className="ep-project-link">
                                        {p}
                                        <span className="ep-project-arrow">→</span>
                                    </Link>
                                </li>
                            ))}
                        </ul>
                    </section>
                )}

                {/* Charter */}
                {valueCards.length > 0 && (
                    <section className="ep-section ep-section--charter">
                        <h2 className="ep-section-title">
                            <span className="ep-section-glyph">◻</span> Charter
                            <span className="ep-section-sub">The values this sphere holds itself to</span>
                        </h2>
                        <div className="ep-cards-grid">
                            {valueCards.map((card, i) => (
                                <EntityValueCard key={card.card_id} card={card} idx={i} />
                            ))}
                        </div>
                    </section>
                )}
            </div>
        </div>
    );
}

export default SpherePage;
