import React, { useState } from 'react';
import '../styles/Projects.css';
import SphereBanner from './SphereBanner'; // Assuming SphereBanner is in the same directory

const NewProjectForm = ({ isVisible, onCreateProject, onCancel }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [valueGraph, setValueGraph] = useState('');
  const [location, setLocation] = useState('');
  const [image, setImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => {
        setPreviewUrl(reader.result);
      };
      reader.readAsDataURL(file);
      setImage(file);
    }
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    onCreateProject({ name, description, valueGraph, location, image });
  };

  if (!isVisible) return null;

  return (
    <div id="project-form" className="interaction">
      <h3>Create a New Project</h3>
      <form onSubmit={handleSubmit}>
        <SphereBanner previewUrl={previewUrl} onImageChange={handleImageChange} />

        <label htmlFor="project-name">Project Name:</label>
        <input type="text" id="project-name" name="project-name" value={name} onChange={(e) => setName(e.target.value)} required />

        <label htmlFor="project-description">Project Description:</label>
        <textarea id="project-description" name="project-description" value={description} onChange={(e) => setDescription(e.target.value)} required></textarea>

        <label htmlFor="project-value-graph">Value Graph:</label>
        <input type="text" id="project-value-graph" name="project-value-graph" value={valueGraph} onChange={(e) => setValueGraph(e.target.value)} required />

        <label htmlFor="project-location">Geographical Location:</label>
        <input type="text" id="project-location" name="project-location" value={location} onChange={(e) => setLocation(e.target.value)} required />

        <div className="form-buttons">
          <button type="submit" className="btn-orange">Create Project</button>
          <button type="button" className="btn-blue" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
};

export default NewProjectForm;
