// SpherePage — shows a single Sphere, loaded by ?id= (or ?name=).
import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import '../styles/SpherePage.css';
import api from '../api';

function SpherePage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const name = params.get('name');
    const [sphere, setSphere] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;
        (async () => {
            try {
                const res = await api.get('/api/spheres');
                const list = res.data || [];
                const found = list.find((s) => (id && s.sphere_id === id) || (name && s.name === name));
                if (active) setSphere(found || null);
            } catch (e) {
                console.error('Error loading sphere:', e);
            } finally {
                if (active) setLoading(false);
            }
        })();
        return () => { active = false; };
    }, [id, name]);

    if (loading) return <div className="route-loading">Loading…</div>;
    if (!sphere) return <div className="container"><main><p className="empty-state">Sphere not found.</p></main></div>;

    const members = sphere.members || [];
    const unions = sphere.unions || [];
    const projects = sphere.projects || [];
    const values = sphere.values || [];

    return (
        <div className="container">
            <main>
                <article className="detail-card">
                    <span className="eyebrow">Sphere · {sphere.location || 'Community'}</span>
                    <h1>{sphere.name}</h1>
                    <p className="detail-description">{sphere.description}</p>

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
                            <h2>Unions</h2>
                            <ul className="detail-list">
                                {unions.map((u, i) => (
                                    <li key={i}><Link to={`/union?name=${encodeURIComponent(u)}`}>🔗 {u}</Link></li>
                                ))}
                                {unions.length === 0 && <li className="muted">No unions yet.</li>}
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

export default SpherePage;
