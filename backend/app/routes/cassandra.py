# File: ./backend/app/routes/cassandra.py
# Description: Flask session interface backed by the Cassandra `sessions` table.
# Classes/Methods:
#    [+] CassandraSession - A custom session object that holds session data.
#    [+] CassandraSessionInterface - Reads/writes sessions through the app's shared connection.
#        [+] open_session(app, request) - Retrieves session data from Cassandra based on the session_id.
#        [+] save_session(app, session, response) - Saves session data in Cassandra and manages session cookies.
#
# Queries are plain parameterised statements rather than prepared ones: a
# prepared statement is bound to the cluster connection it was prepared on,
# and the shared connection can be rebuilt at runtime (see app/db.py).

from flask.sessions import SessionInterface, SessionMixin
from app.db import session as _shared_session
from flask import request
import uuid
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

_SELECT = ("SELECT session_id, user_email, user_id, data, expire_at, last_access_time "
           "FROM sessions WHERE session_id = %s")
_INSERT = ("INSERT INTO sessions (session_id, user_email, user_id, creation_time, "
           "last_access_time, expire_at, data) VALUES (%s, %s, %s, %s, %s, %s, %s)")
# IF EXISTS: a session deleted by a concurrent logout must not come back as a
# half-row.
_TOUCH = ("UPDATE sessions SET last_access_time = %s, expire_at = %s, data = %s "
          "WHERE session_id = %s IF EXISTS")

# The expiry slides with use, but writing the row (and re-sending the cookie)
# on every request was pure write load - and it overwrote creation_time.
TOUCH_EVERY = timedelta(minutes=10)


class CassandraSession(dict, SessionMixin):
    """Custom session object for storing session data. `last_access` is when
    the stored row was last touched (None: this request created the session)."""
    def __init__(self, session_id, initial=None, last_access=None):
        super().__init__(initial or {})
        self.session_id = session_id
        self.modified = False
        self.last_access = last_access


class CassandraSessionInterface(SessionInterface):
    """Interface for storing sessions in Cassandra"""
    def __init__(self, session_lifetime):
        # Reuse the app-wide (self-healing) session rather than opening a second cluster.
        self.cassandra_session = _shared_session
        self.session_lifetime = session_lifetime

    def open_session(self, app, request):
        """Retrieve or create a new session"""
        session_cookie = request.cookies.get(app.config.get('SESSION_COOKIE_NAME', 'session_id'))

        if session_cookie:
            try:
                session_uuid = uuid.UUID(session_cookie)
                result = self.cassandra_session.execute(_SELECT, [session_uuid]).one()

                if result and result.user_email and result.user_id and \
                        (result.expire_at is None or result.expire_at > datetime.utcnow()):
                    session_data = {
                        'user_email': result.user_email,
                        'user_id': str(result.user_id),
                        'session_id': str(result.session_id)
                    }
                    if result.data:
                        session_data.update(result.data)

                    return CassandraSession(str(session_uuid), initial=session_data,
                                            last_access=result.last_access_time or datetime.min)

            except Exception as e:
                logger.error(f"Error retrieving session: {e}")

        # Create new session if none exists or retrieval failed
        return CassandraSession(str(uuid.uuid4()))

    def save_session(self, app, session, response):
        """Slide the session's expiry (at most every TOUCH_EVERY) and refresh
        the cookie when it does. Sessions without a user aren't stored."""
        if request.method == 'OPTIONS':
            return

        session_id = session.get('session_id')
        user_email = session.get('user_email')
        user_id = session.get('user_id')

        if not all([session_id, user_email, user_id]):
            return

        now = datetime.utcnow()
        last = getattr(session, 'last_access', None)
        if last is not None and not session.modified and now - last < TOUCH_EVERY:
            return

        try:
            if isinstance(session_id, str):
                session_id = uuid.UUID(session_id)
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)

            expire_at = now + self.session_lifetime

            # Extract additional data, excluding standard fields
            session_data = {k: v for k, v in dict(session).items()
                            if k not in ['session_id', 'user_email', 'user_id']}

            if last is None:
                self.cassandra_session.execute(
                    _INSERT, (session_id, user_email, user_id, now, now, expire_at, session_data))
            else:
                applied = self.cassandra_session.execute(
                    _TOUCH, (now, expire_at, session_data, session_id)).one()
                if not applied or not applied[0]:
                    return          # logged out meanwhile: don't re-send its cookie

            # Set cookie if not already present
            if 'Set-Cookie' not in response.headers:
                response.set_cookie(
                    app.config.get('SESSION_COOKIE_NAME', 'session_id'),
                    str(session_id),
                    httponly=True,
                    secure=app.config.get('SESSION_COOKIE_SECURE', False),
                    samesite='Lax',
                    domain=self.get_cookie_domain(app),
                    path=self.get_cookie_path(app),
                    max_age=int(self.session_lifetime.total_seconds())
                )
                logger.debug(f'Set session cookie: {session_id}')

        except Exception as e:
            logger.error(f"Error saving session: {e}")


def create_fresh_session(user_email, user_id):
    """Create a new fresh session for the given user"""
    if isinstance(user_id, str):
        user_id = uuid.UUID(user_id)

    session_id = str(uuid.uuid4())
    session_data = {
        'session_id': session_id,
        'user_email': user_email,
        'user_id': str(user_id)
    }
    logger.debug(f'Creating fresh session for user {user_email}')
    return CassandraSession(session_id, initial=session_data)
