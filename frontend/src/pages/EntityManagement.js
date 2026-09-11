// EntityManagement — /sphere-management, /alliance-management,
// /project-management. One console replaces the three. Every control here
// persists: name and description (PATCH), join policy (PATCH), and for
// spheres the sandbox/public governance flags. The old voting / receipt-
// verification selects that only pretended to save are gone until the
// features exist.
import React, { useEffect, useState } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import PropTypes from 'prop-types';
import api from '../api';
import { useLogin } from '../App';
import { useEntity, useInvalidate, KIND_PATH, ID_KEY } from '../utils/queries';
import { usePermissions } from '../utils/usePermissions';
import TabSelector from '../components/TabSelector';
import EntityValueGraph from '../components/EntityValueGraph';
import EntityBanner from '../components/EntityBanner';
import MembersList from '../components/MembersList';
import '../styles/AllianceManagement.css';
import '../styles/EntityPage.css';

const NOUN = { sphere: 'Sphere', alliance: 'Alliance', project: 'Project' };
const MANAGER_WORD = { sphere: 'an admin', alliance: 'a Lead or Board member', project: 'a manager' };
const PEOPLE_TAB = { sphere: 'Members', alliance: 'Members', project: 'Contributors' };

export default function EntityManagement({ kind }) {
    const [params] = useSearchParams();
    const id = params.get('id');
    const { userId, isPlatformAdmin } = useLogin();
    const invalidate = useInvalidate();
    const { data: entity, isLoading } = useEntity(kind, id);
    const perms = usePermissions(kind, entity);

    const [activeTab, setActiveTab] = useState('governance');
    const [name, setName] = useState('');
    const [description, setDescription] = useState('');
    const [joinPolicy, setJoinPolicy] = useState('open');
    const [isSandbox, setIsSandbox] = useState(false);
    const [isPublic, setIsPublic] = useState(false);
    const [saving, setSaving] = useState(false);
    const [note, setNote] = useState(null);
    const [imgVersion, setImgVersion] = useState(0);

    // Seed the form from the entity whenever it (re)loads.
    useEffect(() => {
        if (!entity) return;
        setName(entity.name || '');
        setDescription(entity.description || '');
        setJoinPolicy(entity.join_policy || 'open');
        setIsSandbox(!!entity.is_sandbox);
        setIsPublic(!!entity.is_public);
    }, [entity]);

    if (isLoading) return <div className="ep-loading">Loading…</div>;
    if (!entity) return <div className="ep-page"><p className="ep-not-found">{NOUN[kind]} not found.</p></div>;

    const eid = entity[ID_KEY[kind]] || entity.id;
    if (!perms.canManage) {
        return (
            <div className="ep-page">
                <p className="ep-not-found">
                    Only {MANAGER_WORD[kind]} can manage this {kind}.{' '}
                    <Link to={`/${kind}?id=${eid}`}>Back to {entity.name}</Link>
                </p>
            </div>
        );
    }

    const path = KIND_PATH[kind];

    const saveGovernance = async (e) => {
        e.preventDefault();
        setSaving(true);
        setNote(null);
        try {
            const body = {};
            if (name.trim() !== entity.name) body.name = name.trim();
            if ((description || '').trim() !== (entity.description || '')) body.description = description.trim();
            if (joinPolicy !== (entity.join_policy || 'open')) body.join_policy = joinPolicy;
            if (Object.keys(body).length) await api.patch(`/api/${path}/${eid}`, body);
            if (kind === 'sphere') {
                const gov = { is_public: isPublic };
                if (isPlatformAdmin) gov.is_sandbox = isSandbox;
                await api.post(`/api/spheres/${eid}/governance`, gov);
            }
            await invalidate.entity(kind, eid);
            setNote({ ok: true, text: 'Saved.' });
        } catch (err) {
            setNote({ ok: false, text: err.response?.data?.message || 'Could not save changes.' });
        } finally {
            setSaving(false);
        }
    };

    const handleImageUpload = async (file) => {
        const fd = new FormData();
        fd.append('image', file);
        await api.post(`/api/${path}/${eid}/image`, fd);
        await invalidate.entity(kind, eid);
        setImgVersion((v) => v + 1);
    };

    const tabs = [
        { key: 'governance', label: 'Governance' },
        { key: 'valuegraph', label: 'Value Graph' },
        { key: 'members', label: PEOPLE_TAB[kind] },
    ];

    return (
        <>
        <div className="ep-page-banner">
            <EntityBanner kind={kind} imageUrl={entity.has_image ? `/api/${path}/${eid}/image?v=${imgVersion}` : undefined} onUpload={handleImageUpload}>
                <span className="ep-eyebrow">{NOUN[kind]} Management</span>
                <h1 className="ep-title">{entity.name}</h1>
                {entity.description && <p className="ep-description">{entity.description}</p>}
            </EntityBanner>
        </div>
        <div className="container">
            <aside className="management-sidebar">
                <h2>{NOUN[kind]} Management</h2>
                <p><Link to={`/${kind}?id=${eid}`}>← Back to {entity.name}</Link></p>
                {kind !== 'sphere' && entity.sphere_name && (
                    <p><strong>Sphere:</strong> <Link to={`/sphere?id=${entity.sphere_id}`}>{entity.sphere_name}</Link></p>
                )}
                {kind === 'project' && entity.owner_alliance && (
                    <p><strong>Alliance:</strong> {entity.owner_alliance}</p>
                )}
            </aside>
            <main>
                <TabSelector tabs={tabs} active={activeTab} onChange={setActiveTab} />

                <section className={`management-section tab-content ${activeTab === 'governance' ? '' : 'hidden'}`}>
                    <h3>Governance Settings</h3>
                    <form onSubmit={saveGovernance}>
                        <div className="form-group">
                            <label htmlFor="ent-name">Name</label>
                            <input id="ent-name" type="text" value={name} onChange={(e) => setName(e.target.value)} required />
                        </div>
                        <div className="form-group">
                            <label htmlFor="ent-description">Description</label>
                            <textarea id="ent-description" rows={4} value={description} onChange={(e) => setDescription(e.target.value)} />
                        </div>
                        <div className="form-group">
                            <label htmlFor="join-policy">Membership join policy</label>
                            <select id="join-policy" value={joinPolicy} onChange={(e) => setJoinPolicy(e.target.value)}>
                                <option value="open">Open — anyone can join directly</option>
                                <option value="approval">Approval required — {MANAGER_WORD[kind]} must approve</option>
                            </select>
                        </div>

                        {kind === 'sphere' && (
                            <>
                                <div className="form-group management-toggle">
                                    <label>
                                        <input type="checkbox" checked={isPublic} onChange={(e) => setIsPublic(e.target.checked)} />
                                        {' '}Public activity
                                    </label>
                                    <p className="management-section-sub">
                                        When on, anyone — even visitors without an account — can see this sphere's
                                        projects, alliances and openings.
                                    </p>
                                </div>
                                <div className="form-group management-toggle">
                                    <label style={{ opacity: isPlatformAdmin ? 1 : 0.55 }}>
                                        <input type="checkbox" checked={isSandbox} disabled={!isPlatformAdmin} onChange={(e) => setIsSandbox(e.target.checked)} />
                                        {' '}Sandbox sphere
                                    </label>
                                    <p className="management-section-sub">
                                        Every new member who registers is automatically enrolled into this sphere.
                                        {!isPlatformAdmin && ' Only a platform administrator can change this.'}
                                    </p>
                                </div>
                            </>
                        )}

                        {note && <p className={note.ok ? 'xc-edit-ok' : 'xc-edit-err'}>{note.text}</p>}
                        <button type="submit" className="btn-orange" disabled={saving}>{saving ? 'Saving…' : 'Save Changes'}</button>
                    </form>
                </section>

                <section className={`management-section tab-content ${activeTab === 'valuegraph' ? '' : 'hidden'}`}>
                    <h3>Value Graph</h3>
                    <p className="management-section-sub">
                        The values this {kind} holds itself to — what it cares about, why, and what drift looks like.
                    </p>
                    <EntityValueGraph entityId={eid} canManage={perms.canManage} entityNoun={kind} />
                </section>

                <section className={`management-section tab-content ${activeTab === 'members' ? '' : 'hidden'}`}>
                    <h3>{PEOPLE_TAB[kind]}</h3>
                    <MembersList
                        kind={kind}
                        entityId={eid}
                        members={entity.members || []}
                        pending={entity.pending_members || []}
                        canSetRoles={perms.canSetRoles}
                        currentUserId={userId}
                        onChanged={() => invalidate.entity(kind, eid)}
                    />
                </section>
            </main>
        </div>
        </>
    );
}

EntityManagement.propTypes = { kind: PropTypes.oneOf(['sphere', 'alliance', 'project']).isRequired };
