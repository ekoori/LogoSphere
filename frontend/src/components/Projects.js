// File: ./frontend/src/components/Projects.js
// Class: Projects — fetches and displays projects from the API.

import React, { useState, useEffect, useCallback } from 'react';
import '../styles/Projects.css';
import NewProjectForm from './NewProjectForm';
import ProjectCard from './ProjectCard';
import api from '../api';
import { useLogin } from '../App';

const STATUS_STEPS = ['Initiated', 'In Progress', 'Completed', 'Receipted'];

const Projects = () => {
  const { userId } = useLogin();
  const [projects, setProjects] = useState([]);
  const [projectCards, setProjectCards] = useState({});
  const [mySpheres, setMySpheres] = useState([]);
  const [isFormVisible, setIsFormVisible] = useState(false);

  const toggleFormVisibility = () => setIsFormVisible((v) => !v);

  // Spheres this user belongs to — a project must be anchored to one of them.
  const fetchMySpheres = useCallback(async () => {
    if (!userId) return;
    try {
      const res = await api.get('/api/spheres');
      const mine = (res.data || []).filter((s) =>
        (s.participants || []).map(String).includes(String(userId)));
      setMySpheres(mine);
    } catch (e) {
      console.error('Error fetching spheres:', e);
    }
  }, [userId]);

  const fetchProjects = useCallback(async () => {
    try {
      const response = await api.get('/api/projects');
      const fetched = (response.data || [])
        // Older seed rows have no name/description; only show real projects.
        .filter((p) => p.name && p.description)
        .map((p) => ({
          ...p,
          id: p.project_id,
          participants: p.members || [],
          values: p.values || [],
          exchanges: [],
          acknowledgements: [],
          statusButtons: STATUS_STEPS.map((s) => ({ status: s, label: s })),
        }));
      setProjects(fetched);

      // Pull each project's value cards in parallel so the cards can show
      // value-card chips instead of hashtags.
      const results = await Promise.all(
        fetched.map((p) =>
          api.get(`/api/value_cards/${p.id}`)
            .then((r) => ({ id: p.id, cards: r.data || [] }))
            .catch(() => ({ id: p.id, cards: [] }))
        )
      );
      const cardMap = {};
      results.forEach((r) => { cardMap[r.id] = r.cards; });
      setProjectCards(cardMap);
    } catch (error) {
      console.error('Error fetching projects:', error);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
    fetchMySpheres();
  }, [fetchProjects, fetchMySpheres]);

  const handleCreateProject = async (data) => {
    const fd = new FormData();
    fd.append('name', data.name);
    fd.append('description', data.description || '');
    fd.append('location', data.location || '');
    fd.append('sphere_id', data.sphere_id || '');
    fd.append('sphere_name', data.sphere_name || '');
    if (data.owner_alliance_id) fd.append('owner_alliance_id', data.owner_alliance_id);
    if (data.image) fd.append('image', data.image);
    await api.post('/api/projects', fd);
    setIsFormVisible(false);
    await fetchProjects();
  };

  const handleJoin = async (projectId) => {
    try {
      await api.post(`/api/projects/${projectId}/join`);
      await fetchProjects();
    } catch (e) {
      console.error('Failed to join project:', e);
    }
  };

  return (
    <div className="container">
      <aside>
        <div className="search-box">
          <input type="text" placeholder="Search Projects..." />
        </div>
        <div className="filters">
          <button>All Projects</button>
          <button>Your Projects</button>
          <button>Nearby Projects</button>
        </div>
        <button className="btn-orange" onClick={toggleFormVisibility}>Create Project</button>
      </aside>
      <main>
        <NewProjectForm isVisible={isFormVisible} spheres={mySpheres} onCreateProject={handleCreateProject} onCancel={toggleFormVisibility} />
        {projects.length === 0 ? (
          <p className="empty-state">No projects yet. Start a shared mission for your community.</p>
        ) : (
          <div className="projects-grid">
            {projects.map((project) => (
              <ProjectCard key={project.id} {...project} valueCards={projectCards[project.id] || []} currentUserId={userId} onJoin={handleJoin} onLike={() => {}} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default Projects;
