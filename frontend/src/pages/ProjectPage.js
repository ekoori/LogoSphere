// ProjectPage — shows a single Project, loaded by ?id= (or ?name=).
import React, { useState, useEffect } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import '../styles/ProjectPage.css';
import api from '../api';

function ProjectPage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const name = params.get('name');
    const [project, setProject] = useState(null);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;
        (async () => {
            try {
                const res = await api.get('/api/projects');
                const list = res.data || [];
                const found = list.find((p) => (id && p.project_id === id) || (name && p.name === name));
                if (active) setProject(found || null);
            } catch (e) {
                console.error('Error loading project:', e);
            } finally {
                if (active) setLoading(false);
            }
        })();
        return () => { active = false; };
    }, [id, name]);

    if (loading) return <div className="route-loading">Loading…</div>;
    if (!project) return <div className="container"><main><p className="empty-state">Project not found.</p></main></div>;

    const members = project.members || [];
    const values = project.values || [];

    return (
        <div className="container">
            <main>
                <article className="detail-card">
                    <span className="eyebrow">Project · {project.status || 'Active'}</span>
                    <h1>{project.name}</h1>
                    <p className="detail-meta">
                        {project.owner_union && <>Led by <Link to={`/union?name=${encodeURIComponent(project.owner_union)}`}>{project.owner_union}</Link></>}
                        {project.sphere_name && <> · in <Link to={`/sphere?name=${encodeURIComponent(project.sphere_name)}`}>{project.sphere_name}</Link></>}
                    </p>
                    <p className="detail-description">{project.description}</p>

                    {values.length > 0 && (
                        <div className="detail-values">
                            {values.map((v, i) => <span key={i}>#{v}</span>)}
                        </div>
                    )}

                    <div className="detail-grid">
                        <section className="detail-section">
                            <h2>Contributors ({members.length})</h2>
                            <ul className="detail-list">
                                {members.map((m, i) => (
                                    <li key={i}><Link to={`/user?id=${m.id}`}>👤 {m.name}</Link></li>
                                ))}
                                {members.length === 0 && <li className="muted">No contributors yet.</li>}
                            </ul>
                        </section>
                    </div>
                </article>
            </main>
        </div>
    );
}

export default ProjectPage;
