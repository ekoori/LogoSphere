// UserPage — public profile for any user, loaded by ?id=.
// Shows their MeaningTrail as collapsible ExchangeCards and their posted
// openings offers/needs, mirroring the Home feed layout.

import React, { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import '../styles/App.css';
import '../styles/User.css';
import '../styles/MeaningTrail.css';
import '../styles/Openings.css';

import TrailView from '../components/TrailView';
import { useTrail } from '../utils/queries';
import Openings from '../components/Openings';
import TabSelector from '../components/TabSelector';
import ConnectionsPanel from '../components/ConnectionsPanel';
import ValueCardChip from '../components/ValueCardChip';
import api from '../api';
import { mapService } from '../utils/mappers';
import { useLogin } from '../App';
import { OPENINGS_TAB, TRAIL_TAB, tabFrom } from '../utils/tabs';
import '../styles/ValueCardChip.css';
import { PersonaTag } from '../components/DemoTags';
import { BlockButton, ReportButton } from '../components/Safety';
import { messagesHref } from '../utils/thread';

function UserPage() {
    const { userId: viewerId } = useLogin();
    const [params] = useSearchParams();
    const id = params.get('id');

    const [user, setUser] = useState(null);
    const { data: trail } = useTrail(id, { enabled: !!viewerId });
    const exchangeCount = (trail?.entries || []).filter((e) => e.type === 'exchange').length;
    const [services, setServices] = useState([]);
    const [valueCards, setValueCards] = useState([]);
    const tabParam = params.get('tab');
    const [activeTab, setActiveTab] = useState(() => tabFrom(tabParam, [TRAIL_TAB, OPENINGS_TAB]));
    // Going to another person, or following a link that names a tab, starts afresh.
    useEffect(() => { setActiveTab(tabFrom(tabParam, [TRAIL_TAB, OPENINGS_TAB])); }, [id, tabParam]);
    const [loading, setLoading] = useState(true);
    const [following, setFollowing] = useState(false);

    const fetchAll = useCallback(async () => {
        if (!id) { setLoading(false); return; }
        try {
            const res = await api.get(`/api/users/${id}`);
            setUser(res.data);
        } catch (e) {
            console.error('Error loading user:', e);
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
    }, [id]);

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

    // Served by the avatar endpoint (a photo, or generated initials).
    const avatar = `/api/users/${user.user_id}/avatar`;
    const fullName = [user.name, user.surname].filter(Boolean).join(' ');

    return (
        <div className="container">
            <aside>
                <div className="user-profile-aside">
                    <img className="user-avatar-lg" src={avatar} alt={fullName} />
                    <h2 className="user-aside-name">{fullName}</h2>
                    {user.is_agent && (
                        <p className="user-persona-note">
                            <PersonaTag /> A famous name playing an everyday neighbour in the demo spheres.
                            Their posts are written by AI.
                        </p>
                    )}
                    {viewerId && !isOwnPage && (
                        <button
                            className={`follow-btn ${following ? 'is-following' : ''}`}
                            onClick={handleFollow}
                        >
                            {following ? '✓ Following' : '+ Follow'}
                        </button>
                    )}
                    {viewerId && !isOwnPage && user.can_message && (
                        <Link className="msg-link" to={messagesHref(id)}>Message</Link>
                    )}
                    {viewerId && !isOwnPage && (
                        <div className="safe-profile">
                            <BlockButton personId={id} blocked={!!user.blocked} onChanged={fetchAll} />
                            <ReportButton report={{ kind: 'person', id }} noteRequired />
                        </div>
                    )}
                    {user.location && (
                        <p className="user-aside-meta">📍 {user.location}</p>
                    )}
                    {valueCards.length > 0 && (
                        <div className="user-value-chips">
                            <span className="user-value-chips-label">Values</span>
                            <Link to={`/meaning-graph?owner=${id}`}>See them in the Meaning Graph →</Link>
                            <div className="vc-chips-row">
                                {valueCards.map((card, i) => (
                                    <ValueCardChip key={card.card_id || i} card={card} subjectLabel="Cares about" currentUserId={viewerId} />
                                ))}
                            </div>
                        </div>
                    )}

                    <div className="user-aside-stats">
                        <div className="user-stat">
                            <span className="user-stat-count">{exchangeCount}</span>
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
                        { key: OPENINGS_TAB, label: 'Offers & Needs' },
                    ]}
                    active={activeTab}
                    onChange={setActiveTab}
                />

                {activeTab === 'meaning_trail' && (
                    <TrailView key={id} trailId={id} empty="No meaning trail recorded yet." />
                )}

                {activeTab === OPENINGS_TAB && (
                    services.length === 0
                        ? <p className="empty-state">{fullName} hasn't posted any offers or needs yet.</p>
                        : <Openings services={services} newServiceVisible={false} currentUserId={viewerId} />
                )}
            </main>
        </div>
    );
}

export default UserPage;
