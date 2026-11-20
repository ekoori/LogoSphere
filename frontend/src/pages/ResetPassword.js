// ResetPassword — where a one-time reset link lands (/reset-password#token=…).
// A platform admin makes the link for a member who forgot their password; the
// token sits in the URL fragment, which the browser never sends to the server,
// so it stays out of access logs. It reaches the API only in the POST body.
import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import api from '../api';
import '../styles/UserLogin.css';

const MIN_PASSWORD = 8;

export default function ResetPassword() {
    const [token, setToken] = useState('');
    const [password, setPassword] = useState('');
    const [again, setAgain] = useState('');
    const [busy, setBusy] = useState(false);
    const [error, setError] = useState('');
    const [done, setDone] = useState(false);

    useEffect(() => {
        const m = /(?:^|[#&])token=([^&]+)/.exec(window.location.hash || '');
        setToken(m ? decodeURIComponent(m[1]) : '');
        // Off the address bar (and out of history) once read.
        if (m) window.history.replaceState(null, '', window.location.pathname);
    }, []);

    const submit = async (e) => {
        e.preventDefault();
        setError('');
        if (password.length < MIN_PASSWORD) { setError(`A password needs at least ${MIN_PASSWORD} characters.`); return; }
        if (password !== again) { setError("The two passwords don't match."); return; }
        setBusy(true);
        try {
            await api.post('/api/password/reset', { token, password });
            setDone(true);
        } catch (err) {
            setError(err.response?.data?.message || 'Could not set your password. Please try again.');
        } finally {
            setBusy(false);
        }
    };

    if (done) {
        return (
            <div className="login-container">
                <div className="login-form">
                    <h2>Your password is set</h2>
                    <p className="auth-alt">You were signed out everywhere. Sign in with your new password.</p>
                    <Link to="/login" className="auth-action">Log in</Link>
                </div>
            </div>
        );
    }

    return (
        <div className="login-container">
            <form className="login-form" onSubmit={submit}>
                <h2>Choose a new password</h2>
                {!token && (
                    <p className="auth-error">
                        This page needs the whole reset link. Ask the administrator who sent it for a new one.
                    </p>
                )}
                {error && <p className="auth-error">{error}</p>}
                <input type="password" placeholder="New password" value={password} onChange={(e) => setPassword(e.target.value)}
                       autoComplete="new-password" required disabled={!token} />
                <input type="password" placeholder="New password again" value={again} onChange={(e) => setAgain(e.target.value)}
                       autoComplete="new-password" required disabled={!token} />
                <button type="submit" disabled={busy || !token}>{busy ? 'Saving…' : 'Set my password'}</button>
                <p className="auth-alt">The link works once, for 24 hours. <Link to="/login">Back to log in</Link></p>
            </form>
        </div>
    );
}
