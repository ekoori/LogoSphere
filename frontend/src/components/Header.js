// File: ./frontend/src/components/Header.js
// Description: Fixed top navigation and branding for LogoSphere.
// Class: Header — brand wordmark, primary nav, notifications, and account menu.
import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import '../styles/App.css';
import { useLogin } from '../App';  // Import the useLogin hook from App.js
import NotificationPanel from './NotificationPanel';
import api from '../api';

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
    const { isLoggedIn, userName, handleLogout } = useLogin();
    // Show the user's first name on the account button when signed in.
    const accountLabel = (isLoggedIn && userName) ? userName.split(/\s+/)[0] : 'Account';
    const [notificationsVisible, setNotificationsVisible] = useState(false);
    const [notifications, setNotifications] = useState([]);
    const [unreadCount, setUnreadCount] = useState(0);
    const [accountOpen, setAccountOpen] = useState(false);
    const [menuOpen, setMenuOpen] = useState(false);
    const accountRef = useRef(null);

    const closeMenu = () => setMenuOpen(false);

    const fetchNotifications = useCallback(async () => {
        if (!isLoggedIn) return;
        try {
            const res = await api.get('/api/notifications');
            setNotifications(res.data?.notifications || []);
            setUnreadCount(res.data?.unread_count || 0);
        } catch (_) {
            // Logged out mid-poll, or a transient error — just leave the last
            // known state rather than surface an error for a background poll.
        }
    }, [isLoggedIn]);

    // Poll every 60s, plus an immediate fetch whenever login state changes.
    useEffect(() => {
        fetchNotifications();
        const id = setInterval(fetchNotifications, 60_000);
        return () => clearInterval(id);
    }, [fetchNotifications]);

    const toggleNotifications = () => {
        setNotificationsVisible((v) => {
            if (!v) fetchNotifications(); // catch anything received since the last poll
            return !v;
        });
    };

    const handleItemClick = async (n) => {
        if (n.is_read) return;
        setNotifications((prev) => prev.map((x) => (x.notification_id === n.notification_id ? { ...x, is_read: true } : x)));
        setUnreadCount((c) => Math.max(0, c - 1));
        try {
            await api.post('/api/notifications/read', { created_at: n.created_at, notification_id: n.notification_id });
        } catch (_) { /* best-effort */ }
    };

    const handleMarkAllRead = async () => {
        setNotifications((prev) => prev.map((x) => ({ ...x, is_read: true })));
        setUnreadCount(0);
        try {
            await api.post('/api/notifications/read_all');
        } catch (_) { /* best-effort */ }
    };

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

    // Lock body scroll while the mobile nav drawer is open.
    useEffect(() => {
        document.body.classList.toggle('nav-menu-open', menuOpen);
        return () => document.body.classList.remove('nav-menu-open');
    }, [menuOpen]);

    return (
        <>
        <header>
            <div className="brand">
                <Link to="/" onClick={closeMenu}>
                    <BrandMark />
                    <span className="brand-word">Logo<b>Sphere</b></span>
                </Link>
            </div>

            <nav className={`nav-menu ${menuOpen ? 'is-open' : ''}`}>
                <ul className="nav-primary">
                    <li><Link to="/spheres" onClick={closeMenu}>Spheres</Link></li>
                    <li><Link to="/alliances" onClick={closeMenu}>Alliances</Link></li>
                    <li><Link to="/projects" onClick={closeMenu}>Projects</Link></li>
                    <li><Link to="/openings" onClick={closeMenu}>Openings</Link></li>
                    {/* Items that live in the top bar on desktop but belong in the
                        drawer on mobile. */}
                    <li className="nav-drawer-only"><Link to="/donate" onClick={closeMenu}>Donate 💛</Link></li>
                    <li className="nav-drawer-only"><Link to="/profile" onClick={closeMenu}>Profile</Link></li>
                    <li className="nav-drawer-only"><Link to="/how-it-works" onClick={closeMenu}>How it Works</Link></li>
                    <li className="nav-drawer-only"><Link to="/about" onClick={closeMenu}>About</Link></li>
                    {!isLoggedIn && <li className="nav-drawer-only"><Link to="/login" onClick={closeMenu}>Log in</Link></li>}
                </ul>
            </nav>

            <div className="nav-actions">
                <Link to="/donate" className="donate-link nav-bar-only">Donate 💛</Link>

                <div className="notification-icon">
                    <button id="notification-bell" onClick={toggleNotifications} aria-label="Toggle notifications">
                        🔔
                        {unreadCount > 0 && (
                            <span className="notification-badge">{unreadCount > 9 ? '9+' : unreadCount}</span>
                        )}
                    </button>
                    <NotificationPanel
                        notifications={notifications}
                        isVisible={notificationsVisible}
                        onClose={() => setNotificationsVisible(false)}
                        onItemClick={handleItemClick}
                        onMarkAllRead={handleMarkAllRead}
                    />
                </div>

                <div className="account" ref={accountRef}>
                    <button
                        className="account-toggle"
                        onClick={() => setAccountOpen((v) => !v)}
                        aria-haspopup="true"
                        aria-expanded={accountOpen}
                    >
                        <span className="account-avatar">◍</span>
                        <span className="account-label">{accountLabel}</span>
                        <span className="account-caret">▾</span>
                    </button>
                    {accountOpen && (
                        <div className="account-menu" role="menu">
                            <Link to="/profile" onClick={() => setAccountOpen(false)}>Profile</Link>
                            <Link to="/settings" onClick={() => setAccountOpen(false)}>Settings</Link>
                            <Link to="/admin" onClick={() => setAccountOpen(false)}>Admin</Link>
                            <Link to="/how-it-works" onClick={() => setAccountOpen(false)}>How it Works</Link>
                            <Link to="/about" onClick={() => setAccountOpen(false)}>About</Link>
                            <div className="menu-divider" />
                            {isLoggedIn
                                ? <button onClick={() => { setAccountOpen(false); handleLogout(); }}>Log out</button>
                                : <Link to="/login" onClick={() => setAccountOpen(false)}>Log in</Link>}
                        </div>
                    )}
                </div>

                {!isLoggedIn && <Link to="/login" className="auth-action nav-bar-only">Login</Link>}

                {/* Hamburger — only shown on mobile (CSS). Toggles the nav drawer. */}
                <button
                    className="nav-toggle"
                    onClick={() => setMenuOpen((v) => !v)}
                    aria-label={menuOpen ? 'Close menu' : 'Open menu'}
                    aria-expanded={menuOpen}
                >
                    <span className={`nav-toggle-bars ${menuOpen ? 'is-open' : ''}`} aria-hidden="true">
                        <span /><span /><span />
                    </span>
                </button>
            </div>
        </header>

        {/* Drawer scrim — kept OUTSIDE <header> because the header's
            backdrop-filter would otherwise become the containing block for a
            fixed-position child and clip the overlay to the header. */}
        {menuOpen && <div className="nav-scrim" onClick={closeMenu} aria-hidden="true" />}
        </>
    );
};

export default Header;
