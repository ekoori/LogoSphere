// EntityPage — /sphere, /alliance, /project. One page replaces the three,
// which were ~80% the same: banner up top, Meaning Trail + Openings + People
// in the main column, membership/links/charter in the aside. The per-kind
// differences (what the aside lists, role tiers, join prompt) are data here.
//
// Data: one detail request via the query layer (members, value cards and a
// sphere's alliance/project ids embedded). Activity (openings, trail) is only
// fetched for viewers allowed to see it. A logged-out visitor can view a
// sphere flagged public through the no-auth endpoint.
import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import PropTypes from 'prop-types';
import api from '../api';
import { useLogin } from '../App';
import { useEntity, usePublicSphere, useOpenings, useInvalidate, useEntityIndex, ID_KEY } from '../utils/queries';
import { usePermissions } from '../utils/usePermissions';
import CompactValueGraph from '../components/CompactValueGraph';
import EntityBanner from '../components/EntityBanner';
import Openings from '../components/Openings';
import MeaningTrail from '../components/MeaningTrail';
import TabSelector from '../components/TabSelector';
import MembersList from '../components/MembersList';
import GovernancePanel from '../components/GovernancePanel';
import Avatar from '../components/Avatar';
import { mapService } from '../utils/mappers';
import { fetchAggregateTrail } from '../utils/entityTrail';
import '../styles/EntityPage.css';
import '../styles/ValueCardChip.css';

const NOUN = { sphere: 'Sphere', alliance: 'Alliance', project: 'Project' };
const STATUS_META = {
    'Initiated':   { cls: 'status--initiated',   label: 'Initiated' },
    'In Progress': { cls: 'status--in-progress',  label: 'In Progress' },
    'Completed':   { cls: 'status--completed',    label: 'Completed' },
    'Paused':      { cls: 'status--paused',       label: 'Paused' },
};
// Role tiers shown in the aside, per kind: [role, label, css]
const TIERS = {
    sphere: [],
    alliance: [['admin', 'Lead', 'admin'], ['steward', 'Board members', 'steward'], ['member', 'Members', 'member']],
    project: [['manager', 'Manager', 'admin'], ['steward', 'Stewards', 'steward'], ['contributor', 'Contributors', 'steward'], ['observer', 'Observers', 'member']],
};

function RoleTier({ label, cls, people }) {
    if (!people.length) return null;
    return (
        <div className="ep-role-tier">
            <span className={`ep-role-label role--${cls}`}>{label}</span>
            <div className="ep-roster">
                {people.map((m) => (
                    <Link key={m.id} to={`/user?id=${m.id}`} className={`ep-member-pill ep-member-pill--${cls}`}>
                        <Avatar userId={m.id} name={m.name} size={22} />
                        <span className="ep-member-name">{m.name}</span>
                    </Link>
                ))}
            </div>
        </div>
    );
}

export default function EntityPage({ kind }) {
    const [params] = useSearchParams();
    const id = params.get('id');
    const legacyName = params.get('name');
    const { userId, authChecked } = useLogin();
    const { entityHref, sphereIdByName, allianceIdByName, projectIdByName } = useEntityIndex();
    const invalidate = useInvalidate();

    // Legacy ?name= links: resolve to an id through the cached index.
    const byName = { sphere: sphereIdByName, alliance: allianceIdByName, project: projectIdByName }[kind];
    const resolvedId = id || (legacyName ? byName[legacyName] : null);

    const anonymous = authChecked && !userId;
    const detail = useEntity(kind, resolvedId, { enabled: !!userId });
    const pub = usePublicSphere(resolvedId, { enabled: anonymous && kind === 'sphere' });
    const entity = anonymous ? pub.data : detail.data;
    const loading = !authChecked || (anonymous ? pub.isLoading : detail.isLoading) || (!id && legacyName && !resolvedId && !detail.isError);

    const perms = usePermissions(kind, entity);
    const canViewActivity = anonymous ? !!entity?.is_public : perms.canViewActivity;

    const openings = useOpenings({ enabled: !!userId && canViewActivity });
    const [trail, setTrail] = useState([]);
    const [activeTab, setActiveTab] = useState(params.get('tab') || 'meaning_trail');
    const [showNewOpening, setShowNewOpening] = useState(false);
    const [joining, setJoining] = useState(false);
    const [joinNote, setJoinNote] = useState(null);

    const eid = entity ? (entity[ID_KEY[kind]] || entity.id) : null;

    // Aggregate trail: the entity's own exchanges plus its alliances'/projects'.
    useEffect(() => {
        if (!entity || !userId || !canViewActivity) { setTrail([]); return undefined; }
        let alive = true;
        const own = [eid];
        let projectIds = [];
        if (kind === 'sphere') {
            own.push(...(entity.alliance_list || []).map((a) => a.id));
            projectIds = (entity.project_list || []).map((p) => p.id);
        } else if (kind === 'alliance') {
            projectIds = (entity.projects || []).map((n) => projectIdByName[n]).filter(Boolean);
        } else {
            projectIds = [eid];
        }
        fetchAggregateTrail({ ownEntityIds: own, projectIds }, userId)
            .then((rows) => { if (alive) setTrail(rows); })
            .catch(() => { if (alive) setTrail([]); });
        return () => { alive = false; };
    }, [entity, eid, kind, userId, canViewActivity, projectIdByName]);

    if (loading) return <div className="ep-loading">Loading…</div>;
    if (!entity) return (
        <div className="ep-page">
            <p className="ep-not-found">
                {anonymous && kind === 'sphere'
                    ? <>This sphere is private. <Link to="/login">Log in</Link> to see it.</>
                    : `${NOUN[kind]} not found.`}
            </p>
        </div>
    );

    // Openings shown on this page: posted in the sphere / by the entity / for its projects.
    const projectNames = new Set(kind === 'sphere' ? (entity.project_list || []).map((p) => p.name) : (entity.projects || []));
    const myOpenings = anonymous
        ? (entity.openings || []).map(mapService)
        : (openings.data || []).filter((s) =>
            (kind === 'sphere' && s.sphere_id === eid)
            || s.provider_id === eid
            || (kind !== 'sphere' && s.project_name && projectNames.has(s.project_name))
            || (kind === 'project' && s.project_name === entity.name)
        ).map(mapService);

    const members = entity.members || [];
    const isClosed = kind === 'project' && entity.phase === 'closed';
    const statusInfo = kind !== 'project' ? null
        : isClosed ? { cls: 'status--paused', label: 'Closed' }
            : (STATUS_META[entity.status] || { cls: 'status--in-progress', label: 'Ongoing' });
    const actingAs = {
        id: eid, name: entity.name,
        sphereId: kind === 'sphere' ? eid : entity.sphere_id,
        sphereName: kind === 'sphere' ? entity.name : entity.sphere_name,
        projectName: kind === 'project' ? entity.name : undefined,
    };

    const handleJoin = async () => {
        if (joining || !userId) return;
        setJoining(true);
        setJoinNote(null);
        try {
            const res = await api.post(`/api/${kind}s/${eid}/join`);
            if (res.data?.pending) setJoinNote({ ok: true, text: 'Request sent — a manager will approve it.' });
            await invalidate.entity(kind, eid);
        } catch (e) {
            setJoinNote({ ok: false, text: e.response?.data?.message || `Could not join this ${kind}.` });
        } finally {
            setJoining(false);
        }
    };

    const refresh = () => Promise.all([invalidate.entity(kind, eid), invalidate.openings()]);

    return (
        <div className={`ep-page ep-page--${kind}`}>
            <EntityBanner kind={kind} imageUrl={entity.has_image ? `/api/${kind}s/${eid}/image` : undefined}>
                <div className="ep-meta-row">
                    <span className="ep-eyebrow">{NOUN[kind]}</span>
                    {statusInfo && <span className={`ep-status-badge ${statusInfo.cls}`}>{statusInfo.label}</span>}
                    {kind === 'sphere' && entity.location && <span className="ep-location-chip">{entity.location}</span>}
                    {kind !== 'sphere' && entity.sphere_name && (
                        <Link to={entityHref('sphere', entity.sphere_name, entity.sphere_id)} className="ep-sphere-chip">{entity.sphere_name}</Link>
                    )}
                    {members.length > 0 && (
                        <span className="ep-location-chip">{members.length} member{members.length !== 1 ? 's' : ''}</span>
                    )}
                    {entity.is_public && kind === 'sphere' && <span className="ep-location-chip">Public</span>}
                    {perms.canManage && (
                        <Link to={`/${kind}-management?id=${eid}`} className="ep-status-badge status--in-progress" style={{ textDecoration: 'none' }}>
                            Manage {NOUN[kind]}
                        </Link>
                    )}
                </div>
                <h1 className="ep-title">{entity.name}</h1>
                {kind === 'project' && (entity.owner_alliance ? (
                    <p className="ep-lead-alliance">Led by <Link to={entityHref('alliance', entity.owner_alliance)} className="ep-alliance-link">{entity.owner_alliance}</Link></p>
                ) : entity.owner_name && (
                    <p className="ep-lead-alliance">by <Link to={entity.owner_id ? `/user?id=${entity.owner_id}` : '/user'} className="ep-alliance-link">{entity.owner_name}</Link></p>
                ))}
                <p className="ep-description">{entity.description}</p>
                {!perms.isMember && userId && (
                    <button className="btn btn-accent" onClick={handleJoin} disabled={joining} style={{ marginTop: '0.6rem' }}>
                        {joining ? 'Joining…' : `+ Join this ${NOUN[kind]}`}
                    </button>
                )}
                {joinNote && <p className={joinNote.ok ? 'ep-empty' : 'ep-not-found'} style={{ marginTop: '0.4rem' }}>{joinNote.text}</p>}
            </EntityBanner>

            {!canViewActivity ? (
                <p className="ep-empty" style={{ padding: '0 0.5rem' }}>
                    {userId
                        ? `Join this ${kind} to see its meaning trail, openings and people.`
                        : 'Log in and join this sphere to see its activity.'}
                </p>
            ) : (
                <div className="ep-layout">
                    <aside className="ep-aside">
                        {TIERS[kind].length > 0 && (
                            <div className="ep-aside-section">
                                <h4>{kind === 'alliance' ? 'Governance' : 'Contributors'}</h4>
                                {TIERS[kind].map(([role, label, cls]) => (
                                    <RoleTier key={role} label={label} cls={cls} people={members.filter((m) => m.role === role)} />
                                ))}
                                {members.length === 0 && <p className="ep-empty">No members yet.</p>}
                            </div>
                        )}

                        {kind === 'sphere' && (entity.alliance_list || []).length > 0 && (
                            <div className="ep-aside-section">
                                <h4>Alliances</h4>
                                <ul className="ep-project-list">
                                    {entity.alliance_list.map((a) => (
                                        <li key={a.id}><Link to={`/alliance?id=${a.id}`} className="ep-project-link">{a.name}<span className="ep-project-arrow">→</span></Link></li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        {kind === 'sphere' && (entity.project_list || []).length > 0 && (
                            <div className="ep-aside-section">
                                <h4>Projects</h4>
                                <ul className="ep-project-list">
                                    {entity.project_list.map((p) => (
                                        <li key={p.id}><Link to={`/project?id=${p.id}`} className="ep-project-link">{p.name}<span className="ep-project-arrow">→</span></Link></li>
                                    ))}
                                </ul>
                            </div>
                        )}
                        {kind === 'alliance' && (entity.projects || []).length > 0 && (
                            <div className="ep-aside-section">
                                <h4>Projects</h4>
                                <ul className="ep-project-list">
                                    {entity.projects.map((p, i) => (
                                        <li key={i}><Link to={entityHref('project', p)} className="ep-project-link">{p}<span className="ep-project-arrow">→</span></Link></li>
                                    ))}
                                </ul>
                            </div>
                        )}

                        <div className="ep-aside-section">
                            <h4>Charter</h4>
                            <CompactValueGraph
                                entityId={eid}
                                cards={entity.value_cards}
                                currentUserId={userId}
                                manageHref={perms.canManage ? `/${kind}-management?id=${eid}` : null}
                            />
                        </div>
                    </aside>

                    <main className="ep-main">
                        <TabSelector
                            tabs={[
                                { key: 'meaning_trail', label: 'Meaning Trail' },
                                { key: 'offers-needs', label: 'Offers & Needs' },
                                { key: 'members', label: `People (${members.length})` },
                                ...(userId ? [{ key: 'governance', label: 'Governance' }] : []),
                            ]}
                            active={activeTab}
                            onChange={setActiveTab}
                        />

                        {activeTab === 'governance' && (
                            <GovernancePanel kind={kind} entityId={eid} canManage={perms.canManage} />
                        )}

                        {activeTab === 'members' && (
                            <MembersList
                                kind={kind}
                                entityId={eid}
                                members={members}
                                pending={entity.pending_members || []}
                                canSetRoles={perms.canSetRoles}
                                currentUserId={userId}
                                onChanged={refresh}
                            />
                        )}

                        {activeTab === 'meaning_trail' && (
                            trail.length === 0
                                ? <p className="empty-state">No meaning trail recorded yet for this {kind}.</p>
                                : <MeaningTrail items={trail} />
                        )}

                        {activeTab === 'offers-needs' && (
                            <>
                                {isClosed && (
                                    <p className="ep-empty">This project is closed — it takes no new openings.</p>
                                )}
                                {perms.canManage && !isClosed && (
                                    <div className="ep-manage-form-toggle">
                                        <button className="btn btn-accent" onClick={() => setShowNewOpening((v) => !v)}>
                                            {showNewOpening ? 'Cancel' : `+ Post an Opening as ${entity.name}`}
                                        </button>
                                    </div>
                                )}
                                {myOpenings.length === 0 && !showNewOpening ? (
                                    <p className="empty-state">No offers or needs posted for this {kind} yet.</p>
                                ) : (
                                    <Openings
                                        services={myOpenings}
                                        newServiceVisible={showNewOpening}
                                        onServiceAdded={refresh}
                                        currentUserId={userId}
                                        actingAs={perms.canManage ? actingAs : null}
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

EntityPage.propTypes = { kind: PropTypes.oneOf(['sphere', 'alliance', 'project']).isRequired };
