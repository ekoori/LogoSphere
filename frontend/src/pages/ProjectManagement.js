import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import '../styles/ProjectManagement.css';
import api from '../api';

const ProjectManagement = () => {
  const [params] = useSearchParams();
  const projectId = params.get('id');

  const [project, setProject] = useState({ name: '', description: '', status: '', owner_alliance: '' });
  const [members, setMembers] = useState([]);

  useEffect(() => {
    if (!projectId) return;
    api.get('/api/projects').then((r) => {
      const found = (r.data || []).find((p) => p.project_id === projectId || p.id === projectId);
      if (found) {
        setProject({
          name: found.name || '',
          description: found.description || '',
          status: found.status || '',
          owner_alliance: found.owner_alliance || '',
        });
        setMembers(found.members || []);
      }
    }).catch(() => {});
  }, [projectId]);

  const ROLE_LABEL = { manager: 'Manager', contributor: 'Contributor', observer: 'Observer' };

  return (
    <div className="container">
      <aside className="project-sidebar">
        <h2>{project.name || 'Project Management'}</h2>
        {project.owner_alliance && (
          <p><strong>Alliance:</strong> <a href={`/alliance?name=${encodeURIComponent(project.owner_alliance)}`}>{project.owner_alliance}</a></p>
        )}
        {project.status && (
          <p><strong>Status:</strong> <span className={`status ${(project.status || '').replace(' ', '-').toLowerCase()}`}>{project.status}</span></p>
        )}
      </aside>
      <main>
        <div className="project-section">
          <div className="project-description">
            <h3>Description</h3>
            <p>{project.description || '—'}</p>
          </div>

          <div className="project-description" style={{ marginTop: '2em' }}>
            <h3>Contributors</h3>
            {members.length === 0 ? (
              <p style={{ color: 'var(--ink-faint)', fontStyle: 'italic' }}>No contributors yet.</p>
            ) : (
              <ul style={{ listStyle: 'none', padding: 0, display: 'flex', flexDirection: 'column', gap: '0.5rem' }}>
                {members.map((m) => (
                  <li key={m.id} style={{ display: 'flex', alignItems: 'center', gap: '0.75rem' }}>
                    <a href={`/user?id=${m.id}`} style={{ fontWeight: 500 }}>{m.name}</a>
                    <span style={{
                      fontSize: '0.68rem', fontFamily: 'ui-monospace, monospace', fontWeight: 700,
                      letterSpacing: '0.1em', textTransform: 'uppercase',
                      padding: '0.2em 0.6em', borderRadius: '4px',
                      border: '1px solid var(--border-soft)', color: 'var(--ink-faint)'
                    }}>
                      {ROLE_LABEL[m.role] || m.role}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </div>

          <div className="project-description" style={{ marginTop: '2em' }}>
            <h3>Governance</h3>
            <form onSubmit={(e) => e.preventDefault()}>
              <div className="form-group">
                <label htmlFor="join-policy">Participation join policy</label>
                <select id="join-policy">
                  <option value="open">Open — anyone can join</option>
                  <option value="approval">Manager approval required</option>
                </select>
              </div>
              <button type="submit" className="btn-orange">Save Changes</button>
            </form>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ProjectManagement;
