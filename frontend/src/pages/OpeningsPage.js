// OpeningsPage — the full openings of offers & needs, fetched live.
import React, { useState, useEffect, useCallback } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import '../styles/App.css';
import '../styles/Openings.css';

import Openings from '../components/Openings';
import api from '../api';
import { mapService } from '../utils/mappers';
import { useLogin } from '../App';
import { NEAR_KM, canMeasure } from '../utils/places';
import '../styles/Places.css';

function OpeningsPage() {
    const { userId } = useLogin();
    const [searchParams] = useSearchParams();
    const [isFormVisible, setIsFormVisible] = useState(searchParams.get('new') === '1');
    const [services, setServices] = useState([]);
    const [spheres, setSpheres] = useState([]);
    const [filter, setFilter] = useState('all');
    const [sphereFilter, setSphereFilter] = useState('all');
    const [query, setQuery] = useState('');
    const [near, setNear] = useState(() => {        // km from your place; 0 is anywhere
        const asked = Number(searchParams.get('near'));
        return NEAR_KM.includes(asked) ? asked : 0;
    });
    const mine = useQuery({
        queryKey: ['my-place', userId],
        queryFn: () => api.get(`/api/places/users/${userId}`).then((r) => r.data),
        enabled: !!userId && near > 0,
    });
    const noPlace = near > 0 && !!mine.data && !canMeasure(mine.data.place);

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
        .filter((s) => !near || (!!s.distance && s.distance.km <= near))
        .filter((s) => !q || [s.title, s.description, s.provider, s.actingUser, s.project, s.location]
            .some((f) => (f || '').toLowerCase().includes(q)));
    // Nearest band first, each still in the order it came.
    if (near) shown.sort((a, b) => a.distance.km - b.distance.km);

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
                <div className="opening-sphere-filter">
                    <label htmlFor="opening-distance-select">Distance</label>
                    <select id="opening-distance-select" value={near} onChange={(e) => setNear(Number(e.target.value))}>
                        <option value={0}>Anywhere</option>
                        {NEAR_KM.map((km) => <option key={km} value={km}>Within {km} km of you</option>)}
                    </select>
                </div>
                {near > 0 && !noPlace && (
                    <p className="place-note">Nearest first. Openings that haven&rsquo;t said where they are, and whose sphere hasn&rsquo;t, are left out.</p>
                )}
                <Link className="near-link" to="/nearby">Who and what is near you &rarr;</Link>
            </aside>
            <main>
                {/* With nothing listed the form still has to open: it's how the first gets posted. */}
                {shown.length === 0 && !isFormVisible ? (
                    <p className="empty-state">
                        {noPlace
                            ? <>To see what&rsquo;s near you, first <Link to="/settings#place">say where you are</Link>, as roughly as a town.</>
                            : q || filter !== 'all' || sphereFilter !== 'all' || near
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
