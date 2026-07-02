// Home — landing feed: the logged-in user's MeaningTrail and the openings.
// Both fetched live from the API; 401 means "not logged in" and shows empty state.

import React, { useState, useEffect, useCallback } from 'react';
import '../styles/MeaningTrail.css';
import '../styles/Openings.css';

import MeaningTrail from '../components/MeaningTrail';
import Openings from '../components/Openings';
import TabSelector from '../components/TabSelector';
import ConnectionsPanel from '../components/ConnectionsPanel';
import api from '../api';
import { mapService, mapExchange } from '../utils/mappers';
import { useLogin } from '../App';

function Home() {
    const { userId } = useLogin();
    const [activeTab, setActiveTab] = useState('meaning_trail');
    const [isFormVisible, setIsFormVisible] = useState(false);
    const [items, setItems] = useState([]);
    const [services, setServices] = useState([]);

    const fetchFeed = useCallback(async () => {
        try {
            const res = await api.get('/api/meaning_trail');
            setItems((res.data || []).map(row => {
                const mapped = mapExchange(row);
                // On the home feed the viewer is always the initiator, so:
                //   "Add Receipt" → personal note (type: user)
                //   "Add Acknowledgement" → public shoutout (type: other)
                return {
                    ...mapped,
                    canModify: true,
                    onAddReceipt: async ({ text, cardIds, cards }) => {
                        try {
                            await api.post(`/api/exchange/${mapped.id}/comment`, {
                                type: 'user', text, card_ids: cardIds || [], cards: cards || [],
                            });
                        } catch (e) {
                            console.error('Failed to save note:', e);
                        }
                    },
                    onAddAcknowledgement: async ({ text, cardIds, cards }) => {
                        try {
                            await api.post(`/api/exchange/${mapped.id}/comment`, {
                                type: 'other', text, card_ids: cardIds || [], cards: cards || [],
                            });
                        } catch (e) {
                            console.error('Failed to save acknowledgement:', e);
                        }
                    },
                };
            }));
        } catch (e) {
            if (e.response?.status !== 401) console.error('Error fetching meaning_trail:', e);
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
                <button className="btn-orange" onClick={() => setIsFormVisible((v) => !v)}>
                    {isFormVisible ? 'Hide New Opening Form' : 'New Opening'}
                </button>
                <h3>Meaning Trail</h3>
                <div className="filters">
                    <button>Show All</button>
                    <button>Only Active</button>
                    <button>Only Past</button>
                    <button>Only Acknowledgements</button>
                    <button>Only Receipts</button>
                </div>
                <ConnectionsPanel ownerId={userId} viewerId={userId} />
            </aside>
            <main>
                <TabSelector
                    tabs={[
                        { key: 'meaning_trail', label: 'Meaning Trail' },
                        { key: 'offers-needs', label: 'Offers / Needs' },
                    ]}
                    active={activeTab}
                    onChange={setActiveTab}
                />

                {activeTab === 'meaning_trail' && (
                    items.length === 0
                        ? <p className="empty-state">Your Meaning Trail is empty. Give a little — help a neighbour, share a skill — and your trail of trust will grow here.</p>
                        : <MeaningTrail items={items} />
                )}
                {activeTab === 'offers-needs' && (
                    <Openings services={services} newServiceVisible={isFormVisible} onServiceAdded={fetchFeed} currentUserId={userId} />
                )}
            </main>
        </div>
    );
}

export default Home;
