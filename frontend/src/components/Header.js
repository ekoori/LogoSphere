// File: ./frontend/src/components/Header.js
// Description: Fixed top navigation and branding for LogoSphere.
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
    const [menuOpen, setMenuOpen] = useState(false);
    const accountRef = useRef(null);

    const toggleNotifications = () => setNotificationsVisible((v) => !v);
    const closeMenu = () => setMenuOpen(false);

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
        <>
        <header>
            <div className="brand">
                <Link to="/" onClick={closeMenu}>
                    <BrandMark />
                    Logo<b>Sphere</b>
                </Link>
            </div>

            <nav className={`nav-menu ${menuOpen ? 'is-open' : ''}`}>
                <ul className="nav-primary">
                    <li><Link to="/openings" onClick={closeMenu}>Openings</Link></li>
                    <li><Link to="/spheres" onClick={closeMenu}>Spheres</Link></li>
                    <li><Link to="/alliances" onClick={closeMenu}>Alliances</Link></li>
                    <li><Link to="/projects" onClick={closeMenu}>Projects</Link></li>
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
                        <span className="account-label">Account</span>
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
