import React, { useState } from 'react';
import '../styles/Alliances.css';
import SphereBanner from './SphereBanner'; // Assuming SphereBanner is in the same directory

const NewAllianceForm = ({ isVisible, onCreateAlliance, onCancel }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [meaningGraph, setMeaningGraph] = useState('');
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
    onCreateAlliance({ name, description, meaningGraph, location, image });
  };

  if (!isVisible) return null;

  return (
    <div id="alliance-form" className="interaction">
      <h3>Create a New Alliance</h3>
      <form onSubmit={handleSubmit}>
        <SphereBanner previewUrl={previewUrl} onImageChange={handleImageChange} />

        <label htmlFor="alliance-name">Alliance Name:</label>
        <input type="text" id="alliance-name" name="alliance-name" value={name} onChange={(e) => setName(e.target.value)} required />

        <label htmlFor="alliance-description">Alliance Description:</label>
        <textarea id="alliance-description" name="alliance-description" value={description} onChange={(e) => setDescription(e.target.value)} required></textarea>

        <label htmlFor="alliance-meaning-graph">Meaning Graph:</label>
        <input type="text" id="alliance-meaning-graph" name="alliance-meaning-graph" value={meaningGraph} onChange={(e) => setMeaningGraph(e.target.value)} required />

        <label htmlFor="alliance-location">Geographical Location:</label>
        <input type="text" id="alliance-location" name="alliance-location" value={location} onChange={(e) => setLocation(e.target.value)} required />

        <div className="form-buttons">
          <button type="submit" className="btn-orange">Create Alliance</button>
          <button type="button" className="btn-blue" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
};

export default NewAllianceForm;
