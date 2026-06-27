import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Unions.css';

const pName = (p) => (typeof p === 'string' ? p : p.name);
const pHref = (p) => (typeof p === 'string' || !p.id ? '/user' : `/user?id=${p.id}`);

const UnionCard = ({ id, name, participants, description, projects, values, onJoin }) => {
  const navigate = useNavigate();
  const unionHref = id ? `/union?id=${id}` : '/union';

  return (
    <div className="union-card" onClick={() => navigate(unionHref)}>
      <div className="union-card-header">
        <div className="union-card-left">
          <h3>{name}</h3>
          <div className="union-card-participants">
            <span>👤 {participants.slice(0, 3).map((participant, index) => (
              <a key={index} href={pHref(participant)} onClick={(e) => e.stopPropagation()}>{pName(participant)}{index < Math.min(participants.length, 3) - 1 ? ', ' : ''}</a>
            ))}{participants.length > 3 && <>, <a href={unionHref} onClick={(e) => e.stopPropagation()}>{participants.length - 3} more...</a></>}</span>
          </div>
        </div>
        <div className="union-card-right">
          <button className="btn-orange" onClick={(e) => { e.stopPropagation(); onJoin(id); }}>Request to join</button>
        </div>
      </div>
      <div className="union-card-description-container">
        <p className="union-card-description">{description}</p>
      </div>
      <div className="union-card-project-link">
        {projects.slice(0, 3).map((project, index) => (
          <button key={index} className="btn-status" onClick={(e) => { e.stopPropagation(); navigate(`/project?name=${encodeURIComponent(project)}`); }}>{project}</button>
        ))}
        {projects.length > 3 && <a href="/projects" onClick={(e) => e.stopPropagation()}>{projects.length - 3} more...</a>}
      </div>
      <div className="union-card-values">
        {values.map((value, index) => (
          <span key={index}>#{value}</span>
        ))}
      </div>
    </div>
  );
};

export default UnionCard;
