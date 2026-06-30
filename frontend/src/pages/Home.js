// Home — landing feed: the logged-in user's MeaningTrail and the marketplace.
// Both fetched live from the API; 401 means "not logged in" and shows empty state.

import React, { useState, useEffect, useCallback } from 'react';
import '../styles/MeaningTrail.css';
import '../styles/Marketplace.css';

import MeaningTrail from '../components/MeaningTrail';
import Marketplace from '../components/Marketplace';
import api from '../api';
import { mapService, mapInteraction } from '../utils/mappers';

function Home() {
    const [activeTab, setActiveTab] = useState('meaning_trail');
    const [isFormVisible, setIsFormVisible] = useState(false);
    const [items, setItems] = useState([]);
    const [services, setServices] = useState([]);

    const fetchFeed = useCallback(async () => {
        try {
            const res = await api.get('/api/meaning_trail');
            setItems((res.data || []).map(mapInteraction));
        } catch (e) {
            if (e.response?.status !== 401) console.error('Error fetching meaning_trail:', e);
        }
        try {
            const res = await api.get('/api/marketplace');
            setServices((res.data || []).map(mapService));
        } catch (e) {
            if (e.response?.status !== 401) console.error('Error fetching marketplace:', e);
        }
    }, []);

    useEffect(() => {
        fetchFeed();
    }, [fetchFeed]);

    return (
        <div className="container">
            <aside>
                <h3>Marketplace</h3>
                <button className="btn-orange" onClick={() => setIsFormVisible((v) => !v)}>
                    {isFormVisible ? 'Hide New Service Form' : 'New Service'}
                </button>
                <h3>Meaning Trail</h3>
                <div className="filters">
                    <button>Show All</button>
                    <button>Only Active</button>
                    <button>Only Past</button>
                    <button>Only Shoutouts</button>
                    <button>Only Trustifacts</button>
                </div>
            </aside>
            <main>
                <div className="selector-buttons">
                    <button
                        className={`btn-selector ${activeTab === 'meaning_trail' ? 'active' : ''}`}
                        onClick={() => setActiveTab('meaning_trail')}
                    >
                        Meaning Trail
                    </button>
                    <button
                        className={`btn-selector ${activeTab === 'offers-requests' ? 'active' : ''}`}
                        onClick={() => setActiveTab('offers-requests')}
                    >
                        Offers / Requests
                    </button>
                </div>

                {activeTab === 'meaning_trail' && (
                    items.length === 0
                        ? <p className="empty-state">Your Meaning Trail is empty. Give a little — help a neighbour, share a skill — and your trail of trust will grow here.</p>
                        : <MeaningTrail items={items} />
                )}
                {activeTab === 'offers-requests' && (
                    <Marketplace services={services} newServiceVisible={isFormVisible} onServiceAdded={fetchFeed} />
                )}
            </main>
        </div>
    );
}

export default Home;
