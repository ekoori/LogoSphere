// File: ./frontend/src/components/Header.js
// Description: Fixed top navigation and branding for TrustSphere.
// Class: Header — brand wordmark, primary nav, notifications, and account menu.
import React, { useState, useEffect, useRef } from 'react';
import { Link } from 'react-router-dom';
import '../styles/App.css';
import { useLogin } from '../App';  // Import the useLogin hook from App.js
import NotificationPanel from './NotificationPanel';

// Hand-drawn sun/leaf brand mark — sits beside the wordmark.
const BrandMark = () => (
    <svg className="brand-mark" viewBox="0 0 32 32" fill="none" aria-hidden="true">
        <circle cx="16" cy="16" r="6.5" fill="currentColor" />
        <g stroke="currentColor" strokeWidth="2" strokeLinecap="round">
            <path d="M16 2.5v3.5M16 26v3.5M29.5 16H26M6 16H2.5" />
            <path d="M25.5 6.5l-2.4 2.4M8.9 23.1l-2.4 2.4M25.5 25.5l-2.4-2.4M8.9 8.9L6.5 6.5" />
        </g>
    </svg>
);

const Header = () => {
    const { isLoggedIn, handleLogout } = useLogin();
    const [notificationsVisible, setNotificationsVisible] = useState(false);
    const [accountOpen, setAccountOpen] = useState(false);
    const accountRef = useRef(null);

    const toggleNotifications = () => setNotificationsVisible((v) => !v);

    // Close the account menu when clicking outside of it.
    useEffect(() => {
        const onClick = (e) => {
            if (accountRef.current && !accountRef.current.contains(e.target)) {
                setAccountOpen(false);
            }
        };
        document.addEventListener('mousedown', onClick);
        return () => document.removeEventListener('mousedown', onClick);
    }, []);

    const notifications = [
        {
            avatar: 'static/elon_musk_avatar.jpg',
            author: 'Elon Musk',
            link: '/user',
            message: 'Elon accepted your request for a Roadster drive.',
            time: '2 hours ago'
        },
        {
            avatar: 'static/elon_musk_avatar.jpg',
            author: 'OpenAI',
            link: '/alliance',
            message: 'You got accepted to the OpenAI alliance.',
            time: '4 hours ago'
        },
        {
            avatar: 'static/elon_musk_avatar.jpg',
            author: 'John Doe',
            link: '/user',
            message: 'John Doe liked your post.',
            time: '1 day ago'
        },
        {
            avatar: 'static/elon_musk_avatar.jpg',
            author: 'Jane Smith',
            link: '/project',
            message: 'Jane Smith commented on your project.',
            time: '2 days ago'
        }
    ];

    return (
        <header>
            <div className="brand">
                <Link to="/">
                    <BrandMark />
                    Trust<b>Sphere</b>
                </Link>
            </div>

            <nav>
                <ul className="nav-primary">
                    <li><Link to="/marketplace">Marketplace</Link></li>
                    <li><Link to="/spheres">Spheres</Link></li>
                    <li><Link to="/alliances">Alliances</Link></li>
                    <li><Link to="/projects">Projects</Link></li>
                </ul>
            </nav>

            <div className="nav-actions">
                <Link to="/donate" className="donate-link">Donate 💛</Link>

                <div className="notification-icon">
                    <button id="notification-bell" onClick={toggleNotifications} aria-label="Toggle notifications">🔔</button>
                    <NotificationPanel notifications={notifications} isVisible={notificationsVisible} onClose={toggleNotifications} />
                </div>

                <div className="account" ref={accountRef}>
                    <button
                        className="account-toggle"
                        onClick={() => setAccountOpen((v) => !v)}
                        aria-haspopup="true"
                        aria-expanded={accountOpen}
                    >
                        <span className="account-avatar">◍</span>
                        Account
                        <span className="account-caret">▾</span>
                    </button>
                    {accountOpen && (
                        <div className="account-menu" role="menu">
                            <Link to="/profile" onClick={() => setAccountOpen(false)}>Profile</Link>
                            <Link to="/settings" onClick={() => setAccountOpen(false)}>Settings</Link>
                            <Link to="/admin" onClick={() => setAccountOpen(false)}>Admin</Link>
                            <Link to="/about" onClick={() => setAccountOpen(false)}>About</Link>
                            <div className="menu-divider" />
                            {isLoggedIn
                                ? <button onClick={() => { setAccountOpen(false); handleLogout(); }}>Log out</button>
                                : <Link to="/login" onClick={() => setAccountOpen(false)}>Log in</Link>}
                        </div>
                    )}
                </div>

                {!isLoggedIn && <Link to="/login" className="auth-action">Login</Link>}
            </div>
        </header>
    );
};

export default Header;
