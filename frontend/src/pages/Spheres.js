import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/Spheres.css';
import NewSphereForm from '../components/NewSphereForm';
import SphereCard from '../components/SphereCard';
import api from '../api';

const Spheres = () => {
  const [spheres, setSpheres] = useState([]);
  const navigate = useNavigate();
  const [isFormVisible, setIsFormVisible] = useState(false);

  const toggleFormVisibility = () => {
    setIsFormVisible(!isFormVisible);
  };

  const handleCreateSphere = (newSphere) => {
    const createdSphere = { ...newSphere, id: `sphere-${Date.now()}`, unions: [], participants: [], projects: [], values: [] };
    setSpheres([...spheres, createdSphere]);
    toggleFormVisibility();
    navigate(`/sphere-management/${createdSphere.id}`);
  };

  const dummySpheres = [
    {
      id: 'sphere-ai',
      name: 'AI Development Sphere',
      unions: ['Tech Union', 'AI Enthusiasts Union'],
      participants: ['John Doe', 'Jane Smith', 'Alice Johnson', '147 more...'],
      description: 'A community for AI enthusiasts and professionals. This sphere focuses on developing and advancing AI technologies through collaboration and innovation. We are guided by reason but we hope the successor species we are creating is sentient and will surpass us in wisdom.',
      projects: ['Ongoing Project 1', 'Ongoing Project 2', 'Ongoing Project 3'],
      values: ['technological advancement', 'sentient machines', 'reason']
    },
    {
      id: 'sphere-renewable-energy',
      name: 'Renewable Energy Sphere',
      unions: ['Green Energy Union', 'Sustainability Union'],
      participants: ['Michael Green', 'Sarah Brown', 'Linda White', '95 more...'],
      description: 'A sphere dedicated to promoting and developing renewable energy solutions. Members work together on projects that aim to create sustainable and efficient energy systems.',
      projects: ['Solar Panel Initiative', 'Wind Turbine Project'],
      values: ['sustainability', 'renewable energy', 'environment']
    }
  ];

  const fetchSpheres = useCallback(async () => {
    try {
      const response = await api.get('/api/spheres', {
        withCredentials: true,
      });

      if (response.data) {
        const fetchedSpheres = response.data.map((sphere) => ({
          ...sphere,
          id: sphere.sphere_id,
          unions: sphere.unions ? sphere.unions.slice(0, 5) : [],
          participants: sphere.participants ? sphere.participants.slice(0, 5) : [],
          projects: sphere.projects ? sphere.projects.slice(0, 5) : [],
          values: sphere.values ? sphere.values.slice(0, 5) : [],
        }));
        setSpheres([...dummySpheres, ...fetchedSpheres]);
      }
    } catch (error) {
      console.error('Error fetching spheres:', error);
    }
  }, [dummySpheres]);

  useEffect(() => {
    fetchSpheres();
  }, [fetchSpheres]);

  return (
    <div className="container">
      <aside>
        <div className="search-box">
          <input type="text" placeholder="Search Spheres..." />
        </div>
        <div className="filters">
          <button>All Spheres</button>
          <button>Your Spheres</button>
          <button>Closest by value</button>
          <button>Closest geographically</button>
        </div>
        <button className="btn-orange" onClick={toggleFormVisibility}>Create Sphere</button>
      </aside>
      <main>
        <NewSphereForm isVisible={isFormVisible} onCreateSphere={handleCreateSphere} onCancel={toggleFormVisibility} />
        <div className="sphere-list">
          {spheres.map((sphere) => (
            <SphereCard key={sphere.id} {...sphere} onJoin={(id) => console.log(`Joining sphere ${id}`)} />
          ))}
        </div>
      </main>
    </div>
  );
};

export default Spheres;
