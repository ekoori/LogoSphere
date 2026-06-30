# File: ./backend/app/routes/cassandra.py
# Description: This file implements session management using Cassandra as the backend for storing session data.
# Classes/Methods:
#    [+] CassandraSession - A custom session object that holds session data.
#        [+] __init__(session_id, initial=None) - Initializes the session with a given session_id and optional initial data.
#    [+] CassandraSessionInterface - The session interface responsible for interacting with the Cassandra database.
#        [+] __init__(cluster_nodes, keyspace, session_lifetime) - Initializes the session interface.
#        [+] open_session(app, request) - Retrieves session data from Cassandra based on the session_id.
#        [+] save_session(app, session, response) - Saves session data in Cassandra and manages session cookies.

from flask.sessions import SessionInterface, SessionMixin
from cassandra.cluster import Cluster
from flask import request, current_app as app
import uuid
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class CassandraSession(dict, SessionMixin):
    """Custom session object for storing session data"""
    def __init__(self, session_id, initial=None):
        super().__init__(initial or {})
        self.session_id = session_id
        self.modified = False

class CassandraSessionInterface(SessionInterface):
    """Interface for storing sessions in Cassandra"""
    def __init__(self, cluster_nodes, keyspace, session_lifetime):
        self.cluster = Cluster(cluster_nodes)
        self.cassandra_session = self.cluster.connect(keyspace)
        self.session_lifetime = session_lifetime

        # Prepare statements for better performance
        self.select_session = self.cassandra_session.prepare(
            "SELECT session_id, user_email, user_id, data, expire_at FROM sessions WHERE session_id = ?"
        )
        self.insert_session = self.cassandra_session.prepare("""
            INSERT INTO sessions (
                session_id, user_email, user_id, creation_time, 
                last_access_time, expire_at, data
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """)

    def open_session(self, app, request):
        """Retrieve or create a new session"""
        session_cookie = request.cookies.get(app.config.get('SESSION_COOKIE_NAME', 'session_id'))
        
        if session_cookie:
            try:
                session_uuid = uuid.UUID(session_cookie)
                result = self.cassandra_session.execute(
                    self.select_session, 
                    [session_uuid]
                ).one()

                if result and result.user_email and result.user_id and \
                        (result.expire_at is None or result.expire_at > datetime.utcnow()):
                    session_data = {
                        'user_email': result.user_email,
                        'user_id': str(result.user_id),
                        'session_id': str(result.session_id)
                    }
                    if result.data:
                        session_data.update(result.data)
                    
                    logger.debug(f'Retrieved existing session: {session_cookie}')
                    return CassandraSession(str(session_uuid), initial=session_data)

            except Exception as e:
                logger.error(f"Error retrieving session: {e}")

        # Create new session if none exists or retrieval failed
        new_session_id = str(uuid.uuid4())
        logger.debug(f'Created new session: {new_session_id}')
        return CassandraSession(new_session_id)

    def save_session(self, app, session, response):
        """Save the session and set the cookie"""
        if request.method == 'OPTIONS':
            return

        session_id = session.get('session_id')
        user_email = session.get('user_email')
        user_id = session.get('user_id')

        if not all([session_id, user_email, user_id]):
            logger.debug('Missing required session data, skipping save')
            return

        try:
            # Convert session_id to UUID if it's a string
            if isinstance(session_id, str):
                session_id = uuid.UUID(session_id)
            
            # Convert user_id to UUID if it's a string
            if isinstance(user_id, str):
                user_id = uuid.UUID(user_id)

            now = datetime.utcnow()
            expire_at = now + self.session_lifetime

            # Extract additional data, excluding standard fields
            session_data = {k: v for k, v in dict(session).items() 
                          if k not in ['session_id', 'user_email', 'user_id']}

            # Save session to Cassandra
            self.cassandra_session.execute(
                self.insert_session,
                (
                    session_id,
                    user_email,
                    user_id,
                    now,
                    now,
                    expire_at,
                    session_data
                )
            )

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