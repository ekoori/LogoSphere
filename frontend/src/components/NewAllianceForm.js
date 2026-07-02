import React, { useState } from 'react';
import '../styles/Alliances.css';
import SphereBanner from './SphereBanner';

// `spheres` is the list of spheres the current user belongs to — an alliance
// must be anchored to exactly one of them. onCreateAlliance receives a plain
// object; the parent page builds the multipart request and POSTs it.
const NewAllianceForm = ({ isVisible, spheres = [], onCreateAlliance, onCancel }) => {
  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [location, setLocation] = useState('');
  const [sphereId, setSphereId] = useState('');
  const [image, setImage] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');
  const [error, setError] = useState('');
  const [submitting, setSubmitting] = useState(false);

  const handleImageChange = (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onloadend = () => setPreviewUrl(reader.result);
      reader.readAsDataURL(file);
      setImage(file);
    }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!sphereId) { setError('Please choose the sphere this alliance operates in.'); return; }
    const sphere = spheres.find((s) => s.sphere_id === sphereId);
    setError('');
    setSubmitting(true);
    try {
      await onCreateAlliance({
        name, description, location, image,
        sphere_id: sphereId,
        sphere_name: sphere ? sphere.name : '',
      });
    } catch (err) {
      setError(err.response?.data?.message || 'Failed to create alliance.');
    } finally {
      setSubmitting(false);
    }
  };

  if (!isVisible) return null;

  return (
    <div id="alliance-form" className="exchange">
      <h3>Create a New Alliance</h3>
      {error && <p className="form-error">{error}</p>}
      <form onSubmit={handleSubmit}>
        <SphereBanner previewUrl={previewUrl} onImageChange={handleImageChange} />

        <label htmlFor="alliance-name">Alliance Name:</label>
        <input type="text" id="alliance-name" value={name} onChange={(e) => setName(e.target.value)} required />

        <label htmlFor="alliance-description">Alliance Description:</label>
        <textarea id="alliance-description" value={description} onChange={(e) => setDescription(e.target.value)} required></textarea>

        <label htmlFor="alliance-sphere">Operating Sphere:</label>
        {spheres.length === 0 ? (
          <p className="form-hint">You need to join a sphere before you can start an alliance in it.</p>
        ) : (
          <select id="alliance-sphere" value={sphereId} onChange={(e) => setSphereId(e.target.value)} required>
            <option value="">— choose a sphere —</option>
            {spheres.map((s) => (
              <option key={s.sphere_id} value={s.sphere_id}>{s.name}</option>
            ))}
          </select>
        )}

        <label htmlFor="alliance-location">Geographical Location:</label>
        <input type="text" id="alliance-location" value={location} onChange={(e) => setLocation(e.target.value)} />

        <div className="form-buttons">
          <button type="submit" className="btn-orange" disabled={submitting || spheres.length === 0}>
            {submitting ? 'Creating…' : 'Create Alliance'}
          </button>
          <button type="button" className="btn-blue" onClick={onCancel}>Cancel</button>
        </div>
      </form>
    </div>
  );
};

export default NewAllianceForm;
