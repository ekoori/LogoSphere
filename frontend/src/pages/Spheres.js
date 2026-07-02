import React, { useState, useEffect, useCallback } from 'react';
import '../styles/Spheres.css';
import NewSphereForm from '../components/NewSphereForm';
import SphereCard from '../components/SphereCard';
import api from '../api';
import { useLogin } from '../App';

const Spheres = () => {
  const { userId } = useLogin();
  const [spheres, setSpheres] = useState([]);
  const [sphereCards, setSphereCards] = useState({});
  const [isFormVisible, setIsFormVisible] = useState(false);

  const toggleFormVisibility = () => setIsFormVisible((v) => !v);

  const fetchSpheres = useCallback(async () => {
    try {
      const response = await api.get('/api/spheres');
      const fetched = (response.data || []).map((sphere) => ({
        ...sphere,
        id: sphere.sphere_id,
        alliances: sphere.alliances || [],
        participants: sphere.members || [],
        projects: sphere.projects || [],
        values: sphere.values || [],
      }));
      setSpheres(fetched);

      // Fetch value cards for each sphere in parallel
      const results = await Promise.all(
        fetched.map(s =>
          api.get(`/api/value_cards/${s.id}`)
            .then(r => ({ id: s.id, cards: r.data || [] }))
            .catch(() => ({ id: s.id, cards: [] }))
        )
      );
      const cardMap = {};
      results.forEach(r => { cardMap[r.id] = r.cards; });
      setSphereCards(cardMap);
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

  const handleJoin = async (sphereId) => {
    try {
      await api.post(`/api/spheres/${sphereId}/join`);
      await fetchSpheres();
    } catch (e) {
      console.error('Failed to join sphere:', e);
    }
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
              <SphereCard
                key={sphere.id}
                {...sphere}
                valueCards={sphereCards[sphere.id] || []}
                currentUserId={userId}
                isMember={!!userId && sphere.participants.some((p) => (p.id || p) === userId)}
                onJoin={handleJoin}
              />
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default Spheres;
