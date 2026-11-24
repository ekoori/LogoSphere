// File: ./frontend/src/components/UserLogin.js
// Description: This is the React.js file for the User Login Component.
// Classes/Methods/Properties: 
//    [+] UserLogin - The main component for the user login form.
//        [+] email - State property to store the user's entered email.
//        [+] password - State property to store the user's entered password.
//        [+] handleLogin - Handles the form submission for logging in the user.



import React, { useState } from 'react';
import api from '../api';
import '../styles/App.css'; 
import '../styles/UserLogin.css'; 
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { useLogin } from '../App';  // Import useLogin hook
import { modeOfAccount } from '../utils/modes';
import { useMailOn } from '../utils/useMail';
import { inviteFromHash, returnTo } from '../utils/returnTo';



const UserLogin = () => {
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [forgot, setForgot] = useState(false);
    const { setIsLoggedIn, setUserId, setUserName, setIsPlatformAdmin, adoptUiMode } = useLogin();
    const navigate = useNavigate();
    const mailOn = useMailOn();
    const [asked, setAsked] = useState({});
    const { state } = useLocation();
    const invite = state?.from?.pathname === '/invite' ? inviteFromHash(state.from.hash) : '';

    const emailLink = async () => {
        if (!email.trim()) {
            setAsked({ error: 'Type your email address above first.' });
            return;
        }
        setAsked({ busy: true });
        try {
            setAsked({ ok: (await api.post('/api/password/forgot', { email: email.trim() })).data.message });
        } catch (err) {
            setAsked({ error: err.response?.data?.message || "That didn't send. Please try again." });
        }
    };

    const handleLogin = async (e) => {
        e.preventDefault();
        setError('');
        setSubmitting(true);
        try {
            const response = await api.post('/api/login', {
                email,
                password
            }, {
                withCredentials: true
            });

            if (response.status === 200 && response.data.data) {
                setIsLoggedIn(true);
                setUserId(response.data.data.user_id);
                setUserName((response.data.data.name || '').trim());
                setIsPlatformAdmin(!!response.data.data.is_platform_admin);
                adoptUiMode(modeOfAccount(response.data.data));
                navigate(returnTo(state), { replace: true });
            }
        } catch (error) {
            console.error('Login error:', error);
            setError(error.response?.data?.message || 'Login failed. Check your email and password.');
        } finally {
            setSubmitting(false);
        }
    };

    return (
        <div className="login-container">
            <form className="login-form" onSubmit={handleLogin}>
                <h2>Log in to LogoSphere</h2>
                {error && <p className="auth-error">{error}</p>}
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
                    placeholder="Password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    autoComplete="current-password"
                    required
                />
                <button type="submit" disabled={submitting}>
                    {submitting ? 'Logging in…' : 'Log in'}
                </button>
                <p className="auth-alt">
                    New to LogoSphere? <Link to={invite ? `/register#invite=${invite}` : '/register'}>Create an account</Link>
                </p>
                <p className="auth-alt">
                    <button type="button" className="auth-link-btn" onClick={() => setForgot((v) => !v)} aria-expanded={forgot}>
                        Forgot your password?
                    </button>
                </p>
                {forgot && mailOn && (
                    <div className="auth-forgot">
                        {asked.ok ? (
                            <p role="status">{asked.ok}</p>
                        ) : (
                            <>
                                <p>We&rsquo;ll email you a link to choose a new password. It works once, for 2 hours.</p>
                                {asked.error && <p className="auth-error" role="alert">{asked.error}</p>}
                                <button type="button" onClick={emailLink} disabled={asked.busy}>
                                    {asked.busy ? 'Sending…' : 'Email me a reset link'}
                                </button>
                            </>
                        )}
                    </div>
                )}
                {forgot && mailOn === false && (
                    <p className="auth-forgot" role="note">
                        LogoSphere can't send email yet. Ask a platform administrator for a password reset link — it
                        works once, for 24 hours. If you don't know one, write to{' '}
                        <a href="mailto:support@logosphere.earth">support@logosphere.earth</a>.
                    </p>
                )}
            </form>
        </div>
    );
};

export default UserLogin;