import React from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useEntityIndex } from '../utils/useEntityIndex';
import '../styles/Projects.css';

const pName = (p) => (typeof p === 'string' ? p : p.name);
const pHref = (p) => (typeof p === 'string' || !p.id ? '/user' : `/user?id=${p.id}`);

const ROLE_LABEL = { manager: 'Manager', contributor: 'Contributor', observer: 'Observer' };

const ProjectCard = ({ id, name, sphere_id, sphere_name, owner_alliance, owner_name, owner_id, participants, description, values, currentUserId, onJoin, onLike }) => {
  const navigate = useNavigate();
  const { entityHref } = useEntityIndex();
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
          {sphere_name && (
            <div className="entity-card-breadcrumb">
              <a href={entityHref('sphere', sphere_name, sphere_id)} onClick={(e) => e.stopPropagation()}>
                {sphere_name}
              </a>
              {owner_alliance ? (
                // Run on behalf of an alliance → link to the alliance's page.
                <>
                  <span className="breadcrumb-pipe"> | </span>
                  <a href={entityHref('alliance', owner_alliance)} onClick={(e) => e.stopPropagation()}>
                    {owner_alliance}
                  </a>
                </>
              ) : owner_name && (
                // Otherwise it's a personal project → "by <person>".
                <>
                  <span className="breadcrumb-pipe"> | </span>
                  <span className="project-by">by{' '}
                    <a href={owner_id ? `/user?id=${owner_id}` : '/user'} onClick={(e) => e.stopPropagation()}>
                      {owner_name}
                    </a>
                  </span>
                </>
              )}
            </div>
          )}
          <h3>{name}</h3>
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
