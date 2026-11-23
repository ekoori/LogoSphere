// OpeningsPage — offers & needs, a page at a time: the server filters and pages
// (GET /api/openings?limit=…, app/utils/openings_feed.py), and the next page comes
// as the list nears its end.
import React, { useState, useEffect, useMemo, useRef } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import '../styles/App.css';
import '../styles/Openings.css';

import Openings from '../components/Openings';
import api from '../api';
import { mapService } from '../utils/mappers';
import { useLogin } from '../App';
import { NEAR_KM, canMeasure } from '../utils/places';
import { openingsOf, openingsQuery } from '../utils/openingsQuery';
import '../styles/Places.css';

/** `value`, once it has stopped changing for `ms`. */
function useSettled(value, ms = 300) {
    const [settled, setSettled] = useState(value);
    useEffect(() => {
        const t = setTimeout(() => setSettled(value), ms);
        return () => clearTimeout(t);
    }, [value, ms]);
    return settled;
}

function OpeningsPage() {
    const { userId } = useLogin();
    const [searchParams] = useSearchParams();
    const [isFormVisible, setIsFormVisible] = useState(searchParams.get('new') === '1');
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

    const words = useSettled(query);
    const params = useMemo(() => openingsQuery({ filter, sphereFilter, near, q: words }),
        [filter, sphereFilter, near, words]);
    const list = useInfiniteQuery({
        queryKey: ['openings', 'page', params],
        queryFn: ({ pageParam }) => api.get('/api/openings', { params: { ...params, ...(pageParam && { before: pageParam }) } })
            .then((r) => r.data),
        initialPageParam: null,
        getNextPageParam: (last) => last.next || undefined,
        enabled: !!userId,
        staleTime: 15_000,
    });
    const services = useMemo(() => openingsOf(list.data?.pages).map(mapService), [list.data]);

    // The next page, as the end of the list comes into view.
    const end = useRef(null);
    const { hasNextPage, isFetchingNextPage, fetchNextPage } = list;
    useEffect(() => {
        const node = end.current;
        if (!node || !hasNextPage) return undefined;
        const watch = new IntersectionObserver((seen) => {
            if (seen.some((e) => e.isIntersecting) && !isFetchingNextPage) fetchNextPage();
        }, { rootMargin: '600px 0px' });
        watch.observe(node);
        return () => watch.disconnect();
    }, [hasNextPage, isFetchingNextPage, fetchNextPage, services.length]);

    useEffect(() => {
        api.get('/api/spheres').then((r) => setSpheres(r.data || [])).catch(() => {});
    }, []);

    const toggleFormVisibility = () => setIsFormVisible((v) => !v);
    const filtered = !!words.trim() || filter !== 'all' || sphereFilter !== 'all' || near > 0;

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
                    <button className={filter === 'loans' ? 'active' : ''} onClick={() => setFilter('loans')}>To lend or borrow</button>
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
                    <p className="place-note">Newest first. Openings that haven&rsquo;t said where they are, and whose sphere hasn&rsquo;t, are left out.</p>
                )}
                <Link className="near-link" to="/nearby">Who and what is near you &rarr;</Link>
            </aside>
            <main>
                {/* With nothing listed the form still has to open: it's how the first gets posted. */}
                {services.length === 0 && !isFormVisible ? (
                    <p className="empty-state">
                        {list.isPending
                            ? 'Loading…'
                            : list.isError
                                ? 'The openings didn’t load. Please try again.'
                                : noPlace || list.data?.pages?.[0]?.no_place
                                    ? <>To see what&rsquo;s near you, first <Link to="/settings#place">say where you are</Link>, as roughly as a town.</>
                                    : filtered
                                        ? 'Nothing matches these filters.'
                                        : 'No offers or needs yet. Share something with your community.'}
                    </p>
                ) : (
                    <Openings services={services} newServiceVisible={isFormVisible} onServiceAdded={() => list.refetch()} currentUserId={userId} />
                )}
                <div ref={end} aria-hidden="true" />
                {hasNextPage && (
                    <button type="button" className="openings-more" onClick={() => fetchNextPage()} disabled={isFetchingNextPage}>
                        {isFetchingNextPage ? 'Loading more…' : 'Show more'}
                    </button>
                )}
            </main>
        </div>
    );
}

export default OpeningsPage;
