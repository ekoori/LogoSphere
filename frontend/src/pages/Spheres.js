import React, { useState, useEffect, useCallback } from 'react';
import '../styles/Spheres.css';
import NewSphereForm from '../components/NewSphereForm';
import SphereCard from '../components/SphereCard';
import api from '../api';

const Spheres = () => {
  const [spheres, setSpheres] = useState([]);
  const [isFormVisible, setIsFormVisible] = useState(false);

  const toggleFormVisibility = () => setIsFormVisible((v) => !v);

  const fetchSpheres = useCallback(async () => {
    try {
      const response = await api.get('/api/spheres');
      const fetched = (response.data || []).map((sphere) => ({
        ...sphere,
        id: sphere.sphere_id,
        alliances: sphere.alliances || [],
        // {id, name} pairs so each member links to their profile.
        participants: sphere.members || [],
        projects: sphere.projects || [],
        values: sphere.values || [],
      }));
      setSpheres(fetched);
    } catch (error) {
      console.error('Error fetching spheres:', error);
    }
  }, []);

  useEffect(() => {
    fetchSpheres();
  }, [fetchSpheres]);

  const handleCreateSphere = async () => {
    // The form posts to the API; refresh the list to show the new sphere.
    toggleFormVisibility();
    await fetchSpheres();
  };

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
        {spheres.length === 0 ? (
          <p className="empty-state">No spheres yet. Be the first to start a community.</p>
        ) : (
          <div className="spheres-grid">
            {spheres.map((sphere) => (
              <SphereCard key={sphere.id} {...sphere} onJoin={(id) => console.log(`Joining sphere ${id}`)} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default Spheres;
