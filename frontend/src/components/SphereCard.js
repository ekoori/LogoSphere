import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Spheres.css';

// participants may be plain names (strings) or {id, name} pairs.
const pName = (p) => (typeof p === 'string' ? p : p.name);
const pHref = (p) => (typeof p === 'string' || !p.id ? '/user' : `/user?id=${p.id}`);

const SphereCard = ({ id, name, unions, participants, description, projects, values, onJoin }) => {
  const navigate = useNavigate();
  const sphereHref = id ? `/sphere?id=${id}` : '/sphere';

  return (
    <div className="sphere-card" onClick={() => navigate(sphereHref)}>
      <div className="sphere-card-header">
        <div className="sphere-card-left">
          <h3>{name}</h3>
          <div className="sphere-card-participants">
            <span>🔗 {unions.map((union, index) => (
              <a key={index} href={`/union?name=${encodeURIComponent(union)}`} onClick={(e) => e.stopPropagation()}>{union}{index < unions.length - 1 ? ', ' : ''}</a>
            ))}</span>
          </div>
          <div className="sphere-card-participants">
            <span>👤 {participants.slice(0, 3).map((participant, index) => (
              <a key={index} href={pHref(participant)} onClick={(e) => e.stopPropagation()}>{pName(participant)}{index < Math.min(participants.length, 3) - 1 ? ', ' : ''}</a>
            ))}{participants.length > 3 && <>, <a href={sphereHref} onClick={(e) => e.stopPropagation()}>{participants.length - 3} more...</a></>}</span>
          </div>
        </div>
        <div className="sphere-card-right">
          <button className="btn-orange" onClick={(e) => { e.stopPropagation(); onJoin(id); }}>Join Sphere</button>
        </div>
      </div>
      <div className="sphere-card-description-container">
        <p className="sphere-card-description">{description}</p>
      </div>
      <div className="sphere-card-project-link">
        {projects.slice(0, 3).map((project, index) => (
          <button key={index} className="btn-status" onClick={(e) => { e.stopPropagation(); navigate(`/project?name=${encodeURIComponent(project)}`); }}>{project}</button>
        ))}
        {projects.length > 3 && <a href="/projects" onClick={(e) => e.stopPropagation()}>{projects.length - 3} more...</a>}
      </div>
      <div className="sphere-card-values">
        {values.map((value, index) => (
          <span key={index}>#{value}</span>
        ))}
      </div>
    </div>
  );
};

export default SphereCard;
