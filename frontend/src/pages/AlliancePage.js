// AlliancePage — governance-first alliance detail page.
// Shows charter (value cards), member roster with roles, and linked projects.
import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import '../styles/EntityPage.css';
import api from '../api';
import { useLogin } from '../App';

const ROLE_META = {
    admin:   { label: 'Admin',   glyph: '◈', cls: 'role--admin' },
    steward: { label: 'Steward', glyph: '◉', cls: 'role--steward' },
    member:  { label: 'Member',  glyph: '○', cls: 'role--member' },
};

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

function AlliancePage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const name = params.get('name');
    const { userId } = useLogin();
    const [alliance, setAlliance] = useState(null);
    const [valueCards, setValueCards] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;
        (async () => {
            try {
                const res = await api.get('/api/alliances');
                const list = res.data || [];
                const found = list.find((a) =>
                    (id && (a.alliance_id === id || a.id === id)) ||
                    (name && a.name === name)
                );
                if (active && found) {
                    setAlliance(found);
                    try {
                        const vcRes = await api.get(`/api/value_cards/${found.alliance_id || found.id}`);
                        if (active) setValueCards(vcRes.data || []);
                    } catch (_) {}
                } else if (active) {
                    setAlliance(null);
                }
            } catch (e) {
                console.error('Error loading alliance:', e);
            } finally {
                if (active) setLoading(false);
            }
        })();
        return () => { active = false; };
    }, [id, name]);

    if (loading) return <div className="ep-loading">Loading…</div>;
    if (!alliance) return (
        <div className="ep-page">
            <p className="ep-not-found">Alliance not found.</p>
        </div>
    );

    const members = alliance.members || [];
    const projects = alliance.projects || [];
    const values = alliance.values || [];

    const adminMember = members.find(m => m.role === 'admin');
    const stewards = members.filter(m => m.role === 'steward');
    const regularMembers = members.filter(m => m.role === 'member');

    const currentMember = members.find(m => m.id === userId);
    const canManage = currentMember?.role === 'admin' || currentMember?.role === 'steward';

    return (
        <div className="ep-page ep-page--alliance">

            {/* Hero */}
            <header className="ep-hero">
                <div className="ep-hero-inner">
                    <div className="ep-meta-row">
                        <span className="ep-eyebrow">Alliance</span>
                        {alliance.sphere_name && (
                            <Link
                                to={`/sphere?id=${alliance.sphere_id}`}
                                className="ep-sphere-chip"
                            >
                                {alliance.sphere_name}
                            </Link>
                        )}
                        {canManage && (
                            <Link
                                to={`/alliance-management?id=${alliance.alliance_id}`}
                                className="ep-status-badge status--in-progress"
                                style={{ textDecoration: 'none' }}
                            >
                                Manage Alliance
                            </Link>
                        )}
                    </div>
                    <h1 className="ep-title">{alliance.name}</h1>
                    <p className="ep-description">{alliance.description}</p>
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

                {/* Governance roster */}
                <section className="ep-section ep-section--governance">
                    <h2 className="ep-section-title">
                        <span className="ep-section-glyph">◈</span> Governance
                    </h2>

                    {adminMember && (
                        <div className="ep-role-tier">
                            <span className="ep-role-label role--admin">Admin</span>
                            <div className="ep-roster ep-roster--single">
                                <Link to={`/user?id=${adminMember.id}`} className="ep-member-pill ep-member-pill--admin">
                                    <span className="ep-member-initial">{adminMember.name?.[0]}</span>
                                    <span className="ep-member-name">{adminMember.name}</span>
                                </Link>
                            </div>
                        </div>
                    )}

                    {stewards.length > 0 && (
                        <div className="ep-role-tier">
                            <span className="ep-role-label role--steward">Stewards</span>
                            <div className="ep-roster">
                                {stewards.map(m => (
                                    <Link key={m.id} to={`/user?id=${m.id}`} className="ep-member-pill ep-member-pill--steward">
                                        <span className="ep-member-initial">{m.name?.[0]}</span>
                                        <span className="ep-member-name">{m.name}</span>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}

                    {regularMembers.length > 0 && (
                        <div className="ep-role-tier">
                            <span className="ep-role-label role--member">Members</span>
                            <div className="ep-roster">
                                {regularMembers.map(m => (
                                    <Link key={m.id} to={`/user?id=${m.id}`} className="ep-member-pill">
                                        <span className="ep-member-initial">{m.name?.[0]}</span>
                                        <span className="ep-member-name">{m.name}</span>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}

                    {members.length === 0 && (
                        <p className="ep-empty">No members yet.</p>
                    )}
                </section>

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

                {/* Charter — value cards */}
                {valueCards.length > 0 && (
                    <section className="ep-section ep-section--charter">
                        <h2 className="ep-section-title">
                            <span className="ep-section-glyph">◻</span> Charter
                            <span className="ep-section-sub">The values this alliance holds itself to</span>
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

export default AlliancePage;
