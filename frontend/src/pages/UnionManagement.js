import React, { useState } from 'react';
import '../styles/UnionManagement.css';
import SphereBanner from '../components/SphereBanner';

const UnionManagement = () => {
  const [union, setUnion] = useState({
    name: 'Tech Union',
    description: 'Advancing technology through collaboration.',
    policies: ['Tech Union Policy'],
    bannerImage: 'static/A_banner_image_for_a_tech_union_in_a_solar_punk_en.png'
  });
  const [previewUrl, setPreviewUrl] = useState(union.bannerImage);

  const [activeTab, setActiveTab] = useState('delegation');
  const [nameEdit, setNameEdit] = useState(false);
  const [descriptionEdit, setDescriptionEdit] = useState(false);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result);
      };
      reader.readAsDataURL(file);
      setUnion((prevUnion) => ({
        ...prevUnion,
        bannerImage: file
      }));
    }
  };

  const handleNameEdit = () => setNameEdit(!nameEdit);
  const handleDescriptionEdit = () => setDescriptionEdit(!descriptionEdit);

  const saveName = (e) => {
    e.preventDefault();
    setUnion({ ...union, name: e.target.name.value });
    setNameEdit(false);
  };

  const saveDescription = (e) => {
    e.preventDefault();
    setUnion({ ...union, description: e.target.description.value });
    setDescriptionEdit(false);
  };

  const switchTab = (tab) => {
    setActiveTab(tab);
  };

  return (
    <div className="container">
      <aside className="management-sidebar">
        <h2>Union Management</h2>
        <div>
          {!nameEdit ? (
            <h3 id="union-name-display" onClick={handleNameEdit}>{union.name}</h3>
          ) : (
            <form onSubmit={saveName}>
              <input type="text" name="name" defaultValue={union.name} />
              <button type="submit" className="btn-orange">Save</button>
            </form>
          )}
        </div>
        <div>
          {!descriptionEdit ? (
            <p id="union-description-display" onClick={handleDescriptionEdit}>{union.description}</p>
          ) : (
            <form onSubmit={saveDescription}>
              <textarea name="description" defaultValue={union.description}></textarea>
              <button type="submit" className="btn-orange">Save</button>
            </form>
          )}
        </div>
        <div className="policy-section">
          <h3>Policies</h3>
          <ul>
            {union.policies.map((policy, index) => (
              <li key={index}><a href="/docs/mainpolicy">{policy}</a></li>
            ))}
          </ul>
        </div>
      </aside>
      <main>
        <div className="tab-selector">
          <button className={`btn-selector ${activeTab === 'delegation' ? 'active' : ''}`} onClick={() => switchTab('delegation')}>Sphere Delegation</button>
          <button className={`btn-selector ${activeTab === 'voting' ? 'active' : ''}`} onClick={() => switchTab('voting')}>Voting</button>
          <button className={`btn-selector ${activeTab === 'projects' ? 'active' : ''}`} onClick={() => switchTab('projects')}>Projects</button>
          <button className={`btn-selector ${activeTab === 'members' ? 'active' : ''}`} onClick={() => switchTab('members')}>Members</button>
        </div>
        <section id="delegation" className={`management-section tab-content ${activeTab === 'delegation' ? '' : 'hidden'}`}>
          <h3>Sphere Management</h3>
          <form>
            <div className="form-group">
              <label htmlFor="project-management">Project management performed by:</label>
              <select id="project-management" name="project-management">
                <option value="single-pm">A single PM</option>
                <option value="board-members">Board members</option>
              </select>
            </div>
            <div className="form-group">
              <label htmlFor="trustifacting">TrustiFacting performed by:</label>
              <select id="trustifacting" name="trustifacting">
                <option value="lead">Lead</option>
                <option value="board-members">Board members</option>
                <option value="any-member">Any member</option>
              </select>
            </div>
            <button type="submit" className="btn-orange">Save Changes</button>
          </form>
          <div className="vote-delegation">
            <h3>Your delegation of Union vote</h3>
            <form>
              <div className="form-group">
                <label htmlFor="delegate-vote">Delegate your vote to:</label>
                <input type="text" id="delegate-vote" name="delegate-vote" placeholder="Enter user to delegate" />
                <button type="submit" className="btn-orange">Delegate</button>
              </div>
            </form>
          </div>
        </section>
        <section id="voting" className={`management-section tab-content ${activeTab === 'voting' ? '' : 'hidden'}`}>
          <h3>Voting</h3>
          <form>
            <div className="form-group">
              <label htmlFor="voting">Decisions made by:</label>
              <select id="voting" name="voting">
                <option value="majority"> more than 50% majority</option>
                <option value="twothirds">2/3</option>
                <option value="authocracy">Authocracy</option>
                <option value="board">Board</option>
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
        <section id="projects" className={`management-section tab-content ${activeTab === 'projects' ? '' : 'hidden'}`}>
          <h3>Manage Projects</h3>
          <form>
            <div className="form-group">
              <label htmlFor="project-name">Create a new project</label>
              <input type="text" id="project-name" name="project-name" placeholder="Enter project name" />
              <button type="submit" className="btn-orange">Add</button>
            </div>
            <div className="project-list">
              <h4>Current Projects</h4>
              <ul>
                <li>
                  <a href="/project">AI Ethics Initiative</a>
                  <div className="form-group">
                    <label htmlFor="project-manager">Assign project manager:</label>
                    <input type="text" id="project-manager" name="project-manager" placeholder="Enter project manager" />
                    <button type="submit" className="btn-orange">Assign</button>
                  </div>
                  <button className="btn-remove">Remove</button>
                </li>
                <li>
                  <a href="/project">OpenAI Collaboration</a>
                  <div className="form-group">
                    <label htmlFor="project-manager">Assign project manager:</label>
                    <input type="text" id="project-manager" name="project-manager" placeholder="Enter project manager" />
                    <button type="submit" className="btn-orange">Assign</button>
                  </div>
                  <button className="btn-remove">Remove</button>
                </li>
                {/* More projects can be listed here */}
              </ul>
            </div>
          </form>
        </section>
        <section id="members" className={`management-section tab-content ${activeTab === 'members' ? '' : 'hidden'}`}>
          <h3>Manage Members</h3>
          <form>
            <div className="form-group">
              <label htmlFor="member-name">Add Member</label>
              <input type="text" id="member-name" name="member-name" placeholder="Enter member name" />
              <button type="submit" className="btn-orange">Add</button>
            </div>
            <div className="member-list">
              <h4>Current Members</h4>
              <ul>
                <li><a href="/user">Jane Doe</a> <button className="btn-remove">Remove</button></li>
                <li><a href="/user">John Smith</a> <button className="btn-remove">Remove</button></li>
                {/* More members can be listed here */}
              </ul>
            </div>
          </form>
        </section>
      </main>
    </div>
  );
};

export default UnionManagement;
