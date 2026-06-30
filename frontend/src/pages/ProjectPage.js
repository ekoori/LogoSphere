// ProjectPage — governance-first project detail page.
// Shows charter (value cards), contributor roster with roles, status, and alliance.
import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import '../styles/EntityPage.css';
import api from '../api';
import { useLogin } from '../App';

const FRANKL_META = {
    creative:     { glyph: '✶', label: 'Creative' },
    experiential: { glyph: '❍', label: 'Experiential' },
    attitudinal:  { glyph: '△', label: 'Attitudinal' },
};

const COLOR_CSS = {
    honey: '--honey', leaf: '--leaf', terracotta: '--terracotta',
    sage: '--sage', moss: '--moss',
};

const STATUS_META = {
    'Initiated':   { cls: 'status--initiated',   label: 'Initiated' },
    'In Progress': { cls: 'status--in-progress',  label: 'In Progress' },
    'Completed':   { cls: 'status--completed',    label: 'Completed' },
    'Paused':      { cls: 'status--paused',       label: 'Paused' },
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

function ProjectPage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const name = params.get('name');
    const { userId } = useLogin();
    const [project, setProject] = useState(null);
    const [valueCards, setValueCards] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;
        (async () => {
            try {
                const res = await api.get('/api/projects');
                const list = res.data || [];
                const found = list.find((p) =>
                    (id && (p.project_id === id || p.id === id)) ||
                    (name && p.name === name)
                );
                if (active && found) {
                    setProject(found);
                    try {
                        const vcRes = await api.get(`/api/value_cards/${found.project_id || found.id}`);
                        if (active) setValueCards(vcRes.data || []);
                    } catch (_) {}
                } else if (active) {
                    setProject(null);
                }
            } catch (e) {
                console.error('Error loading project:', e);
            } finally {
                if (active) setLoading(false);
            }
        })();
        return () => { active = false; };
    }, [id, name]);

    if (loading) return <div className="ep-loading">Loading…</div>;
    if (!project) return (
        <div className="ep-page">
            <p className="ep-not-found">Project not found.</p>
        </div>
    );

    const members = project.members || [];
    const values = project.values || [];
    const statusInfo = STATUS_META[project.status] || { cls: 'status--initiated', label: project.status || 'Active' };

    const managers = members.filter(m => m.role === 'manager');
    const contributors = members.filter(m => m.role === 'contributor');
    const currentMember = members.find(m => m.id === userId);
    const canManage = currentMember?.role === 'manager';
    const observers = members.filter(m => m.role === 'observer');

    return (
        <div className="ep-page ep-page--project">

            {/* Hero */}
            <header className="ep-hero ep-hero--project">
                <div className="ep-hero-inner">
                    <div className="ep-meta-row">
                        <span className="ep-eyebrow">Project</span>
                        <span className={`ep-status-badge ${statusInfo.cls}`}>{statusInfo.label}</span>
                        {project.sphere_name && (
                            <Link
                                to={`/sphere?id=${project.sphere_id}`}
                                className="ep-sphere-chip"
                            >
                                {project.sphere_name}
                            </Link>
                        )}
                        {canManage && (
                            <Link
                                to={`/project-management?id=${project.project_id}`}
                                className="ep-status-badge status--in-progress"
                                style={{ textDecoration: 'none' }}
                            >
                                Manage Project
                            </Link>
                        )}
                    </div>
                    <h1 className="ep-title">{project.name}</h1>
                    {project.owner_alliance && (
                        <p className="ep-lead-alliance">
                            Led by{' '}
                            <Link to={`/alliance?name=${encodeURIComponent(project.owner_alliance)}`} className="ep-alliance-link">
                                {project.owner_alliance}
                            </Link>
                        </p>
                    )}
                    <p className="ep-description">{project.description}</p>
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
                        <span className="ep-section-glyph">◈</span> Contributors
                    </h2>

                    {managers.length > 0 && (
                        <div className="ep-role-tier">
                            <span className="ep-role-label role--admin">Manager</span>
                            <div className="ep-roster">
                                {managers.map(m => (
                                    <Link key={m.id} to={`/user?id=${m.id}`} className="ep-member-pill ep-member-pill--admin">
                                        <span className="ep-member-initial">{m.name?.[0]}</span>
                                        <span className="ep-member-name">{m.name}</span>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}

                    {contributors.length > 0 && (
                        <div className="ep-role-tier">
                            <span className="ep-role-label role--steward">Contributors</span>
                            <div className="ep-roster">
                                {contributors.map(m => (
                                    <Link key={m.id} to={`/user?id=${m.id}`} className="ep-member-pill ep-member-pill--steward">
                                        <span className="ep-member-initial">{m.name?.[0]}</span>
                                        <span className="ep-member-name">{m.name}</span>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}

                    {observers.length > 0 && (
                        <div className="ep-role-tier">
                            <span className="ep-role-label role--member">Observers</span>
                            <div className="ep-roster">
                                {observers.map(m => (
                                    <Link key={m.id} to={`/user?id=${m.id}`} className="ep-member-pill">
                                        <span className="ep-member-initial">{m.name?.[0]}</span>
                                        <span className="ep-member-name">{m.name}</span>
                                    </Link>
                                ))}
                            </div>
                        </div>
                    )}

                    {members.length === 0 && (
                        <p className="ep-empty">No contributors yet.</p>
                    )}
                </section>

                {/* Charter — value cards */}
                {valueCards.length > 0 && (
                    <section className="ep-section ep-section--charter">
                        <h2 className="ep-section-title">
                            <span className="ep-section-glyph">◻</span> Charter
                            <span className="ep-section-sub">The values this project holds itself to</span>
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

export default ProjectPage;
