// UserRegistration — create a new LogoSphere account.
// Validates client-side, registers via /api/register, then auto-logs the new
// user in (so they land straight in the app) and routes to their profile.
import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import api from '../api';
import { useLogin } from '../App';
import '../styles/App.css';
import '../styles/UserLogin.css';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const UserRegistration = () => {
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const { setIsLoggedIn, setUserId } = useLogin();
    const navigate = useNavigate();

    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');

        // Client-side validation with clear, inline feedback.
        if (!name.trim()) { setError('Please enter your name.'); return; }
        if (!EMAIL_RE.test(email)) { setError('Please enter a valid email address.'); return; }
        if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
        if (password !== confirm) { setError('Passwords do not match.'); return; }

        setSubmitting(true);
        try {
            await api.post('/api/register', { name: name.trim(), email: email.trim(), password });

            // Auto-login so the new user goes straight into the app.
            const res = await api.post('/api/login', { email: email.trim(), password }, { withCredentials: true });
            if (res.status === 200 && res.data.data) {
                setIsLoggedIn(true);
                setUserId(res.data.data.user_id);
                navigate('/profile');
            } else {
                // Registered but couldn't auto-login — send them to log in manually.
                navigate('/login');
            }
        } catch (err) {
            const msg = err.response?.data?.message || '';
            setError(
                err.response?.status === 400
                    ? (/already/i.test(msg) ? msg : 'That email is already registered, or the details are invalid.')
                    : 'Registration failed. Please try again.'
            );
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="login-container">
            <form className="login-form" onSubmit={handleRegister}>
                <h2>Join LogoSphere</h2>

                {error && <p className="auth-error">{error}</p>}

                <input
                    type="text"
                    placeholder="Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                    required
                />
                <input
                    type="email"
                    placeholder="Email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    autoComplete="email"
                    required
                />
                <input
                    type="password"
                    placeholder="Password (min 8 characters)"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="new-password"
                    required
                />
                <input
                    type="password"
                    placeholder="Confirm password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    autoComplete="new-password"
                    required
                />

                <button type="submit" disabled={submitting}>
                    {submitting ? 'Creating account…' : 'Create account'}
                </button>

                <p className="auth-alt">
                    Already have an account? <Link to="/login">Log in</Link>
                </p>
            </form>
        </div>
    );
};

export default UserRegistration;
