import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useEntityIndex } from '../utils/useEntityIndex';
import '../styles/Alliances.css';
import '../styles/ValueCardChip.css';
import ValueCardChip from './ValueCardChip';
import CardBanner from './CardBanner';

const pName = (p) => (typeof p === 'string' ? p : p.name);
const pHref = (p) => (typeof p === 'string' || !p.id ? '/user' : `/user?id=${p.id}`);

// Alliance leadership vocabulary: admin → Lead, steward → Board member.
const ROLE_LABEL = { admin: 'Lead', steward: 'Board member', member: 'Member', contributor: 'Contributor', manager: 'Manager' };

const AllianceCard = ({ id, name, sphere_id, sphere_name, participants, description, projects, values, valueCards = [], has_image = false, currentUserId, onJoin }) => {
  const navigate = useNavigate();
  const { entityHref } = useEntityIndex();
  const allianceHref = id ? `/alliance?id=${id}` : '/alliance';
  const manageHref = id ? `/alliance-management?id=${id}` : '/alliance-management';

  // participants is the members array: [{id, name, role}] or strings
  const memberEntry = Array.isArray(participants)
    ? participants.find((p) => typeof p === 'object' && p.id === currentUserId)
    : null;
  const isMember = !!memberEntry;
  const userRole = memberEntry?.role || null;
  const canManage = userRole === 'admin' || userRole === 'steward';

  const handleJoinClick = (e) => {
    e.stopPropagation();
    onJoin(id);
  };

  return (
    <div className="alliance-card" onClick={() => navigate(allianceHref)}>
      <CardBanner imageUrl={has_image && id ? `/api/alliances/${id}/image` : null} alt={name} />
      <div className="alliance-card-header">
        <div className="alliance-card-left">
          {sphere_name && (
            <div className="entity-card-breadcrumb">
              <a
                href={entityHref('sphere', sphere_name, sphere_id)}
                onClick={(e) => e.stopPropagation()}
              >
                {sphere_name}
              </a>
            </div>
          )}
          <h3>{name}</h3>
          <div className="alliance-card-participants">
            <span>👤 {participants.slice(0, 3).map((participant, index) => (
              <a key={index} href={pHref(participant)} onClick={(e) => e.stopPropagation()}>
                {pName(participant)}{index < Math.min(participants.length, 3) - 1 ? ', ' : ''}
              </a>
            ))}{participants.length > 3 && <>, <a href={allianceHref} onClick={(e) => e.stopPropagation()}>{participants.length - 3} more…</a></>}</span>
          </div>
        </div>
        <div className="alliance-card-right">
          {canManage ? (
            <Link
              to={manageHref}
              className="btn-orange"
              onClick={(e) => e.stopPropagation()}
            >
              Manage
            </Link>
          ) : isMember ? (
            <span className="uc-member-badge">
              {ROLE_LABEL[userRole] || 'Member'}
            </span>
          ) : (
            <button className="btn-orange" onClick={handleJoinClick}>
              Join
            </button>
          )}
        </div>
      </div>
      <div className="alliance-card-description-container">
        <p className="alliance-card-description">{description}</p>
      </div>
      <div className="alliance-card-project-link">
        {projects.slice(0, 3).map((project, index) => (
          <button key={index} className="btn-status" onClick={(e) => { e.stopPropagation(); navigate(entityHref('project', pName(project), typeof project === 'object' ? project.id : null)); }}>{pName(project)}</button>
        ))}
        {projects.length > 3 && <a href="/projects" onClick={(e) => e.stopPropagation()}>{projects.length - 3} more…</a>}
      </div>
      {(valueCards.length > 0 || values.length > 0) && (
        <div className="alliance-card-values">
          {valueCards.length > 0 ? (
            <div className="vc-chips-row">
              {valueCards.map((card, i) => (
                <ValueCardChip key={card.card_id || i} card={card} subjectLabel="We care about" currentUserId={currentUserId} />
              ))}
            </div>
          ) : (
            values.map((value, index) => (
              <span key={index}>#{value}</span>
            ))
          )}
        </div>
      )}
    </div>
  );
};

export default AllianceCard;
