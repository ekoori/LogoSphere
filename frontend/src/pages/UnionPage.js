// UnionPage — shows a single Union, loaded by ?id= (or ?name=).
import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import '../styles/UnionPage.css';
import api from '../api';

function UnionPage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const name = params.get('name');
    const [union, setUnion] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;
        (async () => {
            try {
                const res = await api.get('/api/unions');
                const list = res.data || [];
                const found = list.find((u) => (id && u.union_id === id) || (name && u.name === name));
                if (active) setUnion(found || null);
            } catch (e) {
                console.error('Error loading union:', e);
            } finally {
                if (active) setLoading(false);
            }
        })();
        return () => { active = false; };
    }, [id, name]);

    if (loading) return <div className="route-loading">Loading…</div>;
    if (!union) return <div className="container"><main><p className="empty-state">Union not found.</p></main></div>;

    const members = union.members || [];
    const projects = union.projects || [];
    const values = union.values || [];

    return (
        <div className="container">
            <main>
                <article className="detail-card">
                    <span className="eyebrow">Union</span>
                    <h1>{union.name}</h1>
                    {union.sphere_name && (
                        <p className="detail-meta">Part of <Link to={`/sphere?name=${encodeURIComponent(union.sphere_name)}`}>{union.sphere_name}</Link></p>
                    )}
                    <p className="detail-description">{union.description}</p>

                    {values.length > 0 && (
                        <div className="detail-values">
                            {values.map((v, i) => <span key={i}>#{v}</span>)}
                        </div>
                    )}

                    <div className="detail-grid">
                        <section className="detail-section">
                            <h2>Members ({members.length})</h2>
                            <ul className="detail-list">
                                {members.map((m, i) => (
                                    <li key={i}><Link to={`/user?id=${m.id}`}>👤 {m.name}</Link></li>
                                ))}
                                {members.length === 0 && <li className="muted">No members yet.</li>}
                            </ul>
                        </section>

                        <section className="detail-section">
                            <h2>Projects</h2>
                            <ul className="detail-list">
                                {projects.map((p, i) => (
                                    <li key={i}><Link to={`/project?name=${encodeURIComponent(p)}`}>🌱 {p}</Link></li>
                                ))}
                                {projects.length === 0 && <li className="muted">No projects yet.</li>}
                            </ul>
                        </section>
                    </div>
                </article>
            </main>
        </div>
    );
}

export default UnionPage;
