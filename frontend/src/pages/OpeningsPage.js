// OpeningsPage — the full openings of offers & needs, fetched live.
import React, { useState, useEffect, useCallback } from 'react';
import { useSearchParams } from 'react-router-dom';
import '../styles/App.css';
import '../styles/Openings.css';

import Openings from '../components/Openings';
import api from '../api';
import { mapService } from '../utils/mappers';
import { useLogin } from '../App';

function OpeningsPage() {
    const { userId } = useLogin();
    const [searchParams] = useSearchParams();
    const [isFormVisible, setIsFormVisible] = useState(searchParams.get('new') === '1');
    const [services, setServices] = useState([]);
    const [spheres, setSpheres] = useState([]);
    const [filter, setFilter] = useState('all');
    const [sphereFilter, setSphereFilter] = useState('all');
    const [query, setQuery] = useState('');

    const toggleFormVisibility = () => setIsFormVisible((v) => !v);

    const fetchServices = useCallback(async () => {
        try {
            const res = await api.get('/api/openings');
            setServices((res.data || []).map(mapService));
        } catch (e) {
            console.error('Error fetching openings:', e);
        }
    }, []);

    useEffect(() => {
        fetchServices();
        api.get('/api/spheres').then((r) => setSpheres(r.data || [])).catch(() => {});
    }, [fetchServices]);

    const q = query.trim().toLowerCase();
    const bySphere = (s) => {
        if (sphereFilter === 'all') return true;
        if (sphereFilter === 'real') return !s.isDemo;
        if (sphereFilter === 'demo') return s.isDemo;
        return s.spheres.some((sp) => sp.id === sphereFilter);
    };
    const shown = services
        .filter((s) => filter === 'all' ? true : filter === 'offers' ? s.type === 'offer' : s.type === 'need')
        .filter(bySphere)
        .filter((s) => !q || [s.title, s.description, s.provider, s.actingUser, s.project]
            .some((f) => (f || '').toLowerCase().includes(q)));

    return (
        <div className="container">
            <aside>
                <button className="btn-orange" onClick={toggleFormVisibility}>
                    {isFormVisible ? 'Hide New Opening Form' : 'New Opening'}
                </button>
                <div className="search-box">
                    <input
                        type="search"
                        placeholder="Search openings…"
                        value={query}
                        onChange={(e) => setQuery(e.target.value)}
                        aria-label="Search openings"
                    />
                </div>
                <div className="filters">
                    <button className={filter === 'all' ? 'active' : ''} onClick={() => setFilter('all')}>Show All</button>
                    <button className={filter === 'offers' ? 'active' : ''} onClick={() => setFilter('offers')}>Offers</button>
                    <button className={filter === 'needs' ? 'active' : ''} onClick={() => setFilter('needs')}>Needs</button>
                </div>
                <div className="opening-sphere-filter">
                    <label htmlFor="opening-sphere-select">Sphere</label>
                    <select
                        id="opening-sphere-select"
                        value={sphereFilter}
                        onChange={(e) => setSphereFilter(e.target.value)}
                    >
                        <option value="all">All spheres</option>
                        <option value="real">Real spheres only</option>
                        <option value="demo">Demo spheres only</option>
                        {spheres.filter((s) => !s.is_demo).map((s) => (
                            <option key={s.sphere_id} value={s.sphere_id}>{s.name}</option>
                        ))}
                        {spheres.some((s) => s.is_demo) && (
                            <optgroup label="Demo spheres">
                                {spheres.filter((s) => s.is_demo).map((s) => (
                                    <option key={s.sphere_id} value={s.sphere_id}>{s.name}</option>
                                ))}
                            </optgroup>
                        )}
                    </select>
                </div>
            </aside>
            <main>
                {/* With nothing listed the form still has to open: it's how the first gets posted. */}
                {shown.length === 0 && !isFormVisible ? (
                    <p className="empty-state">
                        {q || filter !== 'all' || sphereFilter !== 'all'
                            ? 'Nothing matches these filters.'
                            : 'No offers or needs yet. Share something with your community.'}
                    </p>
                ) : (
                    <Openings services={shown} newServiceVisible={isFormVisible} onServiceAdded={fetchServices} currentUserId={userId} />
                )}
            </main>
        </div>
    );
}

export default OpeningsPage;
