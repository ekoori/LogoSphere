import '../styles/App.css';
import React from 'react';
import PropTypes from 'prop-types';

const SphereBanner = ({ previewUrl, onImageChange }) => {
  const handleImageChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      onImageChange(e);
    }
  };

  return (
    <div className="sphere-banner">
      <label htmlFor="sphere-image" className="set-image-btn">Set image...</label>
      <input
        type="file"
        id="sphere-image"
        name="sphere-image"
        style={{ display: 'none' }}
        accept="image/*"
        onChange={handleImageChange}
      />
      {previewUrl && <img id="preview-image" src={previewUrl} alt="Banner preview" className="banner-image" />}
    </div>
  );
};

SphereBanner.propTypes = {
  previewUrl: PropTypes.string,
  onImageChange: PropTypes.func.isRequired
};

export default SphereBanner;
