import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import '../styles/SphereManagement.css';
import SphereBanner from '../components/SphereBanner';
import api from '../api';

const SphereManagement = () => {
  const { sphereId } = useParams();
  const [sphere, setSphere] = useState(null);
  const [previewUrl, setPreviewUrl] = useState('');

  const dummySphere = {
    id: 'sphere-ai',
    name: 'AI Development Sphere',
    location: 'Global',
    status: 'Active',
    admin: 'Jane Doe',
    description: 'The AI Development Sphere is dedicated to advancing artificial intelligence technologies and fostering collaboration among AI researchers and developers.',
    alliances: ['Tech Alliance', 'AI Enthusiasts Alliance'],
    members: ['Jane Doe', 'John Smith', '50 more...'],
    projects: ['AI Ethics Initiative', 'OpenAI Collaboration'],
    values: ['innovation', 'technology', 'collaboration'],
    bannerImage: 'static/A_banner_image_for_an_AI_Development_Sphere_in_a_s.png'
  };

  useEffect(() => {
    const fetchSphere = async () => {
      try {
        const response = await api.get(`/api/spheres/${sphereId}`, {
          withCredentials: true,
        });

        if (response.data) {
          setSphere(response.data);
          setPreviewUrl(response.data.image);
        }
      } catch (error) {
        console.error('Error fetching sphere:', error);
        setSphere(dummySphere);
        setPreviewUrl(dummySphere.bannerImage);
      }
    };

    if (sphereId) {
      fetchSphere();
    } else {
      setSphere(dummySphere);
      setPreviewUrl(dummySphere.bannerImage);
    }
  }, [sphereId]);

  if (!sphere) return <div>Loading...</div>;

  return (
    <div className="container">
      <aside className="sphere-sidebar">
        <h2>{sphere.name}</h2>
        <p><strong>Location:</strong> {sphere.location}</p>
        <p><strong>Status:</strong> <span className="status active">{sphere.status}</span></p>
        <p><strong>Admin:</strong> <a href="/user">{sphere.admin}</a></p>
        <a href="/sphere-management" className="btn-orange">Manage Sphere</a>
      </aside>
      <main>
        <div className="sphere-section">
          <SphereBanner previewUrl={previewUrl} onImageChange={(e) => {}} />

          <div className="sphere-description">
            <h3>Description</h3>
            <p>{sphere.description}</p>
          </div>
          <div className="sphere-alliances">
            <h3>Member Alliances</h3>
            <ul className="alliance-list">
              {sphere.alliances.map((alliance, index) => (
                <li key={index}><a href="/alliance">{alliance}</a></li>
              ))}
            </ul>
          </div>
          <div className="sphere-members">
            <h3>All Members</h3>
            <ul className="member-list">
              {sphere.members.map((member, index) => (
                <li key={index}><a href={index < sphere.members.length - 1 ? "/user" : "/members"}>{member}</a></li>
              ))}
            </ul>
          </div>
          <div className="sphere-projects">
            <h3>Current Projects</h3>
            <ul className="project-list">
              {sphere.projects.map((project, index) => (
                <li key={index}><a href="/project">{project}</a></li>
              ))}
            </ul>
          </div>
          <div className="sphere-values">
            <h3>Meaning Graph</h3>
            {sphere.values.map((value, index) => (
              <span key={index}>#{value}</span>
            ))}
          </div>
        </div>
      </main>
    </div>
  );
};

export default SphereManagement;
