import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import '../styles/TrustTrail.css';
import '../styles/Marketplace.css';
import '../styles/SpherePage.css';

import TrustTrail from '../components/TrustTrail';
import Marketplace from '../components/Marketplace';
import SphereCard from '../components/SphereCard';
import api from '../api';
import { useLogin } from '../App';

function SpherePage() {
    const { isLoggedIn } = useLogin();
    const [activeTab, setActiveTab] = useState('trusttrail');
    const [isFormVisible, setIsFormVisible] = useState(false);
    const [spheres, setSpheres] = useState([]);
    const navigate = useNavigate();

    useEffect(() => {
        if (!isLoggedIn) {
            navigate('/login', { replace: true });
        }
    }, [isLoggedIn, navigate]);

    const toggleTab = (tab) => {
        setActiveTab(tab);
    };

    const toggleFormVisibility = () => {
        setIsFormVisible(!isFormVisible);
    };

    const fetchSpheres = useCallback(async () => {
        try {
            const response = await api.get('/api/spheres', {
                withCredentials: true,
            });

            if (response.data) {
                const fetchedSpheres = response.data.map((sphere) => ({
                    ...sphere,
                    id: sphere.sphere_id,
                    unions: sphere.unions ? sphere.unions.slice(0, 5) : [],
                    participants: sphere.participants ? sphere.participants.slice(0, 5) : [],
                    projects: sphere.projects ? sphere.projects.slice(0, 5) : [],
                    values: sphere.values ? sphere.values.slice(0, 5) : [],
                }));
                setSpheres(fetchedSpheres);
            }
        } catch (error) {
            console.error('Error fetching spheres:', error);
        }
    }, []);

    useEffect(() => {
        fetchSpheres();
    }, [fetchSpheres]);

    const sphere = {
        title: 'AI Development Sphere',
        description: 'The AI Development Sphere is dedicated to advancing artificial intelligence technologies and fostering collaboration among AI researchers and developers.',
        ownerUnion: 'AI Australia Sphere',
        leaders: ['John Doe', 'Jane Smith']
    };

    const transactions = [
        {
            id: 'transaction-cpus',
            type: 'offer',
            spheres: ['OpenAI Sphere'],
            title: 'Requesting 7 H100 CPUs for OpenAI datacentre from Jansen Huang',
            participants: ['You', 'Jansen Huang'],
            description: 'This transaction involves requesting 7 H100 CPUs for the OpenAI datacentre. The request was initiated by Sam and is awaiting a response from Jansen Huang.',
            project: 'OpenAI Datacentre Upgrades',
            imageUrl: 'static/h100_cpus.webp',
            time: '30 min ago',
            status: 'Initiated',
            likesCount: 0,
            likedByCurrentUser: false,
            originService: '🔍 Requesting 7 H100 CPUs',
            initiatedTime: '30 min ago',
            inProgressTime: '',
            finishedTime: '',
            trustifactedTime: '',
            additionalCommentsTime: '',
            trustifacts: [],
            shoutouts: [],
            canModify: true,
            onAddTrustifact: () => console.log('Add Trustifact'),
            onAddShoutout: () => console.log('Add Shoutout'),
            onModifyTransaction: () => console.log('Modify Transaction')
        },
        {
            id: 'transaction-server-rack',
            type: 'request',
            spheres: ['OpenAI Sphere'],
            title: 'Designing and building a server rack in OpenAI datacentre with Ilya S',
            participants: ['Ilya S', 'You'],
            description: 'This transaction involves the design and construction of a new server rack in the OpenAI datacentre. Ilya S, the project manager for the datacentre upgrade, initiated the transaction.',
            project: 'Project not assigned',
            imageUrl: '',
            time: '1h ago',
            status: 'Requested',
            likesCount: 0,
            likedByCurrentUser: false,
            originService: '🔍 Offering Tesla Roadster Ride',
            initiatedTime: '1h ago',
            inProgressTime: '',
            finishedTime: '',
            trustifactedTime: '',
            additionalCommentsTime: '',
            trustifacts: [],
            shoutouts: [],
            canModify: true,
            onAddTrustifact: () => console.log('Add Trustifact'),
            onAddShoutout: () => console.log('Add Shoutout'),
            onModifyTransaction: () => console.log('Modify Transaction')
        },
        {
            id: 'transaction-garden-fences',
            type: 'completed',
            spheres: ['Community Garden Sphere'],
            title: 'Rebuilding fence on the garden with Jane Doe',
            participants: ['You', 'Jane Doe'],
            description: 'This transaction involved the replacement of the garden fence. I designed and installed the new fence, while Jane, the project manager for the Community Garden, coordinated the efforts and managed the project timeline.',
            project: 'Service: Offering Tesla Roadster Ride',
            imageUrl: 'static/garden_old.webp',
            time: '15 min ago',
            status: 'Initiated',
            likesCount: 10,
            likedByCurrentUser: true,
            originService: '🔍 Building Garden Fences',
            initiatedTime: '7d ago',
            inProgressTime: '5d ago',
            finishedTime: '3d ago',
            trustifactedTime: '2d ago',
            additionalCommentsTime: '15 min ago',
            trustifacts: [
                {
                    author: 'Jane Doe',
                    text: 'Working with Sam on the garden fence project was a fantastic experience...',
                    time: '1d ago',
                    likesCount: 3,
                    likedByCurrentUser: true,
                    imageUrl: null
                },
                {
                    author: 'You',
                    text: 'Jane\'s project management skills were top-notch...',
                    time: '12h ago',
                    likesCount: 5,
                    likedByCurrentUser: true,
                    imageUrl: 'static/garden_new.webp'
                }
            ],
            shoutouts: [
                {
                    author: 'Emily Johnson',
                    text: 'The new fence looks amazing! Great job, both of you!',
                    time: '30 min ago',
                    likesCount: 0,
                    likedByCurrentUser: false
                }
            ],
            canModify: false,
            onAddTrustifact: () => console.log('Add Trustifact'),
            onAddShoutout: () => console.log('Add Shoutout'),
            onModifyTransaction: () => console.log('Modify Transaction')
        }
    ];

    const services = [
        {
            id: 'service-ai-consulting',
            type: 'offer',
            spheres: ['AI Development Sphere'],
            title: 'Offering AI Consulting Services',
            provider: 'Elon Musk',
            description: 'Elon is offering his expertise in AI consulting to help innovative projects reach their full potential. His deep knowledge and experience in AI development can provide valuable insights and guidance for your next big project.',
            project: 'Project not assigned',
            imageUrl: 'static/garden_old.webp',
            time: '2d ago',
            status: 'Posted',
            likesCount: 20,
            likedByCurrentUser: false,
            relatedTransactions: ['Requesting 7 H100 CPUs - involving Jansen Huang - Initiated 30 min ago'],
            canModify: true
        },
        {
            id: 'service-garden-fences',
            type: 'offer',
            spheres: ['Community Garden Sphere'],
            title: 'Building garden fences',
            provider: 'Sam',
            description: 'I am offering my services to build garden fences. With extensive experience in carpentry and landscaping, I can provide sturdy and aesthetically pleasing fences for your garden.',
            project: 'Project not assigned',
            imageUrl: '',
            time: '15 min ago',
            status: 'Posted',
            likesCount: 10,
            likedByCurrentUser: false,
            relatedTransactions: ['Rebuilding fence on the garden - involving Jane Doe - Initiated 15 min ago'],
            canModify: true
        }
    ];

    

    return (
        <div className="container">
            <aside>
                <h1>{sphere.title}</h1>
                <p className="sphere-description">{sphere.description}</p>
                <h2>Owner Union</h2>
                <p><a href="/union">{sphere.ownerUnion}</a></p>
                <h2>Sphere Leaders</h2>
                <ul className="leaders-list">
                    {sphere.leaders.map((leader, index) => (
                        <li key={index}><a href="/user">{leader}</a></li>
                    ))}
                </ul>
                <button className="btn-orange" onClick={toggleFormVisibility}>
                    {isFormVisible ? 'Hide New Service Form' : 'New Service'}
                </button>
                <a href="/sphere-management" className="btn-orange">Manage Sphere</a>
            </aside>
            <main>
                <div className="selector-buttons">
                    <button className={`btn-selector ${activeTab === 'trusttrail' ? 'active' : ''}`} onClick={() => toggleTab('trusttrail')}>TrustTrail</button>
                    <button className={`btn-selector ${activeTab === 'offers-requests' ? 'active' : ''}`} onClick={() => toggleTab('offers-requests')}>Offers/Requests</button>
                </div>

                {activeTab === 'trusttrail' && <TrustTrail items={transactions} />}
                {activeTab === 'offers-requests' && <Marketplace services={services} newServiceVisible={isFormVisible} />}
                
                <div className="sphere-list">
                    {spheres.map((sphere) => (
                        <SphereCard key={sphere.id} {...sphere} onJoin={(id) => console.log(`Joining sphere ${id}`)} />
                    ))}
                </div>
            </main>
        </div>
    );
}

export default SpherePage;
