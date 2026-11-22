// Home — landing feed: the logged-in user's MeaningTrail and the openings.
// Both fetched live from the API; 401 means "not logged in" and shows empty state.

import React, { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import '../styles/MeaningTrail.css';
import '../styles/Openings.css';

import TrailView from '../components/TrailView';
import Openings from '../components/Openings';
import TabSelector from '../components/TabSelector';
import ConnectionsPanel from '../components/ConnectionsPanel';
import Avatar from '../components/Avatar';
import DemoInvite from '../components/DemoInvite';
import api from '../api';
import { mapService } from '../utils/mappers';
import { useLogin } from '../App';
import { OPENINGS_TAB, TRAIL_TAB, tabFrom } from '../utils/tabs';

function Home() {
    const { userId } = useLogin();
    const [params] = useSearchParams();
    const tabParam = params.get('tab');
    const [activeTab, setActiveTab] = useState(() => tabFrom(tabParam, [TRAIL_TAB, OPENINGS_TAB, 'following']));
    const [isFormVisible, setIsFormVisible] = useState(false);
    const [services, setServices] = useState([]);
    const [following, setFollowing] = useState([]);

    const fetchFeed = useCallback(async () => {
        try {
            const fr = await api.get('/api/following');
            setFollowing(fr.data || []);
        } catch (e) {
            // not logged in / none followed
        }
        try {
            const res = await api.get('/api/openings');
            // The home feed is personal — only the logged-in user's own postings,
            // not the whole visible marketplace (that's what /openings is for).
            setServices((res.data || [])
                .filter((s) => s.provider_id === userId)
                .map(mapService));
        } catch (e) {
            if (e.response?.status !== 401) console.error('Error fetching openings:', e);
        }
    }, [userId]);

    useEffect(() => {
        fetchFeed();
    }, [fetchFeed]);

    return (
        <div className="container">
            <aside>
                <h3>Openings</h3>
                <button className="btn-orange" onClick={() => { setIsFormVisible((v) => !v); setActiveTab(OPENINGS_TAB); }}>
                    {isFormVisible ? 'Hide New Opening Form' : 'New Opening'}
                </button>
                <ConnectionsPanel ownerId={userId} viewerId={userId} />
            </aside>
            <main>
                <DemoInvite onJoined={fetchFeed} />
                <TabSelector
                    tabs={[
                        { key: 'meaning_trail', label: 'Meaning Trail' },
                        { key: 'offers-needs', label: 'Offers / Needs' },
                        { key: 'following', label: `Following (${following.length})` },
                    ]}
                    active={activeTab}
                    onChange={setActiveTab}
                />

                {activeTab === 'meaning_trail' && (
                    userId
                        ? <TrailView trailId={userId} empty="Your Meaning Trail is empty. Give a little — help a neighbour, share a skill — and your trail of trust will grow here." />
                        : <p className="empty-state"><Link to="/login">Log in</Link> to see your Meaning Trail.</p>
                )}
                {activeTab === 'offers-needs' && services.length === 0 && !isFormVisible && (
                    <p className="empty-state">
                        {userId
                            ? <>You haven't posted an offer or a need yet. Press New Opening to share something, or <Link to="/openings">see what others have posted</Link>.</>
                            : <><Link to="/login">Log in</Link> to post offers and needs, or read <Link to="/how-it-works">how it works</Link>.</>}
                    </p>
                )}
                {activeTab === 'offers-needs' && (
                    <Openings services={services} newServiceVisible={isFormVisible} onServiceAdded={fetchFeed} currentUserId={userId} />
                )}
                {activeTab === 'following' && (
                    following.length === 0
                        ? <p className="empty-state">You're not following anyone yet. Open a member's profile and hit Follow to see them here.</p>
                        : (
                            <div className="following-list">
                                {following.map((f) => (
                                    <Link key={f.id} to={`/user?id=${f.id}`} className="following-row">
                                        <Avatar userId={f.id} name={f.name} size={40} />
                                        <span className="following-name">{f.name}</span>
                                    </Link>
                                ))}
                            </div>
                        )
                )}
            </main>
        </div>
    );
}

export default Home;
