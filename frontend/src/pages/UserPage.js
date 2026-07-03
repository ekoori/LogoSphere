// UserPage — public profile for any user, loaded by ?id=.
// Shows their MeaningTrail as collapsible ExchangeCards and their posted
// openings offers/needs, mirroring the Home feed layout.

import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import '../styles/App.css';
import '../styles/User.css';
import '../styles/MeaningTrail.css';
import '../styles/Openings.css';

import MeaningTrail from '../components/MeaningTrail';
import Openings from '../components/Openings';
import TabSelector from '../components/TabSelector';
import ConnectionsPanel from '../components/ConnectionsPanel';
import ValueCardChip from '../components/ValueCardChip';
import api from '../api';
import { mapExchange, mapService } from '../utils/mappers';
import { useLogin } from '../App';
import '../styles/ValueCardChip.css';

function UserPage() {
    const { userId: viewerId } = useLogin();
    const [params] = useSearchParams();
    const id = params.get('id');

    const [user, setUser] = useState(null);
    const [trail, setTrail] = useState([]);
    const [services, setServices] = useState([]);
    const [valueCards, setValueCards] = useState([]);
    const [activeTab, setActiveTab] = useState('meaning_trail');
    const [loading, setLoading] = useState(true);
    const [following, setFollowing] = useState(false);

    const fetchAll = useCallback(async () => {
        if (!id) { setLoading(false); return; }
        let ownerUser = null;
        try {
            const res = await api.get(`/api/users/${id}`);
            ownerUser = res.data;
            setUser(res.data);
        } catch (e) {
            console.error('Error loading user:', e);
        }
        // "You" only makes sense when the page owner IS the logged-in viewer;
        // otherwise the trail should name the actual owner of this page.
        const isOwnPage = !!viewerId && String(viewerId) === String(id);
        const ownerFullName = ([ownerUser?.name, ownerUser?.surname].filter(Boolean).join(' ')) || 'This member';
        try {
            const res = await api.post('/api/meaning_trail', { userId: id });
            setTrail((res.data || []).map((row) => mapExchange(row, {
                ownerLabel: isOwnPage ? 'You' : ownerFullName,
                ownerId: isOwnPage ? null : id,
            })));
        } catch (e) {
            // empty trail is fine
        }
        try {
            const res = await api.get('/api/openings');
            const userServices = (res.data || [])
                .filter((s) => s.provider_id === id)
                .map(mapService);
            setServices(userServices);
        } catch (e) {
            // ignore
        }
        try {
            const vcRes = await api.get(`/api/value_cards/${id}`);
            setValueCards(vcRes.data || []);
        } catch (_) {}
        setLoading(false);
    }, [id, viewerId]);

    useEffect(() => { fetchAll(); }, [fetchAll]);
    useEffect(() => { setFollowing(!!user?.is_following); }, [user]);

    const isOwnPage = !!viewerId && String(viewerId) === String(id);
    const handleFollow = async () => {
        try {
            const res = await api.post(`/api/users/${id}/follow`);
            setFollowing(res.data.following);
        } catch (e) {
            console.error('Failed to toggle follow:', e);
        }
    };

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
                    {viewerId && !isOwnPage && (
                        <button
                            className={`follow-btn ${following ? 'is-following' : ''}`}
                            onClick={handleFollow}
                        >
                            {following ? '✓ Following' : '+ Follow'}
                        </button>
                    )}
                    {user.location && (
                        <p className="user-aside-meta">📍 {user.location}</p>
                    )}
                    {valueCards.length > 0 && (
                        <div className="user-value-chips">
                            <span className="user-value-chips-label">Values</span>
                            <div className="vc-chips-row">
                                {valueCards.map((card, i) => (
                                    <ValueCardChip key={card.card_id || i} card={card} subjectLabel="Cares about" />
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="user-aside-stats">
                        <div className="user-stat">
                            <span className="user-stat-count">{trail.length}</span>
                            <span className="user-stat-label">exchanges</span>
                        </div>
                        <div className="user-stat">
                            <span className="user-stat-count">{services.length}</span>
                            <span className="user-stat-label">openings</span>
                        </div>
                    </div>
                </div>

                <ConnectionsPanel ownerId={id} viewerId={viewerId} />
            </aside>

            <main>
                <TabSelector
                    tabs={[
                        { key: 'meaning_trail', label: 'Meaning Trail' },
                        { key: 'offerings', label: 'Offers & Needs' },
                    ]}
                    active={activeTab}
                    onChange={setActiveTab}
                />

                {activeTab === 'meaning_trail' && (
                    trail.length === 0
                        ? <p className="empty-state">No meaning trail recorded yet.</p>
                        : <MeaningTrail items={trail} />
                )}

                {activeTab === 'offerings' && (
                    services.length === 0
                        ? <p className="empty-state">{fullName} hasn't posted any offers or needs yet.</p>
                        : <Openings services={services} newServiceVisible={false} currentUserId={viewerId} />
                )}
            </main>
        </div>
    );
}

export default UserPage;
