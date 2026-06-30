// UserPage — public profile for any user, loaded by ?id=.
// Shows their TrustTrail as collapsible TransactionCards and their posted
// marketplace offers/requests, mirroring the Home feed layout.

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import '../styles/App.css';
import '../styles/User.css';
import '../styles/TrustTrail.css';
import '../styles/Marketplace.css';

import TrustTrail from '../components/TrustTrail';
import Marketplace from '../components/Marketplace';
import api from '../api';
import { mapTransaction, mapService } from '../utils/mappers';

function UserPage() {
    const [params] = useSearchParams();
    const id = params.get('id');

    const [user, setUser] = useState(null);
    const [trail, setTrail] = useState([]);
    const [services, setServices] = useState([]);
    const [activeTab, setActiveTab] = useState('trusttrail');
    const [loading, setLoading] = useState(true);

    const fetchAll = useCallback(async () => {
        if (!id) { setLoading(false); return; }
        try {
            const res = await api.get(`/api/users/${id}`);
            setUser(res.data);
        } catch (e) {
            console.error('Error loading user:', e);
        }
        try {
            const res = await api.post('/api/trusttrail', { userId: id });
            setTrail((res.data || []).map(mapTransaction));
        } catch (e) {
            // empty trail is fine
        }
        try {
            const res = await api.get('/api/marketplace');
            // Show only services posted by this user.
            const userServices = (res.data || [])
                .filter((s) => s.provider_id === id)
                .map(mapService);
            setServices(userServices);
        } catch (e) {
            // ignore
        } finally {
            setLoading(false);
        }
    }, [id]);

    useEffect(() => { fetchAll(); }, [fetchAll]);

    if (loading) return <div className="route-loading">Loading…</div>;
    if (!user) return (
        <div className="container">
            <main><p className="empty-state">User not found.</p></main>
        </div>
    );

    const avatar = user.profile_picture
        ? `data:image/jpeg;base64,${user.profile_picture}`
        : '/static/user-image.jpg';
    const fullName = [user.name, user.surname].filter(Boolean).join(' ');

    return (
        <div className="container">
            <aside>
                <div className="user-profile-aside">
                    <img className="user-avatar-lg" src={avatar} alt={fullName} />
                    <h2 className="user-aside-name">{fullName}</h2>
                    {user.location && (
                        <p className="user-aside-meta">📍 {user.location}</p>
                    )}
                    <div className="user-aside-stats">
                        <div className="user-stat">
                            <span className="user-stat-count">{trail.length}</span>
                            <span className="user-stat-label">trust acts</span>
                        </div>
                        <div className="user-stat">
                            <span className="user-stat-count">{services.length}</span>
                            <span className="user-stat-label">offerings</span>
                        </div>
                    </div>
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
                        className={`btn-selector ${activeTab === 'offerings' ? 'active' : ''}`}
                        onClick={() => setActiveTab('offerings')}
                    >
                        Offers &amp; Requests
                    </button>
                </div>

                {activeTab === 'trusttrail' && (
                    trail.length === 0
                        ? <p className="empty-state">No trust trail recorded yet.</p>
                        : <TrustTrail items={trail} />
                )}

                {activeTab === 'offerings' && (
                    services.length === 0
                        ? <p className="empty-state">{fullName} hasn't posted any offers or requests yet.</p>
                        : <Marketplace services={services} newServiceVisible={false} />
                )}
            </main>
        </div>
    );
}

export default UserPage;
