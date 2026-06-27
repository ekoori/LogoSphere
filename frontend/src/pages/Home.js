// ./frontend/src/pages/Home.js
// Landing feed: the logged-in user's TrustTrail and the marketplace of
// offers/requests, both fetched live from the API.

import React, { useState, useEffect, useCallback } from 'react';
import '../styles/TrustTrail.css';
import '../styles/Marketplace.css';

import TrustTrail from '../components/TrustTrail';
import Marketplace from '../components/Marketplace';
import api from '../api';
import { mapService } from '../utils/mappers';

// Format an RFC-1123 / ISO datetime into a short readable date.
function fmtDate(value) {
    if (!value) return 'recently';
    const d = new Date(value);
    if (isNaN(d.getTime())) return 'recently';
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' });
}

// Pick a fitting illustration from the bundled static assets.
function imageFor(text = '') {
    const t = text.toLowerCase();
    if (t.includes('fence') || t.includes('garden')) return '/static/garden_old.webp';
    if (t.includes('gpu') || t.includes('h100') || t.includes('compute')) return '/static/h100_cpus.webp';
    if (t.includes('podcast') || t.includes('workshop') || t.includes('class')) return '/static/yoga_classes.webp';
    if (t.includes('solar') || t.includes('microgrid') || t.includes('energy')) return '/static/projects_spheres.png';
    return null;
}

// Map a flat TrustTrail row from the API into a TransactionCard item.
function mapTransaction(row) {
    const completed = ['Finished', 'Completed', 'Trustifacted', 'Additional Comments Added']
        .includes(row.transaction_status);

    const trustifacts = [];
    if (row.gratitude_comment) {
        trustifacts.push({
            author: row.other_user_name || 'A neighbour',
            text: row.gratitude_comment,
            time: fmtDate(row.gratitude_comment_timestamp),
            likesCount: 0, likedByCurrentUser: false, imageUrl: null,
        });
    }
    if (row.user_comment) {
        trustifacts.push({
            author: 'You',
            text: row.user_comment,
            time: fmtDate(row.user_comment_timestamp),
            likesCount: 0, likedByCurrentUser: false, imageUrl: null,
        });
    }

    const shoutouts = [];
    if (row.other_comment) {
        shoutouts.push({
            author: row.other_comment_author_name || 'A neighbour',
            text: row.other_comment,
            time: fmtDate(row.other_comment_timestamp),
            likesCount: 0, likedByCurrentUser: false,
        });
    }

    return {
        id: row.transaction_id,
        type: completed ? 'completed' : 'offer',
        title: row.transaction_description || 'An exchange of trust',
        spheres: row.project_name ? [row.project_name] : [],
        // {id, name} pairs so the other party links to their profile.
        participants: [
            { name: 'You', id: null },
            ...(row.other_user_name ? [{ name: row.other_user_name, id: row.other_user_id }] : []),
        ],
        description: row.project_name
            ? `An act of giving within the "${row.project_name}" project.`
            : 'A moment of trust shared in the community.',
        project: row.project_name || 'Unassigned',
        imageUrl: imageFor(row.transaction_description),
        time: fmtDate(row.project_start_timestamp),
        status: row.transaction_status,
        likesCount: 0,
        likedByCurrentUser: false,
        initiatedTime: fmtDate(row.project_start_timestamp),
        inProgressTime: '', finishedTime: '', trustifactedTime: '', additionalCommentsTime: '',
        trustifacts,
        shoutouts,
        canModify: false,
        onAddTrustifact: () => {},
        onAddShoutout: () => {},
        onModifyTransaction: () => {},
    };
}

function Home() {
    const [activeTab, setActiveTab] = useState('trusttrail');
    const [isFormVisible, setIsFormVisible] = useState(false);
    const [items, setItems] = useState([]);
    const [services, setServices] = useState([]);

    const toggleTab = (tab) => setActiveTab(tab);
    const toggleFormVisibility = () => setIsFormVisible((v) => !v);

    const fetchFeed = useCallback(async () => {
        // A 401 just means "not logged in" — the feed shows its empty state then.
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
                <button className="btn-orange" onClick={toggleFormVisibility}>
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
                    <button className={`btn-selector ${activeTab === 'trusttrail' ? 'active' : ''}`} onClick={() => toggleTab('trusttrail')}>TrustTrail</button>
                    <button className={`btn-selector ${activeTab === 'offers-requests' ? 'active' : ''}`} onClick={() => toggleTab('offers-requests')}>Offers/Requests</button>
                </div>
                {activeTab === 'trusttrail' && (
                    items.length === 0
                        ? <p className="empty-state">Your TrustTrail is empty. Give a little — help a neighbour, share a skill — and your trail of trust will grow here.</p>
                        : <TrustTrail items={items} />
                )}
                {activeTab === 'offers-requests' && <Marketplace services={services} newServiceVisible={isFormVisible} />}
            </main>
        </div>
    );
}

export default Home;
