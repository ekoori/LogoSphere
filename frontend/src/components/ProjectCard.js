import React from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Projects.css';

const pName = (p) => (typeof p === 'string' ? p : p.name);
const pHref = (p) => (typeof p === 'string' || !p.id ? '/user' : `/user?id=${p.id}`);

const ProjectCard = ({ id, name, owner, participants, description, transactions, statusButtons, values, shoutouts, onLike }) => {
  const navigate = useNavigate();
  const projectHref = id ? `/project?id=${id}` : '/project';
  return (
    <div className="project" onClick={() => navigate(projectHref)}>
      <div className="project-header">
        <div className="project-left">
          <h3>{name}</h3>
          <div className="project-owner">
            <span>🔗 <a href={`/union?name=${encodeURIComponent(owner)}`} onClick={(e) => e.stopPropagation()}>{owner}</a></span>
          </div>
          <div className="project-participants">
            <span>👤 {participants.slice(0, 3).map((participant, index) => (
              <a key={index} href={pHref(participant)} onClick={(e) => e.stopPropagation()}>{pName(participant)}{index < Math.min(participants.length, 3) - 1 ? ', ' : ''}</a>
            ))}{participants.length > 3 && <>, <a href={projectHref} onClick={(e) => e.stopPropagation()}>{participants.length - 3} more...</a></>}</span>
          </div>
        </div>
        <div className="project-right">
          <button className="like-btn" onClick={(e) => { e.stopPropagation(); onLike(id); }}>❤️ {participants.length}</button>
          <div className="time">1h ago</div>
        </div>
      </div>
      <div className="project-description-container">
        <p className="project-description">{description}</p>
      </div>
      <div className="project-transactions">
        {transactions.slice(0, 3).map((transaction, index) => (
          <div key={index} className="transaction">
            <div className="transaction-header">
              <h4>{transaction.title}</h4>
              <button className="transaction-status-btn">{transaction.status}</button>
            </div>
            <p>{transaction.details}</p>
            <div className="transaction-participants">
              <span>👤 <a href="/user" onClick={(e) => e.stopPropagation()}>{transaction.participant}</a></span>
            </div>
          </div>
        ))}
        {transactions.length > 3 && <a href="/project" onClick={(e) => e.stopPropagation()}>{transactions.length - 3} more...</a>}
      </div>
      <div className="project-status-buttons">
        {statusButtons.map((button, index) => (
          <button key={index} className={`btn-status-${button.status.toLowerCase()}`} onClick={(e) => e.stopPropagation()}>{button.label}</button>
        ))}
      </div>
      <div className="project-values">
        {values.map((value, index) => (
          <span key={index}>#{value}</span>
        ))}
      </div>
      <hr />
      <div className="project-shoutouts">
        {shoutouts.map((shoutout, index) => (
          <div key={index} className="shoutout">
            <p><strong>👤 <a href="/user" onClick={(e) => e.stopPropagation()}>{shoutout.author}</a></strong> {shoutout.text}</p>
            <div className="like-timestamp">
              <button className="like-btn" onClick={(e) => e.stopPropagation()}>❤️ {shoutout.likes}</button>
              <div className="time">{shoutout.time}</div>
            </div>
          </div>
        ))}
        <a href="/project" onClick={(e) => e.stopPropagation()}>More shoutouts...</a>
      </div>
    </div>
  );
};

export default ProjectCard;
