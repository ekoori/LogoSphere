// ProjectManagement — manager-only console for a project.
// Access is restricted to a participant with role 'manager'; anyone else is
// turned away. Mirrors AllianceManagement/SphereManagement's shape.
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import '../styles/AllianceManagement.css';
import '../styles/EntityPage.css';
import api from '../api';
import { useLogin } from '../App';
import TabSelector from '../components/TabSelector';
import EntityValueGraph from '../components/EntityValueGraph';
import EntityBanner from '../components/EntityBanner';

const TABS = [
  { key: 'governance', label: 'Governance' },
  { key: 'valuegraph', label: 'Value Graph' },
  { key: 'members',    label: 'Contributors' },
];

const ProjectManagement = () => {
  const [params] = useSearchParams();
  const projectId = params.get('id');
  const { userId } = useLogin();

  const [project, setProject] = useState(null);
  const [loading, setLoading] = useState(true);
  const [nameEdit, setNameEdit] = useState(false);
  const [descriptionEdit, setDescriptionEdit] = useState(false);
  const [activeTab, setActiveTab] = useState('governance');
  const [joinPolicy, setJoinPolicy] = useState('open');
  const [savingPolicy, setSavingPolicy] = useState(false);
  const [imgVersion, setImgVersion] = useState(0);

  const fetchProject = useCallback(async () => {
    if (!projectId) { setLoading(false); return; }
    try {
      const r = await api.get('/api/projects');
      const found = (r.data || []).find((p) => p.project_id === projectId || p.id === projectId);
      setProject(found || null);
    } catch (_) {
      setProject(null);
    } finally {
      setLoading(false);
    }
  }, [projectId]);

  useEffect(() => { fetchProject(); }, [fetchProject]);

  if (loading) return <div className="ep-loading">Loading…</div>;

  const pid = project ? (project.project_id || project.id) : null;
  const isManager = !!userId && !!project
    && (project.members || []).some((m) => m.id === userId && m.role === 'manager');

  if (!project) {
    return (
      <div className="ep-page">
        <p className="ep-not-found">Project not found.</p>
      </div>
    );
  }

  if (!isManager) {
    return (
      <div className="ep-page">
        <p className="ep-not-found">
          Only this project's manager can access project management.{' '}
          <Link to={`/project?id=${pid}`}>Back to {project.name}</Link>
        </p>
      </div>
    );
  }

  const handleImageUpload = async (file) => {
    const fd = new FormData();
    fd.append('image', file);
    await api.post(`/api/projects/${pid}/image`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    await fetchProject();
    setImgVersion((v) => v + 1);
  };

  const saveName = (e) => {
    e.preventDefault();
    setProject((p) => ({ ...p, name: e.target.projectname.value }));
    setNameEdit(false);
  };

  const saveDescription = (e) => {
    e.preventDefault();
    setProject((p) => ({ ...p, description: e.target.description.value }));
    setDescriptionEdit(false);
  };

  return (
    <>
    <div className="ep-page-banner">
      <EntityBanner kind="project" imageUrl={project.has_image ? `/api/projects/${pid}/image?v=${imgVersion}` : undefined} onUpload={handleImageUpload}>
        <span className="ep-eyebrow">Project Management</span>
        <h1 className="ep-title">{project.name}</h1>
        {project.description && <p className="ep-description">{project.description}</p>}
      </EntityBanner>
    </div>
    <div className="container">
      <aside className="management-sidebar">
        <h2>Project Management</h2>
        <div>
          {!nameEdit ? (
            <h3 onClick={() => setNameEdit(true)} style={{ cursor: 'pointer' }}>{project.name || '—'}</h3>
          ) : (
            <form onSubmit={saveName}>
              <input type="text" name="projectname" defaultValue={project.name} autoFocus />
              <button type="submit" className="btn-orange">Save</button>
            </form>
          )}
        </div>
        <div>
          {!descriptionEdit ? (
            <p onClick={() => setDescriptionEdit(true)} style={{ cursor: 'pointer' }}>{project.description || 'Click to add description…'}</p>
          ) : (
            <form onSubmit={saveDescription}>
              <textarea name="description" defaultValue={project.description} rows={4} />
              <button type="submit" className="btn-orange">Save</button>
            </form>
          )}
        </div>
        {project.owner_alliance && (
          <p><strong>Alliance:</strong> <Link to={`/alliance?name=${encodeURIComponent(project.owner_alliance)}`}>{project.owner_alliance}</Link></p>
        )}
      </aside>
      <main>
        <TabSelector tabs={TABS} active={activeTab} onChange={setActiveTab} />

        <section className={`management-section tab-content ${activeTab === 'valuegraph' ? '' : 'hidden'}`}>
          <h3>Value Graph</h3>
          <p className="management-section-sub">
            The values this project holds itself to — what it cares about, why, and what drift looks like.
          </p>
          <EntityValueGraph entityId={pid} canManage={isManager} entityNoun="project" />
        </section>

        <section className={`management-section tab-content ${activeTab === 'governance' ? '' : 'hidden'}`}>
          <h3>Governance Settings</h3>
          <form onSubmit={(e) => { e.preventDefault(); setSavingPolicy(true); setTimeout(() => setSavingPolicy(false), 800); }}>
            <div className="form-group">
              <label htmlFor="join-policy">Participation join policy</label>
              <select id="join-policy" value={joinPolicy} onChange={(e) => setJoinPolicy(e.target.value)}>
                <option value="open">Open — anyone can join</option>
                <option value="approval">Manager approval required</option>
              </select>
            </div>
            <button type="submit" className="btn-orange" disabled={savingPolicy}>
              {savingPolicy ? 'Saved ✓' : 'Save Changes'}
            </button>
          </form>
        </section>

        <section className={`management-section tab-content ${activeTab === 'members' ? '' : 'hidden'}`}>
          <h3>Contributors</h3>
          {(project.members || []).length > 0 ? (
            <ul className="member-list">
              {project.members.map((m) => (
                <li key={m.id}>
                  <Link to={`/user?id=${m.id}`}>{m.name}</Link>
                  <span className="pill pill-honey" style={{ marginLeft: '0.6em' }}>{m.role}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ color: 'var(--ink-faint)', fontStyle: 'italic', fontSize: '0.9rem' }}>No contributors yet.</p>
          )}
        </section>
      </main>
    </div>
    </>
  );
};

export default ProjectManagement;
