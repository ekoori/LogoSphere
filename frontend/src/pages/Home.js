// Home — landing feed: the logged-in user's TrustTrail and the marketplace.
// Both fetched live from the API; 401 means "not logged in" and shows empty state.

import React, { useState, useEffect, useCallback } from 'react';
import '../styles/TrustTrail.css';
import '../styles/Marketplace.css';

import TrustTrail from '../components/TrustTrail';
import Marketplace from '../components/Marketplace';
import api from '../api';
import { mapService, mapTransaction } from '../utils/mappers';

function Home() {
    const [activeTab, setActiveTab] = useState('trusttrail');
    const [isFormVisible, setIsFormVisible] = useState(false);
    const [items, setItems] = useState([]);
    const [services, setServices] = useState([]);

    const fetchFeed = useCallback(async () => {
        try {
            const res = await api.get('/api/trusttrail');
            setItems((res.data || []).map(mapTransaction));
        } catch (e) {
            if (e.response?.status !== 401) console.error('Error fetching trusttrail:', e);
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
                <h3>TrustTrail</h3>
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
                        className={`btn-selector ${activeTab === 'trusttrail' ? 'active' : ''}`}
                        onClick={() => setActiveTab('trusttrail')}
                    >
                        TrustTrail
                    </button>
                    <button
                        className={`btn-selector ${activeTab === 'offers-requests' ? 'active' : ''}`}
                        onClick={() => setActiveTab('offers-requests')}
                    >
                        Offers / Requests
                    </button>
                </div>

                {activeTab === 'trusttrail' && (
                    items.length === 0
                        ? <p className="empty-state">Your TrustTrail is empty. Give a little — help a neighbour, share a skill — and your trail of trust will grow here.</p>
                        : <TrustTrail items={items} />
                )}
                {activeTab === 'offers-requests' && (
                    <Marketplace services={services} newServiceVisible={isFormVisible} onServiceAdded={fetchFeed} />
                )}
            </main>
        </div>
    );
}

export default Home;
