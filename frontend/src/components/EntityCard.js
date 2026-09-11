// EntityCard — the listing card for a sphere, alliance or project. One
// component replaces SphereCard / AllianceCard / ProjectCard, which were
// copy-pasted apart from the breadcrumb and the join vocabulary.
//
// The title is the card's link (the card itself is not a click target), so
// nested links and buttons don't need stopPropagation and keyboard users can
// reach it. Value cards come embedded in the list payload.
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import PropTypes from 'prop-types';
import ValueCardChip from './ValueCardChip';
import CardBanner from './CardBanner';
import { useEntityIndex, KIND_PATH, ID_KEY } from '../utils/queries';
import { useLogin } from '../App';
import '../styles/EntityCard.css';
import '../styles/ValueCardChip.css';

const MANAGE_ROLES = { sphere: ['admin'], alliance: ['admin', 'steward'], project: ['manager', 'steward'] };
const ROLE_LABEL = {
    sphere: { admin: 'Admin', member: 'Member' },
    alliance: { admin: 'Lead', steward: 'Board member', member: 'Member' },
    project: { manager: 'Manager', steward: 'Steward', contributor: 'Contributor' },
};
const NOUN = { sphere: 'Sphere', alliance: 'Alliance', project: 'Project' };

const pName = (p) => (typeof p === 'string' ? p : p.name);
const pHref = (p) => (typeof p === 'string' || !p.id ? '/user' : `/user?id=${p.id}`);

export default function EntityCard({ kind, entity, onJoin }) {
    const { userId, isPlatformAdmin } = useLogin();
    const { entityHref } = useEntityIndex();
    const [joining, setJoining] = useState(false);
    const [joinNote, setJoinNote] = useState(null);

    const id = entity[ID_KEY[kind]] || entity.id;
    const href = `/${kind}?id=${id}`;
    const manageHref = `/${kind}-management?id=${id}`;
    const members = entity.members || [];
    const me = userId ? members.find((m) => String(m.id) === String(userId)) : null;
    const canManage = isPlatformAdmin || (me && MANAGE_ROLES[kind].includes(me.role));
    const isPending = entity.pending_for_me;
    const valueCards = entity.value_cards || [];
    const values = entity.values || [];

    const handleJoin = async () => {
        if (joining || !onJoin) return;
        setJoining(true);
        setJoinNote(null);
        try {
            const res = await onJoin(id);
            if (res?.pending) setJoinNote({ ok: true, text: 'Request sent — awaiting approval' });
        } catch (e) {
            setJoinNote({ ok: false, text: e.response?.data?.message || `Could not join this ${kind}.` });
        } finally {
            setJoining(false);
        }
    };

    // Breadcrumb: the sphere an alliance/project lives in, plus who runs a project.
    const breadcrumb = kind !== 'sphere' && entity.sphere_name ? (
        <div className="entity-card-meta entity-card-breadcrumb">
            <Link to={entityHref('sphere', entity.sphere_name, entity.sphere_id)}>{entity.sphere_name}</Link>
            {kind === 'project' && entity.owner_alliance && (
                <> <span className="breadcrumb-pipe">|</span> <Link to={entityHref('alliance', entity.owner_alliance)}>{entity.owner_alliance}</Link></>
            )}
            {kind === 'project' && !entity.owner_alliance && entity.owner_name && (
                <> <span className="breadcrumb-pipe">|</span> by <Link to={entity.owner_id ? `/user?id=${entity.owner_id}` : '/user'}>{entity.owner_name}</Link></>
            )}
        </div>
    ) : null;

    // Sphere cards list their alliances; sphere + alliance cards list projects.
    const alliances = kind === 'sphere' ? (entity.alliances || []) : [];
    const projects = kind !== 'project' ? (entity.projects || []) : [];

    return (
        <article className={`entity-card entity-card--${kind}`}>
            <CardBanner imageUrl={entity.has_image ? `/api/${KIND_PATH[kind]}/${id}/image` : null} alt={entity.name} />
            <div className="entity-card-header">
                <div className="entity-card-left">
                    {breadcrumb}
                    <h3><Link to={href} className="entity-card-title-link">{entity.name}</Link></h3>
                    {alliances.length > 0 && (
                        <div className="entity-card-meta">
                            🔗 {alliances.map((a, i) => (
                                <React.Fragment key={i}>
                                    <Link to={entityHref('alliance', pName(a), typeof a === 'object' ? a.id : null)}>{pName(a)}</Link>
                                    {i < alliances.length - 1 ? ', ' : ''}
                                </React.Fragment>
                            ))}
                        </div>
                    )}
                    <div className="entity-card-meta">
                        👤 {members.slice(0, 3).map((p, i) => (
                            <React.Fragment key={i}>
                                <Link to={pHref(p)}>{pName(p)}</Link>{i < Math.min(members.length, 3) - 1 ? ', ' : ''}
                            </React.Fragment>
                        ))}
                        {members.length > 3 && <>, <Link to={href}>{members.length - 3} more…</Link></>}
                        {members.length === 0 && <span>No members yet</span>}
                    </div>
                </div>
                <div className="entity-card-right">
                    {canManage ? (
                        <Link to={manageHref} className="btn-orange">Manage</Link>
                    ) : me ? (
                        <span className="uc-member-badge">{ROLE_LABEL[kind][me.role] || 'Member'}</span>
                    ) : isPending ? (
                        <span className="entity-card-pending">Request pending</span>
                    ) : userId && onJoin ? (
                        <button className="btn-orange" onClick={handleJoin} disabled={joining}>
                            {joining ? 'Joining…' : `Join ${NOUN[kind]}`}
                        </button>
                    ) : null}
                    <span className="entity-card-count">{members.length} member{members.length !== 1 ? 's' : ''}</span>
                    {joinNote && <span className={joinNote.ok ? 'entity-card-pending' : 'entity-card-error'}>{joinNote.text}</span>}
                </div>
            </div>

            <div className="entity-card-body">
                <p className="entity-card-description">{entity.description}</p>
            </div>

            {projects.length > 0 && (
                <div className="entity-card-links">
                    {projects.slice(0, 3).map((p, i) => (
                        <Link key={i} className="btn-status" to={entityHref('project', pName(p), typeof p === 'object' ? p.id : null)}>{pName(p)}</Link>
                    ))}
                    {projects.length > 3 && <Link to="/projects">{projects.length - 3} more…</Link>}
                </div>
            )}

            {(valueCards.length > 0 || values.length > 0) && (
                <div className="entity-card-values">
                    {valueCards.length > 0 ? (
                        <div className="vc-chips-row">
                            {valueCards.map((card, i) => (
                                <ValueCardChip key={card.card_id || i} card={card} subjectLabel="We care about" currentUserId={userId} />
                            ))}
                        </div>
                    ) : (
                        values.map((v, i) => <span key={i}>#{v}</span>)
                    )}
                </div>
            )}
        </article>
    );
}

EntityCard.propTypes = {
    kind: PropTypes.oneOf(['sphere', 'alliance', 'project']).isRequired,
    entity: PropTypes.object.isRequired,
    onJoin: PropTypes.func,
};
