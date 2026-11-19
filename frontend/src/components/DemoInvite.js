// "Try the demo spheres" - shown to a member who is in none of the demo
// spheres (where AI personas play everyday neighbours) until they join or
// dismiss it. New members are invited, never enrolled.
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import { useInvalidate } from '../utils/queries';
import { DemoTag } from './DemoTags';
import '../styles/DemoTags.css';

const DISMISSED = 'logosphere.demoInviteDismissed';

function dismissedBefore() {
    try {
        return window.localStorage.getItem(DISMISSED) === '1';
    } catch (e) {
        return false;
    }
}

export default function DemoInvite({ onJoined }) {
    const [demo, setDemo] = useState(null);
    const [hidden, setHidden] = useState(dismissedBefore);
    const [joining, setJoining] = useState(false);
    const [error, setError] = useState('');
    const invalidate = useInvalidate();

    useEffect(() => {
        if (hidden) return undefined;
        let live = true;
        api.get('/api/demo').then((r) => { if (live) setDemo(r.data); }).catch(() => {});
        return () => { live = false; };
    }, [hidden]);

    if (hidden || !demo || !demo.spheres?.length || demo.joined_any) return null;

    const join = async () => {
        setJoining(true);
        setError('');
        try {
            await api.post('/api/demo/join');
            await invalidate.all();
            setHidden(true);
            if (onJoined) onJoined();
        } catch (e) {
            setError(e.response?.data?.message || 'Could not join just now - try again.');
        } finally {
            setJoining(false);
        }
    };
    const dismiss = () => {
        try { window.localStorage.setItem(DISMISSED, '1'); } catch (e) { /* private mode */ }
        setHidden(true);
    };
    const names = demo.spheres.map((s) => s.name);

    return (
        <section className="demo-invite" aria-label="Try the demo spheres">
            <div>
                <h3>Try the demo spheres <DemoTag /></h3>
                <p>
                    {names.join(', ')}: AI personas play everyday neighbours there. Post a need, accept an
                    offer, write a receipt, and see how LogoSphere feels. Nothing there is real.
                </p>
                {error && <p className="entity-list-error">{error}</p>}
            </div>
            <div className="demo-invite-actions">
                <button className="btn-orange" onClick={join} disabled={joining}>
                    {joining ? 'Joining…' : `Join all ${names.length}`}
                </button>
                <Link className="btn btn-ghost" to="/spheres#demo">Look first</Link>
                <button className="btn btn-ghost" onClick={dismiss}>Not now</button>
            </div>
        </section>
    );
}
