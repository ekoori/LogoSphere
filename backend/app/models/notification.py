# Notification model — a per-user inbox of "something happened" events
# (opening accepted, acceptance confirmed, receipt received, new follower).
# Backed by logosphere.notifications: PRIMARY KEY (user_id, created_at,
# notification_id) with created_at DESC, so a user's own feed is always a
# fast single-partition read, already newest-first.
from cassandra.cluster import Cluster
import uuid
import os
import logging
from datetime import datetime

CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(CASSANDRA_HOSTS)
cassandra_session = cluster.connect('logosphere')

# A personal inbox is naturally small and bounded, so list/unread-count both
# work off one bounded fetch rather than a separate COUNT query.
FETCH_LIMIT = 50


class Notification:
    @classmethod
    def create(cls, user_id, actor_id, actor_name, type_, message, link=None):
        """Emit a notification to user_id. Silently no-ops on failure — a
        missed notification should never break the action that triggered it."""
        try:
            cassandra_session.execute(
                """INSERT INTO notifications
                   (user_id, created_at, notification_id, actor_id, actor_name,
                    type, message, link, is_read)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (uuid.UUID(str(user_id)), datetime.utcnow(), uuid.uuid4(),
                 uuid.UUID(str(actor_id)) if actor_id else None, actor_name,
                 type_, message, link, False)
            )
        except Exception as e:
            logging.error(f'Error creating notification: {e}')

    @classmethod
    def list_for_user(cls, user_id):
        try:
            rows = cassandra_session.execute(
                "SELECT * FROM notifications WHERE user_id = %s LIMIT %s",
                [uuid.UUID(str(user_id)), FETCH_LIMIT]
            )
            return [{
                'notification_id': str(r.notification_id),
                'created_at': r.created_at.isoformat() if r.created_at else None,
                'actor_id': str(r.actor_id) if r.actor_id else None,
                'actor_name': r.actor_name,
                'type': r.type,
                'message': r.message,
                'link': r.link,
                'is_read': bool(r.is_read),
            } for r in rows]
        except Exception as e:
            logging.error(f'Error listing notifications: {e}')
            return []

    @classmethod
    def unread_count(cls, user_id):
        return sum(1 for n in cls.list_for_user(user_id) if not n['is_read'])

    @classmethod
    def mark_read(cls, user_id, created_at, notification_id):
        try:
            cassandra_session.execute(
                "UPDATE notifications SET is_read = true WHERE user_id = %s AND created_at = %s AND notification_id = %s",
                [uuid.UUID(str(user_id)), created_at, uuid.UUID(str(notification_id))]
            )
            return True
        except Exception as e:
            logging.error(f'Error marking notification read: {e}')
            return False

    @classmethod
    def mark_all_read(cls, user_id):
        try:
            rows = cassandra_session.execute(
                "SELECT created_at, notification_id, is_read FROM notifications WHERE user_id = %s LIMIT %s",
                [uuid.UUID(str(user_id)), FETCH_LIMIT]
            )
            for r in rows:
                if not r.is_read:
                    cassandra_session.execute(
                        "UPDATE notifications SET is_read = true WHERE user_id = %s AND created_at = %s AND notification_id = %s",
                        [uuid.UUID(str(user_id)), r.created_at, r.notification_id]
                    )
            return True
        except Exception as e:
            logging.error(f'Error marking all notifications read: {e}')
            return False
