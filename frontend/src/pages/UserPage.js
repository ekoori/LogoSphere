// UserPage — shows a user's public profile and TrustTrail, loaded by ?id=.
import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import '../styles/User.css';
import api from '../api';

function UserPage() {
    const [params] = useSearchParams();
    const id = params.get('id');
    const [user, setUser] = useState(null);
    const [trail, setTrail] = useState([]);
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let active = true;
        (async () => {
            if (!id) { setLoading(false); return; }
            try {
                const res = await api.get(`/api/users/${id}`);
                if (active) setUser(res.data);
            } catch (e) {
                console.error('Error loading user:', e);
            }
            try {
                // The TrustTrail of the user being viewed.
                const res = await api.post('/api/trusttrail', { userId: id });
                if (active) setTrail(res.data || []);
            } catch (e) {
                // A user may have an empty trail; ignore.
            } finally {
                if (active) setLoading(false);
            }
        })();
        return () => { active = false; };
    }, [id]);

    if (loading) return <div className="route-loading">Loading…</div>;
    if (!user) return <div className="container"><main><p className="empty-state">User not found.</p></main></div>;

    const avatar = user.profile_picture
        ? `data:image/jpeg;base64,${user.profile_picture}`
        : '/static/user-image.jpg';
    const fullName = [user.name, user.surname].filter(Boolean).join(' ');

    return (
        <div className="container">
            <main>
                <article className="detail-card">
                    <div className="user-profile-header">
                        <img className="user-avatar" src={avatar} alt={fullName} />
                        <div>
                            <span className="eyebrow">Member</span>
                            <h1>{fullName}</h1>
                            {user.location && <p className="detail-meta">📍 {user.location}</p>}
                        </div>
                    </div>

                    <section className="detail-section">
                        <h2>TrustTrail ({trail.length})</h2>
                        {trail.length === 0 ? (
                            <p className="muted">No trust trail yet.</p>
                        ) : (
                            <ul className="detail-list trust-list">
                                {trail.map((t, i) => (
                                    <li key={i}>
                                        <strong>{t.transaction_description}</strong>
                                        <span className="trust-meta">
                                            {t.transaction_status}
                                            {t.other_user_name ? ` · with ${t.other_user_name}` : ''}
                                            {t.project_name ? ` · ${t.project_name}` : ''}
                                        </span>
                                        {t.gratitude_comment && <p className="trust-quote">“{t.gratitude_comment}”</p>}
                                    </li>
                                ))}
                            </ul>
                        )}
                    </section>
                </article>
            </main>
        </div>
    );
}

export default UserPage;
