import React, { useState, useEffect, useCallback } from 'react';
import '../styles/Alliances.css';
import NewAllianceForm from '../components/NewAllianceForm';
import AllianceCard from '../components/AllianceCard';
import api from '../api';
import { useLogin } from '../App';

const Alliances = () => {
  const { userId } = useLogin();
  const [alliances, setAlliances] = useState([]);
  const [isFormVisible, setIsFormVisible] = useState(false);

  const toggleFormVisibility = () => setIsFormVisible((v) => !v);

  const fetchAlliances = useCallback(async () => {
    try {
      const response = await api.get('/api/alliances');
      const fetched = (response.data || []).map((a) => ({
        ...a,
        id: a.alliance_id,
        participants: a.members || [],
        projects: a.projects || [],
        values: a.values || [],
      }));
      setAlliances(fetched);
    } catch (error) {
      console.error('Error fetching alliances:', error);
    }
  }, []);

  useEffect(() => {
    fetchAlliances();
  }, [fetchAlliances]);

  const handleCreateAlliance = async () => {
    toggleFormVisibility();
    await fetchAlliances();
  };

  const handleJoin = async (allianceId) => {
    try {
      await api.post(`/api/alliances/${allianceId}/join`);
      await fetchAlliances();
    } catch (e) {
      console.error('Failed to join alliance:', e);
    }
  };

  return (
    <div className="container">
      <aside>
        <div className="search-box">
          <input type="text" placeholder="Search Alliances..." />
        </div>
        <div className="filters">
          <button>All Alliances</button>
          <button>Your Alliances</button>
          <button>Closest by value</button>
          <button>Closest geographically</button>
        </div>
        <button className="btn-orange" onClick={toggleFormVisibility}>Create Alliance</button>
      </aside>
      <main>
        <NewAllianceForm isVisible={isFormVisible} onCreateAlliance={handleCreateAlliance} onCancel={toggleFormVisibility} />
        {alliances.length === 0 ? (
          <p className="empty-state">No alliances yet. Gather a few people and start one.</p>
        ) : (
          <div className="alliances-grid">
            {alliances.map((alliance) => (
              <AllianceCard key={alliance.id} {...alliance} currentUserId={userId} onJoin={handleJoin} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default Alliances;
