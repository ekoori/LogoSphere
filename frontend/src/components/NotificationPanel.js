// NotificationPanel — dropdown on desktop, full-width sheet under the header
// on mobile. Renders real backend notifications: click an item to mark it
// read and jump to what it's about; "Mark all read" clears the unread badge.
//
// The panel is rendered through a portal onto <body> with fixed positioning
// computed from the bell's position. Living inside the sticky header used to
// tie its stacking (and, because the header has a backdrop-filter, its
// containing block) to the header — on some browsers/pages the panel ended
// up painted beneath the page banner. On <body> with its own z-index it can't.
import React, { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';
import Avatar from './Avatar';

const MOBILE_QUERY = '(max-width: 900px)';

function timeAgo(iso) {
    if (!iso) return '';
    const diffMs = Date.now() - new Date(iso).getTime();
    const mins = Math.floor(diffMs / 60000);
    if (mins < 1) return 'just now';
    if (mins < 60) return `${mins}m ago`;
    const hours = Math.floor(mins / 60);
    if (hours < 24) return `${hours}h ago`;
    const days = Math.floor(hours / 24);
    if (days < 7) return `${days}d ago`;
    return new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
}

// Where to put the panel: under the bell on desktop, a sheet under the header on mobile.
function computePlacement() {
    const bell = document.getElementById('notification-bell');
    const header = document.querySelector('header');
    const headerBottom = header ? header.getBoundingClientRect().bottom : 64;
    if (window.matchMedia(MOBILE_QUERY).matches || !bell) {
        return { position: 'fixed', top: headerBottom + 6, left: 8, right: 8, width: 'auto',
                 maxHeight: `calc(100vh - ${headerBottom + 6}px - 1rem)`, zIndex: 2001 };
    }
    const r = bell.getBoundingClientRect();
    return { position: 'fixed', top: r.bottom + 10, right: Math.max(8, window.innerWidth - r.right), left: 'auto',
             maxHeight: `calc(100vh - ${r.bottom + 10}px - 1rem)`, zIndex: 2001 };
}

const NotificationPanel = ({ notifications, isVisible, onClose, onItemClick, onMarkAllRead }) => {
    const panelRef = useRef(null);
    const navigate = useNavigate();
    const [placement, setPlacement] = useState(() => (typeof window === 'undefined' ? {} : computePlacement()));

    useEffect(() => {
        if (!isVisible) return undefined;
        const update = () => setPlacement(computePlacement());
        update();
        window.addEventListener('resize', update);
        window.addEventListener('scroll', update, true);
        return () => {
            window.removeEventListener('resize', update);
            window.removeEventListener('scroll', update, true);
        };
    }, [isVisible]);

    useEffect(() => {
        const handleClickOutside = (event) => {
            const bell = document.getElementById('notification-bell');
            if (bell && bell.contains(event.target)) return; // the bell toggles it itself
            if (panelRef.current && !panelRef.current.contains(event.target)) onClose();
        };
        if (isVisible) document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [isVisible, onClose]);

    // Lock body scroll while the mobile sheet is open (mirrors the nav drawer).
    useEffect(() => {
        const mobile = typeof window !== 'undefined' && window.matchMedia(MOBILE_QUERY).matches;
        document.body.classList.toggle('notification-panel-open', isVisible && mobile);
        return () => document.body.classList.remove('notification-panel-open');
    }, [isVisible]);

    if (!isVisible) return null;

    const hasUnread = notifications.some((n) => !n.is_read);

    return createPortal(
        <>
            {/* Scrim — tap outside (or the whole backdrop on mobile) to close. */}
            <div className="notification-scrim" onClick={onClose} aria-hidden="true" style={{ zIndex: 2000 }} />
            <div ref={panelRef} id="notification-panel" className="notification-panel" style={placement} role="dialog" aria-label="Notifications">
                <div className="notification-panel-head">
                    <h4>Notifications</h4>
                    <div className="notification-head-actions">
                        {hasUnread && (
                            <button className="notification-markall" onClick={onMarkAllRead}>Mark all read</button>
                        )}
                        <button className="notification-close" onClick={onClose} aria-label="Close notifications">✕</button>
                    </div>
                </div>

                {notifications.length === 0 ? (
                    <p className="notification-empty">You're all caught up.</p>
                ) : (
                    <ul className="notification-list">
                        {notifications.map((n) => (
                            <li key={n.notification_id} className={n.is_read ? '' : 'is-unread'}>
                                <button
                                    className="notification-item"
                                    onClick={() => {
                                        onItemClick(n);
                                        if (n.link) navigate(n.link);
                                        onClose();
                                    }}
                                >
                                    <Avatar userId={n.actor_id} name={n.actor_name} size={38} />
                                    <span className="notification-body">
                                        <span className="notification-message">{n.message}</span>
                                        <span className="notification-time">{timeAgo(n.created_at)}</span>
                                    </span>
                                    {!n.is_read && <span className="notification-dot" aria-hidden="true" />}
                                </button>
                            </li>
                        ))}
                    </ul>
                )}
            </div>
        </>,
        document.body
    );
};

NotificationPanel.propTypes = {
    notifications: PropTypes.arrayOf(PropTypes.shape({
        notification_id: PropTypes.string.isRequired,
        created_at: PropTypes.string,
        actor_id: PropTypes.string,
        actor_name: PropTypes.string,
        type: PropTypes.string,
        message: PropTypes.string.isRequired,
        link: PropTypes.string,
        is_read: PropTypes.bool,
    })).isRequired,
    isVisible: PropTypes.bool.isRequired,
    onClose: PropTypes.func.isRequired,
    onItemClick: PropTypes.func.isRequired,
    onMarkAllRead: PropTypes.func.isRequired,
};

export default NotificationPanel;
