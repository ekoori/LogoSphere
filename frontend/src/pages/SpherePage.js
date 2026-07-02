// SpherePage — Meaning Trail + Openings in the main focus (like UserPage),
// membership/alliances/projects/charter on the side, banner up top. Non-members
// see the banner and a join prompt but not the sphere's internal activity. The
// trail aggregates the sphere's own direct activity, every alliance's, and
// every project's.
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import '../styles/EntityPage.css';
import '../styles/ValueCardChip.css';
import api from '../api';
import CompactValueGraph from '../components/CompactValueGraph';
import EntityBanner from '../components/EntityBanner';
import Openings from '../components/Openings';
import MeaningTrail from '../components/MeaningTrail';
import TabSelector from '../components/TabSelector';
import { mapService } from '../utils/mappers';
import { fetchAggregateTrail } from '../utils/entityTrail';
import { useLogin } from '../App';

function SpherePage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const name = params.get('name');
    const { userId } = useLogin();
    const [sphere, setSphere] = useState(null);
    const [openings, setOpenings] = useState([]);
    const [trail, setTrail] = useState([]);
    const [loading, setLoading] = useState(true);
    const [joining, setJoining] = useState(false);
    const [activeTab, setActiveTab] = useState('meaning_trail');
    const [showNewOpening, setShowNewOpening] = useState(false);

    const fetchSphere = useCallback(async () => {
        try {
            const res = await api.get('/api/spheres');
            const list = res.data || [];
            const found = list.find((s) =>
                (id && s.sphere_id === id) ||
                (name && s.name === name)
            );
            if (!found) { setSphere(null); return; }
            setSphere(found);

            const isMember = !!userId && (found.participants || found.members || [])
                .some((p) => (p.id || p) === userId);
            if (!isMember) return; // openings/trail are members-only; nothing more to fetch

            // The API already only returns openings from spheres the viewer
            // belongs to, so a non-member simply gets none here regardless.
            try {
                const opRes = await api.get('/api/openings');
                setOpenings((opRes.data || [])
                    .filter((s) => s.sphere_id === found.sphere_id)
                    .map(mapService));
            } catch (_) {}

            try {
                const [allAlliances, allProjects] = await Promise.all([
                    api.get('/api/alliances').then((r) => r.data || []).catch(() => []),
                    api.get('/api/projects').then((r) => r.data || []).catch(() => []),
                ]);
                const allianceIds = allAlliances
                    .filter((a) => (found.alliances || []).includes(a.name))
                    .map((a) => a.alliance_id || a.id);
                const projectIds = allProjects
                    .filter((p) => (found.projects || []).includes(p.name))
                    .map((p) => p.project_id || p.id);
                const rows = await fetchAggregateTrail(
                    { ownEntityIds: [found.sphere_id, ...allianceIds], projectIds },
                    userId
                );
                setTrail(rows);
            } catch (_) {}
        } catch (e) {
            console.error('Error loading sphere:', e);
        } finally {
            setLoading(false);
        }
    }, [id, name, userId]);

    useEffect(() => { fetchSphere(); }, [fetchSphere]);

    if (loading) return <div className="ep-loading">Loading…</div>;
    if (!sphere) return (
        <div className="ep-page">
            <p className="ep-not-found">Sphere not found.</p>
        </div>
    );

    const participants = sphere.participants || [];
    const alliances = sphere.alliances || [];
    const projects = sphere.projects || [];
    const isMember = !!userId && participants.some(p => (p.id || p) === userId);
    const isAdmin = !!userId && userId === sphere.admin1;
    const canManage = !!userId && (participants.length === 0 || isMember);

    const actingAs = { id: sphere.sphere_id, name: sphere.name, sphereId: sphere.sphere_id, sphereName: sphere.name };

    const handleJoin = async () => {
        if (joining || !userId) return;
        setJoining(true);
        try {
            await api.post(`/api/spheres/${sphere.sphere_id}/join`);
            await fetchSphere();
        } catch (e) {
            console.error('Failed to join sphere:', e);
        } finally {
            setJoining(false);
        }
    };

    return (
        <div className="ep-page ep-page--sphere">
            <EntityBanner kind="sphere" image={sphere.image}>
                <div className="ep-meta-row">
                    <span className="ep-eyebrow">Sphere</span>
                    {sphere.location && <span className="ep-location-chip">{sphere.location}</span>}
                    {participants.length > 0 && (
                        <span className="ep-location-chip">
                            {participants.length} member{participants.length !== 1 ? 's' : ''}
                        </span>
                    )}
                    {isAdmin && (
                        <Link to={`/sphere-management?id=${sphere.sphere_id}`} className="ep-status-badge status--in-progress" style={{ textDecoration: 'none' }}>
                            Manage Sphere
                        </Link>
                    )}
                </div>
                <h1 className="ep-title">{sphere.name}</h1>
                <p className="ep-description">{sphere.description}</p>
                {!isMember && userId && (
                    <button className="btn btn-accent" onClick={handleJoin} disabled={joining} style={{ marginTop: '0.6rem' }}>
                        {joining ? 'Joining…' : '+ Join this Sphere'}
                    </button>
                )}
            </EntityBanner>

            {!isMember ? (
                <p className="ep-empty" style={{ padding: '0 0.5rem' }}>
                    {userId
                        ? "Join this sphere to see its meaning trail, openings, alliances, and projects."
                        : 'Log in and join this sphere to see its activity.'}
                </p>
            ) : (
                <div className="ep-layout">
                    {/* ── Sidebar: alliances, projects, charter ────────── */}
                    <aside className="ep-aside">
                        {alliances.length > 0 && (
                            <div className="ep-aside-section">
                                <h4>Alliances</h4>
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
                            </div>
                        )}

                        {projects.length > 0 && (
                            <div className="ep-aside-section">
                                <h4>Projects</h4>
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
                            </div>
                        )}

                        <div className="ep-aside-section">
                            <h4>Charter</h4>
                            <CompactValueGraph
                                entityId={sphere.sphere_id}
                                manageHref={isAdmin ? `/sphere-management?id=${sphere.sphere_id}` : null}
                            />
                        </div>
                    </aside>

                    {/* ── Main: Meaning Trail / Openings ───────────────── */}
                    <main className="ep-main">
                        <TabSelector
                            tabs={[
                                { key: 'meaning_trail', label: 'Meaning Trail' },
                                { key: 'offers-needs', label: 'Offers & Needs' },
                            ]}
                            active={activeTab}
                            onChange={setActiveTab}
                        />

                        {activeTab === 'meaning_trail' && (
                            trail.length === 0
                                ? <p className="empty-state">No meaning trail recorded yet for this sphere.</p>
                                : <MeaningTrail items={trail} />
                        )}

                        {activeTab === 'offers-needs' && (
                            <>
                                {canManage && (
                                    <div className="ep-manage-form-toggle">
                                        <button className="btn btn-accent" onClick={() => setShowNewOpening(v => !v)}>
                                            {showNewOpening ? 'Cancel' : `+ Post an Opening as ${sphere.name}`}
                                        </button>
                                    </div>
                                )}
                                {openings.length === 0 && !showNewOpening ? (
                                    <p className="empty-state">No openings posted in this sphere yet.</p>
                                ) : (
                                    <Openings
                                        services={openings}
                                        newServiceVisible={showNewOpening}
                                        onServiceAdded={fetchSphere}
                                        currentUserId={userId}
                                        actingAs={canManage ? actingAs : null}
                                    />
                                )}
                            </>
                        )}
                    </main>
                </div>
            )}
        </div>
    );
}

export default SpherePage;
