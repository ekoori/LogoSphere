// Where emailed links land: finish joining, confirm an address, stop the
// notification emails. None changes anything until a button is pressed, since
// mail scanners open links by themselves.
import React, { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';
import { useLogin } from '../App';
import { modeOfAccount } from '../utils/modes';
import { tokenFromHash } from '../utils/linkToken';
import '../styles/UserLogin.css';

const MIN_PASSWORD = 8;
const said = (err, fallback) => err.response?.data?.message || fallback;

function useLinkToken() {
    const [token] = useState(() => tokenFromHash(window.location.hash));
    useEffect(() => {
        // Off the address bar, and out of history, once read.
        if (token) window.history.replaceState(null, '', window.location.pathname);
    }, [token]);
    return token;
}

export function JoinPage() {
    const token = useLinkToken();
    const { setIsLoggedIn, setUserId, setUserName, setIsPlatformAdmin, adoptUiMode } = useLogin();
    const navigate = useNavigate();
    const [password, setPassword] = useState('');
    const [again, setAgain] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');

    const submit = async (e) => {
        e.preventDefault();
        setError('');
        if (password.length < MIN_PASSWORD) { setError(`A password needs at least ${MIN_PASSWORD} characters.`); return; }
        if (password !== again) { setError("The two passwords don't match."); return; }
        setBusy(true);
        let made;
        try {
            made = (await api.post('/api/register/confirm', { token, password })).data;
        } catch (err) {
            setError(said(err, 'That did not work. Please try again.'));
            setBusy(false);
            return;
        }
        try {
            const { data } = await api.post('/api/login', { email: made.email, password });
            setIsLoggedIn(true);
            setUserId(data.data.user_id);
            setUserName((data.data.name || '').trim());
            setIsPlatformAdmin(!!data.data.is_platform_admin);
            adoptUiMode(modeOfAccount(data.data));
            navigate('/profile', { replace: true });
        } catch (err) {
            navigate('/login', { replace: true });      // the account is made: only signing in is left
        }
    };

    return (
        <div className="login-container">
            <form className="login-form" onSubmit={submit}>
                <h2>Finish joining</h2>
                {token
                    ? <p className="auth-alt">Choose a password, and your account is ready.</p>
                    : <p className="auth-error">This page needs the whole link from the email.</p>}
                {error && <p className="auth-error" role="alert">{error}</p>}
                <input type="password" placeholder="Password (min 8 characters)" aria-label="Password" autoComplete="new-password"
                       value={password} onChange={(e) => setPassword(e.target.value)} required disabled={!token} />
                <input type="password" placeholder="Password again" aria-label="Password again" autoComplete="new-password"
                       value={again} onChange={(e) => setAgain(e.target.value)} required disabled={!token} />
                <button type="submit" disabled={busy || !token}>{busy ? 'Creating your account…' : 'Create my account'}</button>
                <p className="auth-alt">Link too old? <Link to="/register">Ask for a new one</Link></p>
            </form>
        </div>
    );
}

// One button that uses the link up.
function LinkAction({ title, about, button, post, after, done }) {
    const token = useLinkToken();
    const [state, setState] = useState({});

    const press = async () => {
        setState({ busy: true });
        try {
            setState({ ok: (await post(token)).data.message || done });
        } catch (err) {
            setState({ error: said(err, 'That did not work. Please try again.') });
        }
    };

    return (
        <div className="login-container">
            <div className="login-form">
                <h2>{title}</h2>
                {state.ok ? (
                    <p className="auth-ok" role="status">{state.ok}</p>
                ) : (
                    <>
                        {token
                            ? <p className="auth-alt">{about}</p>
                            : <p className="auth-error">This page needs the whole link from the email.</p>}
                        {state.error && <p className="auth-error" role="alert">{state.error}</p>}
                        <button type="button" onClick={press} disabled={!token || state.busy}>
                            {state.busy ? 'One moment…' : button}
                        </button>
                    </>
                )}
                <p className="auth-alt">{after}</p>
            </div>
        </div>
    );
}

export function ConfirmEmailPage() {
    return (
        <LinkAction
            title="Confirm your email"
            about="This shows that the address is yours, so LogoSphere may email you what you chose."
            button="Yes, confirm it"
            done="Your email is confirmed."
            post={(token) => api.post('/api/email/confirm', { token })}
            after={<Link to="/settings#email">Your email settings</Link>}
        />
    );
}

export function UnsubscribePage() {
    return (
        <LinkAction
            title="Stop notification emails"
            about="You will get no more notifications by email. Your notifications stay on LogoSphere."
            button="Stop the emails"
            done="Done."
            post={(token) => api.post(`/api/email/unsubscribe/${encodeURIComponent(token)}`)}
            after={<>Changed your mind? <Link to="/settings#email">Choose what is emailed</Link></>}
        />
    );
}
