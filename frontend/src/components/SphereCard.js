import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useEntityIndex } from '../utils/useEntityIndex';
import '../styles/Spheres.css';
import '../styles/ValueCardChip.css';
import ValueCardChip from './ValueCardChip';

// participants may be plain names (strings) or {id, name} pairs.
const pName = (p) => (typeof p === 'string' ? p : p.name);
const pHref = (p) => (typeof p === 'string' || !p.id ? '/user' : `/user?id=${p.id}`);

const SphereCard = ({ id, name, alliances, participants, description, projects, values, valueCards = [], isMember = false, currentUserId, onJoin }) => {
  const navigate = useNavigate();
  const { entityHref } = useEntityIndex();
  const [joining, setJoining] = useState(false);
  const sphereHref = id ? `/sphere?id=${id}` : '/sphere';

  const handleJoin = async (e) => {
    e.stopPropagation();
    if (joining || isMember || !onJoin) return;
    setJoining(true);
    try {
      await onJoin(id);
    } finally {
      setJoining(false);
    }
  };

  return (
    <div className="sphere-card" onClick={() => navigate(sphereHref)}>
      <div className="sphere-card-header">
        <div className="sphere-card-left">
          <h3>{name}</h3>
          <div className="sphere-card-participants">
            <span>🔗 {alliances.map((alliance, index) => (
              <a key={index} href={entityHref('alliance', typeof alliance === 'string' ? alliance : alliance.name, typeof alliance === 'object' ? alliance.id : null)} onClick={(e) => e.stopPropagation()}>{typeof alliance === 'string' ? alliance : alliance.name}{index < alliances.length - 1 ? ', ' : ''}</a>
            ))}</span>
          </div>
          <div className="sphere-card-participants">
            <span>👤 {participants.slice(0, 3).map((participant, index) => (
              <a key={index} href={pHref(participant)} onClick={(e) => e.stopPropagation()}>{pName(participant)}{index < Math.min(participants.length, 3) - 1 ? ', ' : ''}</a>
            ))}{participants.length > 3 && <>, <a href={sphereHref} onClick={(e) => e.stopPropagation()}>{participants.length - 3} more...</a></>}</span>
          </div>
        </div>
        <div className="sphere-card-right">
          {isMember ? (
            <span className="sphere-card-joined">✓ Joined</span>
          ) : currentUserId ? (
            <button className="btn-orange" onClick={handleJoin} disabled={joining}>
              {joining ? 'Joining…' : 'Join Sphere'}
            </button>
          ) : null}
        </div>
      </div>
      <div className="sphere-card-description-container">
        <p className="sphere-card-description">{description}</p>
      </div>
      <div className="sphere-card-project-link">
        {projects.slice(0, 3).map((project, index) => (
          <button key={index} className="btn-status" onClick={(e) => { e.stopPropagation(); navigate(entityHref('project', typeof project === 'string' ? project : project.name, typeof project === 'object' ? project.id : null)); }}>{typeof project === 'string' ? project : project.name}</button>
        ))}
        {projects.length > 3 && <a href="/projects" onClick={(e) => e.stopPropagation()}>{projects.length - 3} more...</a>}
      </div>
      {(valueCards.length > 0 || values.length > 0) && (
        <div className="sphere-card-values">
          {valueCards.length > 0 ? (
            <div className="vc-chips-row">
              {valueCards.map((card, i) => (
                <ValueCardChip key={card.card_id || i} card={card} subjectLabel="We care about" />
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

export default SphereCard;
