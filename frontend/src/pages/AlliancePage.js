// AlliancePage — Meaning Trail + Openings in the main focus (like UserPage),
// governance/projects/charter on the side, banner up top. The trail aggregates
// the alliance's own direct activity plus every one of its listed projects'.
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import '../styles/EntityPage.css';
import '../styles/ValueCardChip.css';
import api from '../api';
import { useLogin } from '../App';
import CompactValueGraph from '../components/CompactValueGraph';
import EntityBanner from '../components/EntityBanner';
import Openings from '../components/Openings';
import MeaningTrail from '../components/MeaningTrail';
import TabSelector from '../components/TabSelector';
import MembersList from '../components/MembersList';
import Avatar from '../components/Avatar';
import { mapService } from '../utils/mappers';
import { fetchAggregateTrail } from '../utils/entityTrail';

function AlliancePage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const name = params.get('name');
    const { userId } = useLogin();
    const [alliance, setAlliance] = useState(null);
    const [openings, setOpenings] = useState([]);
    const [trail, setTrail] = useState([]);
    const [loading, setLoading] = useState(true);
    const [activeTab, setActiveTab] = useState('meaning_trail');
    const [showNewOpening, setShowNewOpening] = useState(false);

    const fetchAlliance = useCallback(async () => {
        try {
            const res = await api.get('/api/alliances');
            const list = res.data || [];
            const found = list.find((a) =>
                (id && (a.alliance_id === id || a.id === id)) ||
                (name && a.name === name)
            );
            if (found) {
                setAlliance(found);
                const aid = found.alliance_id || found.id;
                const allProjects = await api.get('/api/projects').then((r) => r.data || []).catch(() => []);
                const ownProjectIds = allProjects
                    .filter((p) => (found.projects || []).includes(p.name))
                    .map((p) => p.project_id || p.id);

                try {
                    const opRes = await api.get('/api/openings');
                    const projectNames = new Set(found.projects || []);
                    setOpenings((opRes.data || [])
                        .filter((s) => s.provider_id === aid || (s.project_name && projectNames.has(s.project_name)))
                        .map(mapService));
                } catch (_) {}

                try {
                    const rows = await fetchAggregateTrail({ ownEntityIds: [aid], projectIds: ownProjectIds }, userId);
                    setTrail(rows);
                } catch (_) {}
            } else {
                setAlliance(null);
            }
        } catch (e) {
            console.error('Error loading alliance:', e);
        } finally {
            setLoading(false);
        }
    }, [id, name, userId]);

    useEffect(() => { fetchAlliance(); }, [fetchAlliance]);

    if (loading) return <div className="ep-loading">Loading…</div>;
    if (!alliance) return (
        <div className="ep-page">
            <p className="ep-not-found">Alliance not found.</p>
        </div>
    );

    const aid = alliance.alliance_id || alliance.id;
    const members = alliance.members || [];
    const projects = alliance.projects || [];

    const adminMember = members.find(m => m.role === 'admin');
    const stewards = members.filter(m => m.role === 'steward');
    const regularMembers = members.filter(m => m.role === 'member');

    const currentMember = members.find(m => m.id === userId);
    const canManage = currentMember?.role === 'admin' || currentMember?.role === 'steward';

    const actingAs = {
        id: aid, name: alliance.name,
        sphereId: alliance.sphere_id, sphereName: alliance.sphere_name,
    };

    return (
        <div className="ep-page ep-page--alliance">
            <EntityBanner kind="alliance" image={alliance.image}>
                <div className="ep-meta-row">
                    <span className="ep-eyebrow">Alliance</span>
                    {alliance.sphere_name && (
                        <Link to={`/sphere?id=${alliance.sphere_id}`} className="ep-sphere-chip">
                            {alliance.sphere_name}
                        </Link>
                    )}
                    {canManage && (
                        <Link to={`/alliance-management?id=${aid}`} className="ep-status-badge status--in-progress" style={{ textDecoration: 'none' }}>
                            Manage Alliance
                        </Link>
                    )}
                </div>
                <h1 className="ep-title">{alliance.name}</h1>
                <p className="ep-description">{alliance.description}</p>
            </EntityBanner>

            <div className="ep-layout">
                {/* ── Sidebar: governance, projects, charter ───────────── */}
                <aside className="ep-aside">
                    <div className="ep-aside-section">
                        <h4>Governance</h4>
                        {adminMember && (
                            <div className="ep-role-tier">
                                <span className="ep-role-label role--admin">Lead</span>
                                <div className="ep-roster ep-roster--single">
                                    <Link to={`/user?id=${adminMember.id}`} className="ep-member-pill ep-member-pill--admin">
                                        <Avatar userId={adminMember.id} name={adminMember.name} size={22} />
                                        <span className="ep-member-name">{adminMember.name}</span>
                                    </Link>
                                </div>
                            </div>
                        )}
                        {stewards.length > 0 && (
                            <div className="ep-role-tier">
                                <span className="ep-role-label role--steward">Board members</span>
                                <div className="ep-roster">
                                    {stewards.map(m => (
                                        <Link key={m.id} to={`/user?id=${m.id}`} className="ep-member-pill ep-member-pill--steward">
                                            <Avatar userId={m.id} name={m.name} size={22} />
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
                                            <Avatar userId={m.id} name={m.name} size={22} />
                                            <span className="ep-member-name">{m.name}</span>
                                        </Link>
                                    ))}
                                </div>
                            </div>
                        )}
                        {members.length === 0 && <p className="ep-empty">No members yet.</p>}
                    </div>

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
                            entityId={aid}
                            manageHref={canManage ? `/alliance-management?id=${aid}` : null}
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
                            kind="alliance"
                            entityId={aid}
                            members={members}
                            canManage={currentMember?.role === 'admin'}
                            currentUserId={userId}
                            onChanged={fetchAlliance}
                        />
                    )}

                    {activeTab === 'meaning_trail' && (
                        trail.length === 0
                            ? <p className="empty-state">No meaning trail recorded yet for this alliance.</p>
                            : <MeaningTrail items={trail} />
                    )}

                    {activeTab === 'offers-needs' && (
                        <>
                            {canManage && (
                                <div className="ep-manage-form-toggle">
                                    <button className="btn btn-accent" onClick={() => setShowNewOpening(v => !v)}>
                                        {showNewOpening ? 'Cancel' : `+ Post an Opening as ${alliance.name}`}
                                    </button>
                                </div>
                            )}
                            {openings.length === 0 && !showNewOpening ? (
                                <p className="empty-state">No offers or needs posted for this alliance yet.</p>
                            ) : (
                                <Openings
                                    services={openings}
                                    newServiceVisible={showNewOpening}
                                    onServiceAdded={fetchAlliance}
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

export default AlliancePage;
