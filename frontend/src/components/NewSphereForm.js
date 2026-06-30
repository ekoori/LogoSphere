import React, { useState } from 'react';
import '../styles/Spheres.css';
import SphereBanner from './SphereBanner';
import api from '../api';

const NewSphereForm = ({ isVisible, onCreateSphere, onCancel }) => {
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    const formData = new FormData();
    formData.append('name', name);
    formData.append('description', description);
    formData.append('value_graph', valueGraph);
    formData.append('location', location);
    if (image) {
      formData.append('image', image);
    }

    try {
      const response = await api.post('/api/spheres', formData, {
        headers: {
          'Content-Type': 'multipart/form-data',
        },
        withCredentials: true,
      });

      if (response.status === 201) {
        onCreateSphere(response.data);
      }
    } catch (error) {
      console.error('Error creating sphere:', error);
    }
  };

  if (!isVisible) return null;

  return (
    <div id="sphere-form" className="interaction">
      <h3>Create a New Sphere</h3>
      <form onSubmit={handleSubmit}>
        <SphereBanner previewUrl={previewUrl} onImageChange={handleImageChange} />

        <label htmlFor="sphere-name">Sphere Name:</label>
        <input type="text" id="sphere-name" name="sphere-name" value={name} onChange={(e) => setName(e.target.value)} required />

        <label htmlFor="sphere-description">Sphere Description:</label>
        <textarea id="sphere-description" name="sphere-description" value={description} onChange={(e) => setDescription(e.target.value)} required></textarea>

        <label htmlFor="sphere-value-graph">Value Graph:</label>
        <input type="text" id="sphere-value-graph" name="sphere-value-graph" value={valueGraph} onChange={(e) => setValueGraph(e.target.value)} required />

        <label htmlFor="sphere-location">Geographical Location:</label>
        <input type="text" id="sphere-location" name="sphere-location" value={location} onChange={(e) => setLocation(e.target.value)} required />

        <div className="form-buttons">
          <button type="submit" className="btn-orange">Create Sphere</button>
          <button type="button" className="btn-blue" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
};

export default NewSphereForm;
