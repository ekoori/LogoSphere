// MarketplacePage — the full marketplace of offers & requests, fetched live.
import React, { useState, useEffect, useCallback } from 'react';
import '../styles/App.css';
import '../styles/Marketplace.css';

import Marketplace from '../components/Marketplace';
import api from '../api';
import { mapService } from '../utils/mappers';

function MarketplacePage() {
    const [isFormVisible, setIsFormVisible] = useState(false);
    const [services, setServices] = useState([]);
    const [filter, setFilter] = useState('all');

    const toggleFormVisibility = () => setIsFormVisible((v) => !v);

    const fetchServices = useCallback(async () => {
        try {
            const res = await api.get('/api/marketplace');
            setServices((res.data || []).map(mapService));
        } catch (e) {
            console.error('Error fetching marketplace:', e);
        }
    }, []);

    useEffect(() => {
        fetchServices();
    }, [fetchServices]);

    const shown = services.filter((s) =>
        filter === 'all' ? true : filter === 'offers' ? s.type === 'offer' : s.type === 'request'
    );

    return (
        <div className="container">
            <aside>
                <button className="btn-orange" onClick={toggleFormVisibility}>
                    {isFormVisible ? 'Hide New Service Form' : 'New Service'}
                </button>
                <div className="search-box">
                    <input type="text" placeholder="Search..." />
                </div>
                <div className="filters">
                    <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>Show All</button>
                    <button className={filter === 'offers' ? 'active' : ''} onClick={() => setFilter('offers')}>Offers</button>
                    <button className={filter === 'requests' ? 'active' : ''} onClick={() => setFilter('requests')}>Requests</button>
                </div>
            </aside>
            <main>
                {shown.length === 0 ? (
                    <p className="empty-state">No offers or requests yet. Share something with your community.</p>
                ) : (
                    <Marketplace services={shown} newServiceVisible={isFormVisible} />
                )}
            </main>
        </div>
    );
}

export default MarketplacePage;
