// SphereManagement — admin-only console for a sphere.
// Access is restricted to the sphere's admin1; anyone else is turned away.
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
  { key: 'members',    label: 'Members' },
];

const SphereManagement = () => {
  const [params] = useSearchParams();
  const sphereId = params.get('id');
  const { userId } = useLogin();

  const [sphere, setSphere] = useState(null);
  const [loading, setLoading] = useState(true);
  const [nameEdit, setNameEdit] = useState(false);
  const [descriptionEdit, setDescriptionEdit] = useState(false);
  const [activeTab, setActiveTab] = useState('governance');
  const [joinPolicy, setJoinPolicy] = useState('open');
  const [savingPolicy, setSavingPolicy] = useState(false);
  const [imgVersion, setImgVersion] = useState(0);

  const fetchSphere = useCallback(async () => {
    if (!sphereId) { setLoading(false); return; }
    try {
      const r = await api.get('/api/spheres');
      const found = (r.data || []).find((s) => s.sphere_id === sphereId);
      setSphere(found || null);
    } catch (_) {
      setSphere(null);
    } finally {
      setLoading(false);
    }
  }, [sphereId]);

  useEffect(() => { fetchSphere(); }, [fetchSphere]);

  const handleImageUpload = async (file) => {
    const fd = new FormData();
    fd.append('image', file);
    await api.post(`/api/spheres/${sphereId}/image`, fd, { headers: { 'Content-Type': 'multipart/form-data' } });
    await fetchSphere();
    setImgVersion((v) => v + 1); // bust the cached banner so the new image shows
  };

  if (loading) return <div className="ep-loading">Loading…</div>;

  const isAdmin = !!userId && !!sphere && userId === sphere.admin1;

  if (!sphere) {
    return (
      <div className="ep-page">
        <p className="ep-not-found">Sphere not found.</p>
      </div>
    );
  }

  if (!isAdmin) {
    return (
      <div className="ep-page">
        <p className="ep-not-found">
          Only this sphere's admin can access sphere management.{' '}
          <Link to={`/sphere?id=${sphere.sphere_id}`}>Back to {sphere.name}</Link>
        </p>
      </div>
    );
  }

  const saveName = (e) => {
    e.preventDefault();
    setSphere((s) => ({ ...s, name: e.target.spherename.value }));
    setNameEdit(false);
  };

  const saveDescription = (e) => {
    e.preventDefault();
    setSphere((s) => ({ ...s, description: e.target.description.value }));
    setDescriptionEdit(false);
  };

  return (
    <>
    <div className="ep-page-banner">
      <EntityBanner kind="sphere" imageUrl={sphere.has_image ? `/api/spheres/${sphereId}/image?v=${imgVersion}` : undefined} onUpload={handleImageUpload}>
        <span className="ep-eyebrow">Sphere Management</span>
        <h1 className="ep-title">{sphere.name}</h1>
        {sphere.description && <p className="ep-description">{sphere.description}</p>}
      </EntityBanner>
    </div>
    <div className="container">
      <aside className="management-sidebar">
        <h2>Sphere Management</h2>
        <div>
          {!nameEdit ? (
            <h3 onClick={() => setNameEdit(true)} style={{ cursor: 'pointer' }}>{sphere.name || '—'}</h3>
          ) : (
            <form onSubmit={saveName}>
              <input type="text" name="spherename" defaultValue={sphere.name} autoFocus />
              <button type="submit" className="btn-orange">Save</button>
            </form>
          )}
        </div>
        <div>
          {!descriptionEdit ? (
            <p onClick={() => setDescriptionEdit(true)} style={{ cursor: 'pointer' }}>{sphere.description || 'Click to add description…'}</p>
          ) : (
            <form onSubmit={saveDescription}>
              <textarea name="description" defaultValue={sphere.description} rows={4} />
              <button type="submit" className="btn-orange">Save</button>
            </form>
          )}
        </div>
      </aside>
      <main>
        <TabSelector tabs={TABS} active={activeTab} onChange={setActiveTab} />

        <section className={`management-section tab-content ${activeTab === 'valuegraph' ? '' : 'hidden'}`}>
          <h3>Value Graph</h3>
          <p className="management-section-sub">
            The values this sphere holds itself to — what it cares about, why, and what drift looks like.
          </p>
          <EntityValueGraph entityId={sphere.sphere_id} canManage={isAdmin} entityNoun="sphere" />
        </section>

        <section className={`management-section tab-content ${activeTab === 'governance' ? '' : 'hidden'}`}>
          <h3>Governance Settings</h3>
          <form onSubmit={(e) => { e.preventDefault(); setSavingPolicy(true); setTimeout(() => setSavingPolicy(false), 800); }}>
            <div className="form-group">
              <label htmlFor="join-policy">Membership join policy</label>
              <select id="join-policy" value={joinPolicy} onChange={(e) => setJoinPolicy(e.target.value)}>
                <option value="open">Open — anyone can join directly</option>
                <option value="approval">Approval required — admin must approve</option>
              </select>
            </div>
            <button type="submit" className="btn-orange" disabled={savingPolicy}>
              {savingPolicy ? 'Saved ✓' : 'Save Changes'}
            </button>
          </form>
        </section>

        <section className={`management-section tab-content ${activeTab === 'members' ? '' : 'hidden'}`}>
          <h3>Members</h3>
          {(sphere.members || []).length > 0 ? (
            <ul className="member-list">
              {sphere.members.map((m) => (
                <li key={m.id}>
                  <Link to={`/user?id=${m.id}`}>{m.name}</Link>
                  {m.id === sphere.admin1 && <span className="pill pill-honey" style={{ marginLeft: '0.6em' }}>Admin</span>}
                </li>
              ))}
            </ul>
          ) : (
            <p style={{ color: 'var(--ink-faint)', fontStyle: 'italic', fontSize: '0.9rem' }}>No members yet.</p>
          )}
        </section>
      </main>
    </div>
    </>
  );
};

export default SphereManagement;
