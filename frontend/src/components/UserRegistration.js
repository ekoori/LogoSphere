// UserRegistration — create a new LogoSphere account.
// With email working it is email first: name and address here, the password
// on the page the emailed link opens (pages/EmailLinkPages.js). Without email
// the account is made here, signed in at once and routed to its profile.
import React, { useEffect, useState } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import api from '../api';
import { useLogin } from '../App';
import { modeOfAccount } from '../utils/modes';
import { useMailOn } from '../utils/useMail';
import { groupHref, inviteFromHash } from '../utils/returnTo';
import '../styles/App.css';
import '../styles/UserLogin.css';

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

const UserRegistration = () => {
    const mailOn = useMailOn();
    const [name, setName] = useState('');
    const [email, setEmail] = useState('');
    const [password, setPassword] = useState('');
    const [confirm, setConfirm] = useState('');
    const [error, setError] = useState('');
    const [submitting, setSubmitting] = useState(false);
    const [sent, setSent] = useState(false);
    const { setIsLoggedIn, setUserId, setUserName, adoptUiMode } = useLogin();
    const navigate = useNavigate();
    const withPassword = mailOn === false;
    const { hash } = useLocation();
    const invite = inviteFromHash(hash);
    const [invited, setInvited] = useState(null);

    useEffect(() => {
        setInvited(null);
        if (!invite) return undefined;
        let current = true;
        api.post('/api/invites/look', { code: invite })
            .then((r) => { if (current) setInvited(r.data); })
            .catch(() => { if (current) setInvited({ broken: true }); });
        return () => { current = false; };
    }, [invite]);

    const handleRegister = async (e) => {
        e.preventDefault();
        setError('');

        // Client-side validation with clear, inline feedback.
        if (!name.trim()) { setError('Please enter your name.'); return; }
        if (!EMAIL_RE.test(email.trim())) { setError('Please enter a valid email address.'); return; }
        if (withPassword) {
            if (password.length < 8) { setError('Password must be at least 8 characters.'); return; }
            if (password !== confirm) { setError('Passwords do not match.'); return; }
        }

        setSubmitting(true);
        try {
            const details = { name: name.trim(), email: email.trim(), ...(withPassword && { password }), ...(invite && { invite }) };
            const made = await api.post('/api/register', details);
            if (made.data.confirm_email) {
                setSent(true);
                return;
            }

            // Auto-login so the new user goes straight into the app.
            const res = await api.post('/api/login', { email: email.trim(), password }, { withCredentials: true });
            if (res.status === 200 && res.data.data) {
                setIsLoggedIn(true);
                setUserId(res.data.data.user_id);
                setUserName((res.data.data.name || '').trim());
                adoptUiMode(modeOfAccount(res.data.data));
                navigate(groupHref(made.data.invited_to) || '/profile');
            } else {
                // Registered but couldn't auto-login — send them to log in manually.
                navigate('/login');
            }
        } catch (err) {
            const msg = err.response?.data?.message || '';
            const status = err.response?.status;
            if (!withPassword && msg && (status === 400 || status === 429)) setError(msg);
            else if (status === 400) setError(/already/i.test(msg) ? msg : 'That email is already registered, or the details are invalid.');
            else setError('Registration failed. Please try again.');
        } finally {
            setSubmitting(false);
        }
    };

    if (sent) {
        return (
            <div className="login-container">
                <div className="login-form">
                    <h2>Check your email</h2>
                    <p className="auth-ok" role="status">
                        We sent a link to <strong>{email.trim()}</strong>. Open it to choose your password.
                    </p>
                    <p className="auth-alt">It can take a few minutes: look in spam too. The link works for a day.</p>
                    <p className="auth-alt">
                        <button type="button" className="auth-link-btn" onClick={() => setSent(false)}>
                            Send it again, or use another address
                        </button>
                    </p>
                </div>
            </div>
        );
    }

    return (
        <div className="login-container">
            <form className="login-form" onSubmit={handleRegister}>
                <h2>Join LogoSphere</h2>
                {invited && (
                    <p className={invited.broken ? 'auth-error' : 'auth-ok'} role="status">
                        {invited.broken
                            ? "That invitation doesn't work any more. You can still join."
                            : `${invited.inviter} invited you${invited.group ? ` to ${invited.group.name}` : ''}.`}
                    </p>
                )}

                {error && <p className="auth-error" role="alert">{error}</p>}

                <input
                    type="text"
                    placeholder="Name"
                    value={name}
                    onChange={(e) => setName(e.target.value)}
                    autoComplete="name"
                    maxLength={80}
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
                {withPassword && (
                    <>
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
                    </>
                )}

                <p className="auth-alt">
                    By joining you agree to the <Link to="/tos">terms of service</Link> and
                    the <Link to="/privacy">privacy policy</Link>.
                </p>
                <button type="submit" disabled={submitting || mailOn === undefined}>
                    {mailOn
                        ? (submitting ? 'Sending…' : 'Email me a link to join')
                        : (submitting ? 'Creating account…' : 'Create account')}
                </button>
                {mailOn && <p className="auth-alt">You choose your password from the link we email you.</p>}

                <p className="auth-alt">
                    Already have an account?{' '}
                    <Link to="/login" state={invite ? { from: { pathname: '/invite', hash: `#${invite}` } } : undefined}>Log in</Link>
                </p>
            </form>
        </div>
    );
};

export default UserRegistration;
