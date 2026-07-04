# Routes: Notifications API — a user's own inbox of "something happened" events.
import logging
from datetime import datetime
from flask import request, jsonify, current_app as app
from app.models.notification import Notification
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


@validate_session
def get_notifications(user_id=None):
    """List the caller's notifications (newest first) plus the unread count."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        items = Notification.list_for_user(user_id)
        unread = sum(1 for n in items if not n['is_read'])
        return jsonify({'notifications': items, 'unread_count': unread}), 200
    except Exception as e:
        logger.error(f'Error in get_notifications: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def mark_notification_read(user_id=None):
    """Mark one notification read. Body: { created_at, notification_id } —
    both are needed since they're part of the row's primary key."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        created_at_raw = data.get('created_at')
        notification_id = data.get('notification_id')
        if not created_at_raw or not notification_id:
            return jsonify({'message': 'created_at and notification_id are required'}), 400
        created_at = datetime.fromisoformat(created_at_raw)
        Notification.mark_read(user_id, created_at, notification_id)
        return jsonify({'message': 'ok'}), 200
    except ValueError:
        return jsonify({'message': 'Invalid created_at'}), 400
    except Exception as e:
        logger.error(f'Error in mark_notification_read: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def mark_all_notifications_read(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        Notification.mark_all_read(user_id)
        return jsonify({'message': 'ok'}), 200
    except Exception as e:
        logger.error(f'Error in mark_all_notifications_read: {e}')
        return jsonify({'message': 'Internal server error'}), 500
