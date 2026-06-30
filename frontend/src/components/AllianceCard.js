import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import '../styles/Alliances.css';

const pName = (p) => (typeof p === 'string' ? p : p.name);
const pHref = (p) => (typeof p === 'string' || !p.id ? '/user' : `/user?id=${p.id}`);

const ROLE_LABEL = { admin: 'Admin', steward: 'Steward', member: 'Member', contributor: 'Contributor', manager: 'Manager' };

const AllianceCard = ({ id, name, participants, description, projects, values, currentUserId, onJoin }) => {
  const navigate = useNavigate();
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
      <div className="alliance-card-header">
        <div className="alliance-card-left">
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
          <button key={index} className="btn-status" onClick={(e) => { e.stopPropagation(); navigate(`/project?name=${encodeURIComponent(project)}`); }}>{project}</button>
        ))}
        {projects.length > 3 && <a href="/projects" onClick={(e) => e.stopPropagation()}>{projects.length - 3} more…</a>}
      </div>
      <div className="alliance-card-values">
        {values.map((value, index) => (
          <span key={index}>#{value}</span>
        ))}
      </div>
    </div>
  );
};

export default AllianceCard;
