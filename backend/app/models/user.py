# File: ./backend/app/models/user.py
# Description: This file defines the User model, which manages user authentication, registration, session management, and user retrieval using Cassandra
#              as the database.
# Classes:
#    [+] User - Represents a user in the application, with methods to manage user authentication, registration, session management, and retrieval.
# Properties:
#    [+] name - The name of the user.
#    [+] email - The email address of the user.
#    [+] user_id - The unique identifier for the user.
#    [+] session_id - The current session identifier associated with the user.
# Methods: 
#    [+] __init__(self, name, email, user_id, session_id=None): Initializes a new User instance with the provided details.
#    [+] get_id(self): Returns the user_id of the user as a string.
#    [+] to_dict(self): Returns the user's details as a dictionary.
#    [+] register(cls, data): Registers a new user in the system and stores the user details in Cassandra.
#    [+] login(cls, data): Authenticates a user by checking the provided credentials against stored records in Cassandra.
#    [+] check_session(cls, session_id): Verifies if a session with the given session_id is still active.
#    [+] logout(cls, session_id): Logs out a user by deleting their session from Cassandra.
#    [+] get(user_id): Fetches the user with the given user_id from the database.
#    [+] update(user_id, name, surname, location, profile_picture): Updates the user profile data in the database.

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import uuid
import logging
import os
import re
from datetime import datetime, timedelta

# Basic email shape check + minimum password length. This is input validation,
# not account/ownership verification (no confirmation email is sent).
_EMAIL_RE = re.compile(r'^[^@\s]+@[^@\s]+\.[^@\s]+$')
_MIN_PASSWORD_LEN = 8


def normalize_email(value):
    """Emails are matched and stored lower-case and trimmed."""
    return (value or '').strip().lower()

from app.db import session as cassandra_session, is_unavailable
from app.utils import image_store, preferences

class User(UserMixin):
    def __init__(self, name, email, user_id, session_id=None):
        self.name = name
        self.email = email
        self.user_id = user_id
        self.surname = None
        self.location = None
        self.profile_picture = None
        # Whether a profile picture is stored. The picture itself is never
        # read here (get_picture serves it): it went out base64-encoded in
        # every check_session and profile response - megabytes per call.
        self.has_picture = False
        # An AI persona account (see backend/agents).
        self.is_agent = False
        # Simple or Advanced (app/utils/preferences.py): presentation only.
        self.ui_mode = preferences.ADVANCED
        self.session_id = session_id


    def to_dict(self):
        # Local import avoids any module load-order coupling with the
        # permissions helper (which reads the credentials table).
        from app.utils.permissions import is_platform_admin
        # No session_id here: a user's data must never carry a session token
        # (routes/login.py returns the new session separately).
        return {
            'name': self.name,
            'user_id': str(self.user_id),
            'email': self.email,
            'surname': self.surname,
            'location': self.location,
            'is_platform_admin': is_platform_admin(self.user_id),
            # The picture itself is served by /api/users/<id>/avatar.
            'has_picture': bool(self.has_picture),
            'is_agent': bool(self.is_agent),
            'ui_mode': self.ui_mode,
        }


    def get_id(self):
        return str(self.user_id)

    @classmethod
    def register(cls, data):
        # Validate required fields up front so missing data is a clean failure
        # rather than an unhandled KeyError -> 500.
        if not data:
            logging.error('Registration failed: no data provided')
            return None
        name = (data.get('name') or '').strip()
        # Stored lower-case: an address is the same whatever its case, and
        # sign-in matches it exactly.
        email = normalize_email(data.get('email'))
        password = data.get('password') or ''
        if not name or not email or not password:
            logging.error('Registration failed: missing name, email or password')
            return None
        # Server-side input validation — never trust the client's checks.
        if not _EMAIL_RE.match(email):
            logging.error('Registration failed: invalid email format')
            return None
        if len(password) < _MIN_PASSWORD_LEN:
            logging.error('Registration failed: password too short')
            return None

        # Reject duplicate emails — otherwise two accounts share an email and
        # login becomes ambiguous.
        existing = cassandra_session.execute(
            "SELECT user_id FROM user_credentials WHERE email = %s",
            (email,)
        ).one()
        if existing:
            logging.error('Registration failed: email already registered')
            return None

        password_hash = generate_password_hash(password)
        user_id = uuid.uuid4()
        logging.info(f'Registering user with user_id: {user_id}')

        query = "INSERT INTO user_credentials (user_id, email, password) VALUES (%s, %s, %s)"
        cassandra_session.execute(query, (user_id, email, password_hash))

        # Store profile data in users table
        query = "INSERT INTO users (user_id, email, name, ui_mode) VALUES (%s, %s, %s, %s)"
        cassandra_session.execute(query, (user_id, email, name, preferences.SIMPLE))

        user = cls(name, email, user_id)
        user.ui_mode = preferences.SIMPLE
        return user

    @classmethod
    def login(cls, data):
        email = normalize_email(data.get('email'))
        password = data.get('password') or ''

        try:
            # Fetch user credentials (email is backed by a secondary index)
            query = "SELECT * FROM user_credentials WHERE email = %s"
            rows = cassandra_session.execute(query, (email,))

            for row in rows:
                if check_password_hash(row.password, password):
                    # Fetch additional user details like name
                    user_details_query = "SELECT user_id, name, ui_mode FROM users WHERE user_id = %s"
                    user_details = cassandra_session.execute(user_details_query, (row.user_id,)).one()

                    if user_details:
                        # The caller (routes/login.py) creates the new session. No
                        # other session of this user is looked up or returned: the
                        # login response used to carry one (a second live token)
                        # inside its user data.
                        user = cls(name=user_details.name, email=row.email, user_id=row.user_id)
                        user.ui_mode = preferences.mode_of(getattr(user_details, 'ui_mode', None))
                        return user
                    else:
                        logging.error('User details not found in the users table')
                        return None
            
            logging.error('Invalid email or password')
            return None

        except Exception as e:
            if is_unavailable(e):
                raise       # an outage, not a wrong password
            logging.error(f'Error during login: {e}')
            return None

    # Session tokens are bearer credentials: they are never written to the logs.
    @classmethod
    def check_session(cls, session_id):
        try:
            query = "SELECT * FROM sessions WHERE session_id = %s"
            rows = cassandra_session.execute(query, (uuid.UUID(session_id),))  # Ensure session_id is converted to UUID

            for row in rows:
                if row.expire_at > datetime.utcnow():
                    if isinstance(row.user_id, uuid.UUID):
                        return row.user_id
                    else:
                        logging.error(f"Invalid user_id found: {row.user_id}")
                        return None
            logging.info('Session is inactive or expired')
            return None
        except Exception as e:
            if is_unavailable(e):
                raise       # an outage, not an expired session
            logging.error(f'Error during session check: {e}')
            return None

    @classmethod
    def logout(cls, session_id):
        try:
            session_uuid = uuid.UUID(session_id)
            query = "DELETE FROM sessions WHERE session_id = %s"
            cassandra_session.execute(query, (session_uuid,))
            logging.info('Session deleted on logout')
        except Exception as e:
            logging.error(f'Error during logout: {e}')

    @classmethod
    def get(cls, user_id):
        try:
            user_id = uuid.UUID(user_id)
        except ValueError as e:
            logging.error(f'Invalid user_id type: {type(user_id)}, value: {user_id}')
            return None

        try:
            logging.info(f'user.py: Fetching user with user_id: {user_id}')
            # writetime() tells whether a picture is set without loading it.
            query = ("SELECT user_id, email, name, surname, location, is_agent, ui_mode, picture_object, writetime(profile_picture) AS picture_wt "
                     "FROM users WHERE user_id = %s")
            rows = cassandra_session.execute(query, (user_id,))

            for row in rows:
                user = cls(name=row.name, email=row.email, user_id=row.user_id)
                user.surname = row.surname
                user.location = row.location
                user.has_picture = row.picture_wt is not None or bool(getattr(row, 'picture_object', None))
                user.is_agent = bool(getattr(row, 'is_agent', False))
                user.ui_mode = preferences.mode_of(getattr(row, 'ui_mode', None))
                return user

            logging.error(f'User not found with user_id: {user_id}')
            return None
        except Exception as e:
            if is_unavailable(e):
                raise       # an outage, not "no such user"
            logging.error(f'Error fetching user: {e}')
            return None

    @classmethod
    def get_picture(cls, user_id):
        """The stored profile picture's bytes, or None (for the avatar endpoint)."""
        try:
            row = cassandra_session.execute(
                "SELECT profile_picture, picture_object FROM users WHERE user_id = %s",
                [uuid.UUID(str(user_id))]).one()
            return image_store.fetch(getattr(row, 'picture_object', None), row.profile_picture) if row else None
        except (ValueError, TypeError):
            return None

    @classmethod
    def update(cls, user_id, name=None, surname=None, location=None, profile_picture=None):
        logging.info(f'Updating user with user_id: {user_id}')
        
        # Ensure user_id is a UUID object
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                logging.error(f'Invalid user_id: {user_id}')
                return None
        
        # Construct the update query dynamically based on provided fields
        update_fields = []
        update_values = []
        
        # None = not sent, leave it. A name can't be blanked; surname and
        # location can be cleared by sending them empty.
        if name and name.strip():
            update_fields.append("name = %s")
            update_values.append(name.strip())
        if surname is not None:
            update_fields.append("surname = %s")
            update_values.append(surname.strip() or None)
        if location is not None:
            from app.utils import places    # imported here: places imports models
            if places.words_changed(user_id, location):
                update_fields.append("place = null")
            update_fields.append("location = %s")
            update_values.append(location.strip() or None)
        if profile_picture:
            obj, blob = image_store.store(profile_picture, 'avatar')
            update_fields += ["profile_picture = %s", "picture_object = %s"]
            update_values += [blob, obj]
        
        if not update_fields:
            logging.error('No fields provided to update')
            return None

        # Append user_id for WHERE clause
        update_values.append(user_id)

        query = f"UPDATE users SET {', '.join(update_fields)} WHERE user_id = %s"
        
        try:
            cassandra_session.execute(query, tuple(update_values))
            # Pass user_id as string to cls.get
            return cls.get(str(user_id))
        except Exception as e:
            logging.error(f'Failed to update user profile: {e}')
            return None
