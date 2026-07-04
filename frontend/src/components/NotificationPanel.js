// NotificationPanel — dropdown on desktop, full-width sheet under the header
// on mobile (see .notification-scrim in App.css, same pattern as the nav
// drawer). Renders real backend notifications: click an item to mark it read
// and jump to what it's about; "Mark all read" clears the unread badge.
import React, { useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import PropTypes from 'prop-types';
import Avatar from './Avatar';

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

const NotificationPanel = ({ notifications, isVisible, onClose, onItemClick, onMarkAllRead }) => {
    const panelRef = useRef(null);
    const navigate = useNavigate();

    useEffect(() => {
        const handleClickOutside = (event) => {
            if (panelRef.current && !panelRef.current.contains(event.target)) {
                onClose();
            }
        };
        if (isVisible) document.addEventListener('mousedown', handleClickOutside);
        return () => document.removeEventListener('mousedown', handleClickOutside);
    }, [isVisible, onClose]);

    // Lock body scroll while the mobile sheet is open (mirrors the nav drawer).
    useEffect(() => {
        document.body.classList.toggle('notification-panel-open', isVisible);
        return () => document.body.classList.remove('notification-panel-open');
    }, [isVisible]);

    if (!isVisible) return null;

    const hasUnread = notifications.some((n) => !n.is_read);

    return (
        <>
            {/* Scrim — tap outside (or the whole backdrop on mobile) to close. */}
            <div className="notification-scrim" onClick={onClose} aria-hidden="true" />
            <div ref={panelRef} id="notification-panel" className="notification-panel">
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
        </>
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
