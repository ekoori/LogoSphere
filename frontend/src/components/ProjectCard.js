import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import '../styles/Projects.css';

const pName = (p) => (typeof p === 'string' ? p : p.name);
const pHref = (p) => (typeof p === 'string' || !p.id ? '/user' : `/user?id=${p.id}`);

const ROLE_LABEL = { manager: 'Manager', contributor: 'Contributor', observer: 'Observer' };

const ProjectCard = ({ id, name, owner, participants, description, values, currentUserId, onJoin, onLike }) => {
  const navigate = useNavigate();
  const projectHref = id ? `/project?id=${id}` : '/project';
  const manageHref = id ? `/project-management?id=${id}` : '/project-management';

  const memberEntry = Array.isArray(participants)
    ? participants.find((p) => typeof p === 'object' && p.id === currentUserId)
    : null;
  const isMember = !!memberEntry;
  const userRole = memberEntry?.role || null;
  const canManage = userRole === 'manager';

  const handleJoinClick = (e) => {
    e.stopPropagation();
    onJoin(id);
  };

  return (
    <div className="project" onClick={() => navigate(projectHref)}>
      <div className="project-header">
        <div className="project-left">
          <h3>{name}</h3>
          {owner && (
            <div className="project-owner">
              <span>🔗 <a href={`/alliance?name=${encodeURIComponent(owner)}`} onClick={(e) => e.stopPropagation()}>{owner}</a></span>
            </div>
          )}
          <div className="project-participants">
            <span>👤 {participants.slice(0, 3).map((p, i) => (
              <a key={i} href={pHref(p)} onClick={(e) => e.stopPropagation()}>
                {pName(p)}{i < Math.min(participants.length, 3) - 1 ? ', ' : ''}
              </a>
            ))}{participants.length > 3 && <>, <a href={projectHref} onClick={(e) => e.stopPropagation()}>{participants.length - 3} more…</a></>}</span>
          </div>
        </div>
        <div className="project-right">
          {canManage ? (
            <Link to={manageHref} className="like-btn" onClick={(e) => e.stopPropagation()} style={{ textDecoration: 'none' }}>
              Manage
            </Link>
          ) : isMember ? (
            <span className="uc-member-badge">{ROLE_LABEL[userRole] || 'Member'}</span>
          ) : (
            <button className="like-btn join-btn" onClick={handleJoinClick}>Join</button>
          )}
          <div className="time">{participants.length} member{participants.length !== 1 ? 's' : ''}</div>
        </div>
      </div>
      <div className="project-description-container">
        <p className="project-description">{description}</p>
      </div>
      <div className="project-values">
        {(values || []).map((value, index) => (
          <span key={index}>#{value}</span>
        ))}
      </div>
    </div>
  );
};

export default ProjectCard;
