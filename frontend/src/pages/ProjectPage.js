// ProjectPage — Meaning Trail + Openings in the main focus (like UserPage),
// governance/contributors/charter on the side, banner up top.
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import '../styles/EntityPage.css';
import '../styles/ValueCardChip.css';
import api from '../api';
import { useLogin } from '../App';
import EntityBanner from '../components/EntityBanner';
import CompactValueGraph from '../components/CompactValueGraph';
import Openings from '../components/Openings';
import MeaningTrail from '../components/MeaningTrail';
import TabSelector from '../components/TabSelector';
import MembersList from '../components/MembersList';
import Avatar from '../components/Avatar';
import { mapService } from '../utils/mappers';
import { fetchAggregateTrail } from '../utils/entityTrail';

const STATUS_META = {
    'Initiated':   { cls: 'status--initiated',   label: 'Initiated' },
    'In Progress': { cls: 'status--in-progress',  label: 'In Progress' },
    'Completed':   { cls: 'status--completed',    label: 'Completed' },
    'Paused':      { cls: 'status--paused',       label: 'Paused' },
};

function ProjectPage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const name = params.get('name');
    const { userId } = useLogin();
    const [project, setProject] = useState(null);
    const [openings, setOpenings] = useState([]);
    const [trail, setTrail] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('meaning_trail');
    const [showNewOpening, setShowNewOpening] = useState(false);

    const fetchProject = useCallback(async () => {
        try {
            const res = await api.get('/api/projects');
            const list = res.data || [];
            const found = list.find((p) =>
                (id && (p.project_id === id || p.id === id)) ||
                (name && p.name === name)
            );
            if (found) {
                setProject(found);
                const pid = found.project_id || found.id;
                try {
                    const opRes = await api.get('/api/openings');
                    setOpenings((opRes.data || [])
                        .filter((s) => s.project_name === found.name || s.provider_id === pid)
                        .map(mapService));
                } catch (_) {}
                try {
                    const rows = await fetchAggregateTrail({ ownEntityIds: [pid], projectIds: [pid] }, userId);
                    setTrail(rows);
                } catch (_) {}
            } else {
                setProject(null);
            }
        } catch (e) {
            console.error('Error loading project:', e);
        } finally {
            setLoading(false);
        }
    }, [id, name, userId]);

    useEffect(() => { fetchProject(); }, [fetchProject]);

    if (loading) return <div className="ep-loading">Loading…</div>;
    if (!project) return (
        <div className="ep-page">
            <p className="ep-not-found">Project not found.</p>
        </div>
    );

    const pid = project.project_id || project.id;
    const members = project.members || [];
    const statusInfo = STATUS_META[project.status] || { cls: 'status--initiated', label: project.status || 'Active' };

    const managers = members.filter(m => m.role === 'manager');
    const contributors = members.filter(m => m.role === 'contributor');
    const observers = members.filter(m => m.role === 'observer');
    const currentMember = members.find(m => m.id === userId);
    const canManage = currentMember?.role === 'manager';

    const actingAs = {
        id: pid, name: project.name,
        sphereId: project.sphere_id, sphereName: project.sphere_name,
        projectName: project.name,
    };

    return (
        <div className="ep-page ep-page--project">
            <EntityBanner kind="project" imageUrl={project.has_image ? `/api/projects/${pid}/image` : undefined}>
                <div className="ep-meta-row">
                    <span className="ep-eyebrow">Project</span>
                    <span className={`ep-status-badge ${statusInfo.cls}`}>{statusInfo.label}</span>
                    {project.sphere_name && (
                        <Link to={`/sphere?id=${project.sphere_id}`} className="ep-sphere-chip">
                            {project.sphere_name}
                        </Link>
                    )}
                    {canManage && (
                        <Link to={`/project-management?id=${pid}`} className="ep-status-badge status--in-progress" style={{ textDecoration: 'none' }}>
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
            </EntityBanner>

            <div className="ep-layout">
                {/* ── Sidebar: governance, charter ─────────────────────── */}
                <aside className="ep-aside">
                    <div className="ep-aside-section">
                        <h4>Contributors</h4>
                        {managers.length > 0 && (
                            <div className="ep-role-tier">
                                <span className="ep-role-label role--admin">Manager</span>
                                <div className="ep-roster">
                                    {managers.map(m => (
                                        <Link key={m.id} to={`/user?id=${m.id}`} className="ep-member-pill ep-member-pill--admin">
                                            <Avatar userId={m.id} name={m.name} size={22} />
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
                                            <Avatar userId={m.id} name={m.name} size={22} />
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
                                            <Avatar userId={m.id} name={m.name} size={22} />
                                            <span className="ep-member-name">{m.name}</span>
                                        </Link>
                                    ))}
                                </div>
                            </div>
                        )}
                        {members.length === 0 && <p className="ep-empty">No contributors yet.</p>}
                    </div>

                    <div className="ep-aside-section">
                        <h4>Charter</h4>
                        <CompactValueGraph
                            entityId={pid}
                            currentUserId={userId}
                            manageHref={canManage ? `/project-management?id=${pid}` : null}
                        />
                    </div>
                </aside>

                {/* ── Main: Meaning Trail / Openings ───────────────────── */}
                <main className="ep-main">
                    <TabSelector
                        tabs={[
                            { key: 'meaning_trail', label: 'Meaning Trail' },
                            { key: 'offers-needs', label: 'Offers & Needs' },
                            { key: 'members', label: `People (${members.length})` },
                        ]}
                        active={activeTab}
                        onChange={setActiveTab}
                    />

                    {activeTab === 'members' && (
                        <MembersList
                            kind="project"
                            entityId={pid}
                            members={members}
                            canManage={canManage}
                            currentUserId={userId}
                            onChanged={fetchProject}
                        />
                    )}

                    {activeTab === 'meaning_trail' && (
                        trail.length === 0
                            ? <p className="empty-state">No meaning trail recorded yet for this project.</p>
                            : <MeaningTrail items={trail} />
                    )}

                    {activeTab === 'offers-needs' && (
                        <>
                            {canManage && (
                                <div className="ep-manage-form-toggle">
                                    <button className="btn btn-accent" onClick={() => setShowNewOpening(v => !v)}>
                                        {showNewOpening ? 'Cancel' : `+ Post an Opening as ${project.name}`}
                                    </button>
                                </div>
                            )}
                            {openings.length === 0 && !showNewOpening ? (
                                <p className="empty-state">No offers or needs posted for this project yet.</p>
                            ) : (
                                <Openings
                                    services={openings}
                                    newServiceVisible={showNewOpening}
                                    onServiceAdded={fetchProject}
                                    currentUserId={userId}
                                    actingAs={canManage ? actingAs : null}
                                />
                            )}
                        </>
                    )}
                </main>
            </div>
        </div>
    );
}

export default ProjectPage;
