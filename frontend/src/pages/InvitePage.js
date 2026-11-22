// Where an invitation link lands. Its code rides in the fragment, which never
// reaches a server's log, and nothing is joined until a button is pressed.
import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import api from '../api';
import { useLogin } from '../App';
import { groupHref, inviteFromHash } from '../utils/returnTo';
import '../styles/UserLogin.css';
import '../styles/Events.css';

export default function InvitePage() {
    const { hash } = useLocation();
    const code = inviteFromHash(hash);
    const { isLoggedIn, authChecked } = useLogin();
    const navigate = useNavigate();
    const client = useQueryClient();
    const [found, setFound] = useState(null);       // {inviter, group}, or {broken}
    const [busy, setBusy] = useState(false);
    const [problem, setProblem] = useState('');

    useEffect(() => {
        setProblem('');
        if (!code) {
            setFound({ broken: 'This page needs the whole invitation link.' });
            return undefined;
        }
        let current = true;
        setFound(null);
        api.post('/api/invites/look', { code })
            .then((r) => { if (current) setFound(r.data); })
            .catch((err) => {
                if (current) setFound({ broken: err.response?.data?.message || "That didn't load. Open the link again in a moment." });
            });
        return () => { current = false; };
    }, [code]);

    const accept = async () => {
        setBusy(true);
        setProblem('');
        try {
            const { data } = await api.post('/api/invites/accept', { code });
            client.invalidateQueries();
            navigate(groupHref(data.group) || '/profile', { replace: true });
        } catch (err) {
            setProblem(err.response?.data?.message || "That didn't work. Please try again.");
            setBusy(false);
        }
    };

    if (!found || !authChecked) return <div className="login-container"><p className="evt-soft" role="status">Loading…</p></div>;

    const { broken, inviter, group } = found;
    return (
        <div className="login-container">
            <div className="login-form inv-card">
                {broken ? (
                    <>
                        <h2>Invitation</h2>
                        <p className="auth-error" role="alert">{broken}</p>
                        <p className="auth-alt"><Link to="/">To LogoSphere</Link></p>
                    </>
                ) : (
                    <>
                        <h2>{inviter} invites you to {group ? group.name : 'LogoSphere'}</h2>
                        <p className="auth-alt">
                            {group
                                ? `A ${group.kind} on LogoSphere, where people offer and ask for help, and remember it.`
                                : 'A place where people offer and ask for help, and remember it.'}
                        </p>
                        {problem && <p className="auth-error" role="alert">{problem}</p>}
                        {isLoggedIn ? (
                            group ? (
                                <>
                                    <button type="button" onClick={accept} disabled={busy}>{busy ? 'Joining…' : `Join ${group.name}`}</button>
                                    {group.kind !== 'sphere' && <p className="auth-alt">You join its sphere as well.</p>}
                                </>
                            ) : (
                                <p className="auth-alt">You&rsquo;re here already. <Link to="/profile">To your page</Link></p>
                            )
                        ) : (
                            <>
                                <Link className="evt-btn evt-btn--main" to={`/register#invite=${code}`}>Create an account</Link>
                                <p className="auth-alt">
                                    Have one already?{' '}
                                    <Link to="/login" state={{ from: { pathname: '/invite', hash: `#${code}` } }}>Log in</Link>
                                </p>
                            </>
                        )}
                    </>
                )}
            </div>
        </div>
    );
}
