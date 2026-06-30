import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import '../styles/AllianceManagement.css';
import api from '../api';

const AllianceManagement = () => {
  const [params] = useSearchParams();
  const allianceId = params.get('id');

  const [alliance, setAlliance] = useState({ name: '', description: '' });
  const [nameEdit, setNameEdit] = useState(false);
  const [descriptionEdit, setDescriptionEdit] = useState(false);
  const [activeTab, setActiveTab] = useState('delegation');
  const [joinPolicy, setJoinPolicy] = useState('open');
  const [savingPolicy, setSavingPolicy] = useState(false);

  useEffect(() => {
    if (!allianceId) return;
    api.get('/api/alliances').then((r) => {
      const found = (r.data || []).find((a) => a.alliance_id === allianceId || a.id === allianceId);
      if (found) {
        setAlliance({ name: found.name, description: found.description || '' });
      }
    }).catch(() => {});
  }, [allianceId]);

  const saveName = (e) => {
    e.preventDefault();
    setAlliance((a) => ({ ...a, name: e.target.alliancename.value }));
    setNameEdit(false);
  };

  const saveDescription = (e) => {
    e.preventDefault();
    setAlliance((a) => ({ ...a, description: e.target.description.value }));
    setDescriptionEdit(false);
  };

  return (
    <div className="container">
      <aside className="management-sidebar">
        <h2>Alliance Management</h2>
        <div>
          {!nameEdit ? (
            <h3 id="alliance-name-display" onClick={() => setNameEdit(true)} style={{ cursor: 'pointer' }}>{alliance.name || '—'}</h3>
          ) : (
            <form onSubmit={saveName}>
              <input type="text" name="alliancename" defaultValue={alliance.name} autoFocus />
              <button type="submit" className="btn-orange">Save</button>
            </form>
          )}
        </div>
        <div>
          {!descriptionEdit ? (
            <p onClick={() => setDescriptionEdit(true)} style={{ cursor: 'pointer' }}>{alliance.description || 'Click to add description…'}</p>
          ) : (
            <form onSubmit={saveDescription}>
              <textarea name="description" defaultValue={alliance.description} rows={4} />
              <button type="submit" className="btn-orange">Save</button>
            </form>
          )}
        </div>
      </aside>
      <main>
        <div className="tab-selector">
          <button className={`btn-selector ${activeTab === 'delegation' ? 'active' : ''}`} onClick={() => setActiveTab('delegation')}>Governance</button>
          <button className={`btn-selector ${activeTab === 'voting' ? 'active' : ''}`} onClick={() => setActiveTab('voting')}>Voting</button>
          <button className={`btn-selector ${activeTab === 'projects' ? 'active' : ''}`} onClick={() => setActiveTab('projects')}>Projects</button>
          <button className={`btn-selector ${activeTab === 'members' ? 'active' : ''}`} onClick={() => setActiveTab('members')}>Members</button>
        </div>

        <section className={`management-section tab-content ${activeTab === 'delegation' ? '' : 'hidden'}`}>
          <h3>Governance Settings</h3>
          <form onSubmit={(e) => { e.preventDefault(); setSavingPolicy(true); setTimeout(() => setSavingPolicy(false), 800); }}>
            <div className="form-group">
              <label htmlFor="join-policy">Membership join policy</label>
              <select id="join-policy" value={joinPolicy} onChange={(e) => setJoinPolicy(e.target.value)}>
                <option value="open">Open — anyone can join directly</option>
                <option value="approval">Approval required — admin/steward must approve</option>
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="project-management">Project management performed by</label>
              <select id="project-management" name="project-management">
                <option value="single-pm">A single PM</option>
                <option value="board-members">Board members</option>
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="receipting">Receipts verified by</label>
              <select id="receipting" name="receipting">
                <option value="lead">Lead</option>
                <option value="board-members">Board members</option>
                <option value="any-member">Any member</option>
              </select>
            </div>
            <button type="submit" className="btn-orange" disabled={savingPolicy}>
              {savingPolicy ? 'Saved ✓' : 'Save Changes'}
            </button>
          </form>
        </section>

        <section className={`management-section tab-content ${activeTab === 'voting' ? '' : 'hidden'}`}>
          <h3>Voting</h3>
          <form onSubmit={(e) => e.preventDefault()}>
            <div className="form-group">
              <label htmlFor="voting">Decisions made by</label>
              <select id="voting" name="voting">
                <option value="majority">More than 50% majority</option>
                <option value="twothirds">2/3 supermajority</option>
                <option value="authocracy">Steward discretion</option>
                <option value="board">Board vote</option>
              </select>
            </div>
            <div className="form-group">
              <label>Vote on:</label>
              <div className="checkbox-group">
                <input type="checkbox" id="vote-new-member" name="vote-new-member" />
                <label htmlFor="vote-new-member">Accepting new member</label>
              </div>
              <div className="checkbox-group">
                <input type="checkbox" id="vote-board-members" name="vote-board-members" />
                <label htmlFor="vote-board-members">Board members</label>
              </div>
              <div className="checkbox-group">
                <input type="checkbox" id="vote-policy" name="vote-policy" />
                <label htmlFor="vote-policy">Policy acceptance</label>
              </div>
            </div>
            <button type="submit" className="btn-orange">Save Changes</button>
          </form>
        </section>

        <section className={`management-section tab-content ${activeTab === 'projects' ? '' : 'hidden'}`}>
          <h3>Manage Projects</h3>
          <p style={{ color: 'var(--ink-faint)', fontStyle: 'italic', fontSize: '0.9rem' }}>
            Project creation and assignment is managed from the Projects page.
          </p>
        </section>

        <section className={`management-section tab-content ${activeTab === 'members' ? '' : 'hidden'}`}>
          <h3>Manage Members</h3>
          <p style={{ color: 'var(--ink-faint)', fontStyle: 'italic', fontSize: '0.9rem' }}>
            Member roles and invitations coming soon.
          </p>
        </section>
      </main>
    </div>
  );
};

export default AllianceManagement;
