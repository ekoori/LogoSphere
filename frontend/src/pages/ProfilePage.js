// File: ./frontend/src/pages/ProfilePage.js
// Description: This is the React.js file for the user profile page. It displays user information and allows editing if the user is logged in.
// Classes/Methods/Properties:
//    [+] ProfilePage - The main component for the profile page.
//        [+] isEditing - State property to track whether the profile is in edit mode.
//        [+] profileData - State property to store the user's profile information.
//        [+] handleEditToggle - Toggles the edit mode for the profile.
//        [+] handleInputChange - Handles changes to the input fields in the edit mode.
//        [+] handleImageChange - Handles changes to the profile image.
//        [+] handleSaveChanges - Saves the changes made to the profile.


import React, { useState, useEffect } from 'react';
import { useNavigate, Navigate } from 'react-router-dom';
import '../styles/Profile.css';
import { useLogin } from '../App';
import api from '../api';

const DUMMY_PROFILE = {
  name: 'Sam Altman',
  email: 'sam.altman@example.com',
  location: 'San Francisco, USA',
  joined: 'January 2023',
  image: 'static/user-image.jpg',
  values: ['#community', '#technology', '#sustainability'],
  spheres: ['AI Development Sphere', 'Renewable Energy Sphere'],
  unions: ['Tech Union', 'AI Enthusiasts Union'],
  projects: ['OpenAI Datacenter Expansion', 'Community Garden Initiative'],
  following: ['Elon Musk', 'Joe Rogan']
};

const ProfilePage = () => {
  const [isEditing, setIsEditing] = useState(false);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);
  const [profileData, setProfileData] = useState(DUMMY_PROFILE);
  const [imageFile, setImageFile] = useState(null);

  const { isLoggedIn } = useLogin();
  const navigate = useNavigate();

  useEffect(() => {
    const fetchUserData = async () => {
      if (!isLoggedIn) {
        // navigate('/login', { replace: true });
        return;
      }

      try {
        setLoading(true);
        setError(null);
        console.log('Fetching user data...');
        
        const response = await api.get('/api/user/profile', {
          withCredentials: true,
          headers: {
            'Content-Type': 'application/json',
          }
        });

        console.log('User data response:', response);

        if (response.data) {
          setProfileData(prevData => ({
            ...prevData,
            name: response.data.name || prevData.name,
            email: response.data.email || prevData.email,
            location: response.data.location || prevData.location,
            image: response.data.profile_picture ? `data:image/jpeg;base64,${response.data.profile_picture}` : prevData.image,
            // Keep dummy data for these if not provided by the API
            values: response.data.values || prevData.values,
            spheres: response.data.spheres || prevData.spheres,
            unions: response.data.unions || prevData.unions,
            projects: response.data.projects || prevData.projects,
            following: response.data.following || prevData.following
          }));
        }
      } catch (error) {
        console.error('Error fetching user data:', error);
        if (error.response?.status === 401) {
          navigate('/login', { replace: true });
        } else {
          setError('Failed to load profile data, showing default profile.');
          // Keep the dummy data in case of error
          setProfileData(DUMMY_PROFILE);
        }
      } finally {
        setLoading(false);
      }
    };

    fetchUserData();
    
  }, [isLoggedIn, navigate]);

  const handleEditToggle = () => {
    setIsEditing(!isEditing);
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setProfileData(prev => ({
      ...prev,
      [name]: value
    }));
  };

  const handleImageChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      const file = e.target.files[0];
      setImageFile(file);
      setProfileData(prev => ({
        ...prev,
        image: URL.createObjectURL(file)
      }));
    }
  };

  const handleSaveChanges = async (e) => {
    e.preventDefault();
    try {
      const formData = new FormData();
      formData.append('name', profileData.name);
      formData.append('location', profileData.location);
      if (imageFile) {
        formData.append('profile_picture', imageFile);
      }

      const response = await api.post('/api/updateuser', formData, {
        withCredentials: true,
        headers: {
          'Content-Type': 'multipart/form-data',
        }
      });

      if (response.status === 200) {
        setProfileData(prev => ({
          ...prev,
          ...response.data,
          image: response.data.profile_picture ? `data:image/jpeg;base64,${response.data.profile_picture}` : prev.image,
          // Preserve the data that might not be returned by the API
          values: prev.values,
          spheres: prev.spheres,
          unions: prev.unions,
          projects: prev.projects,
          following: prev.following
        }));
        setIsEditing(false);
        setError(null);
      }
    } catch (error) {
      console.error('Error saving user data:', error);
      setError('Failed to save changes. Please try again.');
    }
  };

  // If not logged in, redirect to login
  if (!isLoggedIn) {
    // return <Navigate to="/login" replace />;
  }

  if (loading) {
    return <div className="container">Loading profile...</div>;
  }

  return (
    <div className="container">
      <aside className="profile-sidebar">
        <img src={profileData.image} alt="Profile" className="profile-image" />
        <div className="profile-info">
          <h2>{profileData.name}</h2>
          <p>Location: {profileData.location}</p>
          <p>Joined: {profileData.joined}</p>
          <button className="btn-orange" onClick={handleEditToggle}>
            {isEditing ? 'Cancel' : 'Edit Profile'}
          </button>
          {isEditing && (
            <form className="profile-form" onSubmit={handleSaveChanges}>
              <div className="form-group">
                <label htmlFor="profileImage">Profile Image</label>
                <input 
                  type="file" 
                  id="profileImage" 
                  name="profileImage" 
                  onChange={handleImageChange} 
                />
              </div>
              <div className="form-group">
                <label htmlFor="name">Name</label>
                <input 
                  type="text" 
                  id="name" 
                  name="name" 
                  value={profileData.name} 
                  onChange={handleInputChange} 
                />
              </div>
              <div className="form-group">
                <label htmlFor="location">Location</label>
                <input 
                  type="text" 
                  id="location" 
                  name="location" 
                  value={profileData.location} 
                  onChange={handleInputChange} 
                />
              </div>
              <button type="submit" className="btn-orange">Save Changes</button>
              {error && <div className="error-message">{error}</div>}
            </form>
          )}
        </div>
      </aside>
      <main>
        <div className="profile-section">
          <div className="profile-header">
            <h2>{profileData.name}</h2>
            {error && <div className="error-banner">{error}</div>}
          </div>
          <div className="profile-values">
            <h3>Your Value Graph</h3>
            <div className="values-container">
              {profileData.values.map((value, index) => (
                <span key={index} className="value-tag">{value}</span>
              ))}
            </div>
          </div>
          <div className="profile-spheres">
            <h3>Spheres you are a member of</h3>
            <ul className="sphere-list">
              {profileData.spheres.map((sphere, index) => (
                <li key={index}>{sphere}</li>
              ))}
            </ul>
          </div>
          <div className="profile-unions">
            <h3>Unions you are a member of</h3>
            <ul className="sphere-list">
              {profileData.unions.map((union, index) => (
                <li key={index}>{union}</li>
              ))}
            </ul>
          </div>
          <div className="profile-projects">
            <h3>Currently active projects</h3>
            <ul className="sphere-list">
              {profileData.projects.map((project, index) => (
                <li key={index}>{project}</li>
              ))}
            </ul>
          </div>
          <div className="profile-following">
            <h3>Users you are following</h3>
            <ul className="sphere-list">
              {profileData.following.map((user, index) => (
                <li key={index}>{user}</li>
              ))}
            </ul>
          </div>
        </div>
      </main>
    </div>
  );
};

export default ProfilePage;