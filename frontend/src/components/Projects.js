// File: ./frontend/src/components/Projects.js
// Class: Projects — fetches and displays projects from the API.

import React, { useState, useEffect, useCallback } from 'react';
import '../styles/Projects.css';
import NewProjectForm from './NewProjectForm';
import ProjectCard from './ProjectCard';
import api from '../api';

const STATUS_STEPS = ['Initiated', 'In Progress', 'Completed', 'Trustifacted'];

const Projects = () => {
  const [projects, setProjects] = useState([]);
  const [isFormVisible, setIsFormVisible] = useState(false);

  const toggleFormVisibility = () => setIsFormVisible((v) => !v);

  const fetchProjects = useCallback(async () => {
    try {
      const response = await api.get('/api/projects');
      const fetched = (response.data || [])
        // Older seed rows have no name/description; only show real projects.
        .filter((p) => p.name && p.description)
        .map((p) => ({
          ...p,
          id: p.project_id,
          owner: p.owner_union || p.owner || 'Independent',
          participants: p.members || [],
          values: p.values || [],
          transactions: [],
          shoutouts: [],
          statusButtons: STATUS_STEPS.map((s) => ({ status: s, label: s })),
        }));
      setProjects(fetched);
    } catch (error) {
      console.error('Error fetching projects:', error);
    }
  }, []);

  useEffect(() => {
    fetchProjects();
  }, [fetchProjects]);

  const handleCreateProject = async () => {
    toggleFormVisibility();
    await fetchProjects();
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
        <NewProjectForm isVisible={isFormVisible} onCreateProject={handleCreateProject} onCancel={toggleFormVisibility} />
        {projects.length === 0 ? (
          <p className="empty-state">No projects yet. Start a shared mission for your community.</p>
        ) : (
          <div className="projects-grid">
            {projects.map((project) => (
              <ProjectCard key={project.id} {...project} onLike={(id) => console.log(`Liked project ${id}`)} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default Projects;
