// Near you: members who chose to be findable, and spheres, by rough distance
// from your own place. (Openings are filtered by distance on their own page.)
import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useQuery } from '@tanstack/react-query';
import api from '../api';
import Avatar from '../components/Avatar';
import { DemoTag, PersonaTag } from '../components/DemoTags';
import { NEAR_KM } from '../utils/places';
import '../styles/Places.css';

export default function NearbyPage() {
    const [km, setKm] = useState(25);
    const { data, isError, refetch } = useQuery({
        queryKey: ['nearby', km],
        queryFn: () => api.get('/api/nearby', { params: { km } }).then((r) => r.data),
    });

    return (
        <div className="near-page">
            <h1>Near you</h1>
            <p className="place-note">
                Members appear only if they chose to be findable, and only ever as a rough distance.
            </p>
            {!data && (
                <p className="place-note">
                    {isError
                        ? <>That didn&rsquo;t load. <button type="button" className="place-btn" onClick={() => refetch()}>Try again</button></>
                        : 'Looking around…'}
                </p>
            )}
            {data && !data.has_place && (
                <div className="near-empty">
                    <p>To see who and what is near you, say where you are, as roughly as you like.</p>
                    <Link className="place-btn place-btn--main" to="/settings#place">Put yourself on the map</Link>
                </div>
            )}
            {data?.has_place && (
                <>
                    <div className="near-controls">
                        <label>
                            Within
                            <select value={km} onChange={(e) => setKm(Number(e.target.value))}>
                                {NEAR_KM.map((n) => <option key={n} value={n}>{n} km</option>)}
                            </select>
                        </label>
                        <Link to="/openings?near=25">Openings near you &rarr;</Link>
                    </div>
                    {!data.findable && (
                        <p className="near-hint">
                            Others can&rsquo;t find you here. You can <Link to="/settings#place">let members nearby find you</Link>.
                        </p>
                    )}

                    <h2>People</h2>
                    {data.people.length === 0 && <p className="place-note">Nobody who chose to be findable is this near yet.</p>}
                    <ul className="near-list">
                        {data.people.map((p) => (
                            <li key={p.id}>
                                <Link className="near-row" to={`/user?id=${p.id}`}>
                                    <Avatar userId={p.id} name={p.name} size={40} />
                                    <span className="near-who">
                                        <strong>{p.name}</strong>{p.is_agent && <PersonaTag compact />}
                                        {p.location && <small>{p.location}</small>}
                                    </span>
                                    <span className="where-distance">{p.distance.text}</span>
                                </Link>
                            </li>
                        ))}
                    </ul>

                    <h2>Spheres</h2>
                    {data.spheres.length === 0 && <p className="place-note">No sphere this near has said where it is.</p>}
                    <ul className="near-list">
                        {data.spheres.map((s) => (
                            <li key={s.id}>
                                <Link className="near-row" to={`/sphere?id=${s.id}`}>
                                    <span className="near-glyph" aria-hidden="true">✦</span>
                                    <span className="near-who">
                                        <strong>{s.name}</strong>{s.is_demo && <DemoTag />}
                                        <small>
                                            {[s.location, `${s.member_count} member${s.member_count === 1 ? '' : 's'}`, s.is_member && 'you’re in it']
                                                .filter(Boolean).join(' · ')}
                                        </small>
                                    </span>
                                    <span className="where-distance">{s.distance.text}</span>
                                </Link>
                            </li>
                        ))}
                    </ul>
                </>
            )}
        </div>
    );
}
