import React, { useState, useEffect, useCallback } from 'react';
import '../styles/Unions.css';
import NewUnionForm from '../components/NewUnionForm';
import UnionCard from '../components/UnionCard';
import api from '../api';

const Unions = () => {
  const [unions, setUnions] = useState([]);
  const [isFormVisible, setIsFormVisible] = useState(false);

  const toggleFormVisibility = () => setIsFormVisible((v) => !v);

  const fetchUnions = useCallback(async () => {
    try {
      const response = await api.get('/api/unions');
      const fetched = (response.data || []).map((u) => ({
        ...u,
        id: u.union_id,
        participants: u.members || [],
        projects: u.projects || [],
        values: u.values || [],
      }));
      setUnions(fetched);
    } catch (error) {
      console.error('Error fetching unions:', error);
    }
  }, []);

  useEffect(() => {
    fetchUnions();
  }, [fetchUnions]);

  const handleCreateUnion = async () => {
    toggleFormVisibility();
    await fetchUnions();
  };

  return (
    <div className="container">
      <aside>
        <div className="search-box">
          <input type="text" placeholder="Search Unions..." />
        </div>
        <div className="filters">
          <button>All Unions</button>
          <button>Your Unions</button>
          <button>Closest by value</button>
          <button>Closest geographically</button>
        </div>
        <button className="btn-orange" onClick={toggleFormVisibility}>Create Union</button>
      </aside>
      <main>
        <NewUnionForm isVisible={isFormVisible} onCreateUnion={handleCreateUnion} onCancel={toggleFormVisibility} />
        {unions.length === 0 ? (
          <p className="empty-state">No unions yet. Gather a few people and start one.</p>
        ) : (
          <div className="unions-grid">
            {unions.map((union) => (
              <UnionCard key={union.id} {...union} onJoin={(id) => console.log(`Joining union ${id}`)} />
            ))}
          </div>
        )}
      </main>
    </div>
  );
};

export default Unions;
