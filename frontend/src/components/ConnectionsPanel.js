// ConnectionsPanel — "Spheres / Alliances / Active projects" list, shared by
// ProfilePage, Home, and UserPage.
//
// Shows the entities `ownerId` belongs to. When `viewerId` differs from
// `ownerId` (viewing someone else's page), a sphere is only shown if the
// viewer is ALSO a member of it — and any alliance/project that belongs to a
// sphere the viewer can't see is hidden too, mirroring the backend's
// sphere-membership gating. Passing viewerId === ownerId (or omitting it)
// shows the owner's own connections unfiltered.

import React, { useState, useEffect } from 'react';
import PropTypes from 'prop-types';
import { Link } from 'react-router-dom';
import '../styles/Profile.css';
import api from '../api';

const ACTIVE_PROJECT_STATUSES = ['Initiated', 'In Progress'];

const isMemberOf = (members, id) => !!id && (members || []).some((m) => (m.id || m) === id);

function ConnectionsPanel({ ownerId, viewerId }) {
    const [spheres, setSpheres] = useState([]);
    const [alliances, setAlliances] = useState([]);
    const [projects, setProjects] = useState([]);
    const [loaded, setLoaded] = useState(false);

    useEffect(() => {
        if (!ownerId) { setLoaded(true); return undefined; }
        let active = true;
        (async () => {
            const [sphereRes, allianceRes, projectRes] = await Promise.all([
                api.get('/api/spheres').catch(() => ({ data: [] })),
                api.get('/api/alliances').catch(() => ({ data: [] })),
                api.get('/api/projects').catch(() => ({ data: [] })),
            ]);
            if (!active) return;

            const ownerSpheres = (sphereRes.data || []).filter((s) => isMemberOf(s.members, ownerId));
            const visibleSpheres = viewerId && viewerId !== ownerId
                ? ownerSpheres.filter((s) => isMemberOf(s.members, viewerId))
                : ownerSpheres;
            const visibleSphereIds = new Set(visibleSpheres.map((s) => s.sphere_id));

            const ownerAlliances = (allianceRes.data || []).filter((a) =>
                isMemberOf(a.members, ownerId) && (!a.sphere_id || visibleSphereIds.has(a.sphere_id)));
            const ownerProjects = (projectRes.data || []).filter((p) =>
                isMemberOf(p.members, ownerId)
                && ACTIVE_PROJECT_STATUSES.includes(p.status)
                && (!p.sphere_id || visibleSphereIds.has(p.sphere_id)));

            setSpheres(visibleSpheres);
            setAlliances(ownerAlliances);
            setProjects(ownerProjects);
            setLoaded(true);
        })();
        return () => { active = false; };
    }, [ownerId, viewerId]);

    if (!loaded) return null;

    const isOwnPage = !!viewerId && viewerId === ownerId;
    const nothingVisible = spheres.length === 0 && alliances.length === 0 && projects.length === 0;

    return (
        <div className="pf-sidebar">
            {spheres.length > 0 && (
                <div className="pf-sidebar-section">
                    <h4>Spheres</h4>
                    <ul className="pf-conn-list">
                        {spheres.map((s) => (
                            <li key={s.sphere_id}>
                                <Link to={`/sphere?id=${s.sphere_id}`} className="pf-conn-pill">{s.name}</Link>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            {alliances.length > 0 && (
                <div className="pf-sidebar-section">
                    <h4>Alliances</h4>
                    <ul className="pf-conn-list">
                        {alliances.map((a) => (
                            <li key={a.alliance_id}>
                                <Link to={`/alliance?id=${a.alliance_id}`} className="pf-conn-pill">{a.name}</Link>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            {projects.length > 0 && (
                <div className="pf-sidebar-section">
                    <h4>Active projects</h4>
                    <ul className="pf-conn-list">
                        {projects.map((p) => (
                            <li key={p.project_id}>
                                <Link to={`/project?id=${p.project_id}`} className="pf-conn-pill">{p.name}</Link>
                            </li>
                        ))}
                    </ul>
                </div>
            )}
            {nothingVisible && (
                <div className="pf-sidebar-section pf-sidebar-section--muted">
                    <p className="pf-sidebar-hint">
                        {isOwnPage
                            ? 'Your connections, projects, and spheres will appear here as you participate in the community.'
                            : 'No shared spheres to show yet.'}
                    </p>
                </div>
            )}
        </div>
    );
}

ConnectionsPanel.propTypes = {
    ownerId: PropTypes.string,
    viewerId: PropTypes.string,
};

export default ConnectionsPanel;
