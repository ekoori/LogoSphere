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
#    [+] get_existing_session(cls, user_id): Retrieves an existing session ID for a user if one exists and is active.
#    [+] check_session(cls, session_id): Verifies if a session with the given session_id is still active.
#    [+] logout(cls, session_id): Logs out a user by deleting their session from Cassandra.
#    [+] get(user_id): Fetches the user with the given user_id from the database.
#    [+] update(user_id, name, surname, location, profile_picture): Updates the user profile data in the database.

from cassandra.cluster import Cluster
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
import uuid
import logging
import os
from datetime import datetime, timedelta
import base64

# Set up Cassandra session
# Host(s) configurable via CASSANDRA_HOST (comma-separated), defaults to localhost.
CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(CASSANDRA_HOSTS)
cassandra_session = cluster.connect('logosphere')

class User(UserMixin):
    def __init__(self, name, email, user_id, session_id=None):
        self.name = name
        self.email = email
        self.user_id = user_id
        self.surname = None
        self.location = None
        self.profile_picture = None
        self.session_id = session_id


    def to_dict(self):
        return {
            'name': self.name,
            'user_id': str(self.user_id),
            'email': self.email,
            'session_id': str(self.session_id) if self.session_id else None,
            'surname': self.surname,
            'location': self.location,
            'profile_picture': base64.b64encode(self.profile_picture).decode('utf-8') if self.profile_picture else None
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
        name = data.get('name')
        email = data.get('email')
        password = data.get('password')
        if not name or not email or not password:
            logging.error('Registration failed: missing name, email or password')
            return None

        # Reject duplicate emails — otherwise two accounts share an email and
        # login becomes ambiguous.
        existing = cassandra_session.execute(
            "SELECT user_id FROM user_credentials WHERE email = %s",
            (email,)
        ).one()
        if existing:
            logging.error(f'Registration failed: email already registered: {email}')
            return None

        password_hash = generate_password_hash(password)
        user_id = uuid.uuid4()
        logging.info(f'Registering user with user_id: {user_id}')

        query = "INSERT INTO user_credentials (user_id, email, password) VALUES (%s, %s, %s)"
        cassandra_session.execute(query, (user_id, email, password_hash))

        # Store profile data in users table
        query = "INSERT INTO users (user_id, email, name) VALUES (%s, %s, %s)"
        cassandra_session.execute(query, (user_id, email, name))

        return cls(name, email, user_id)

    @classmethod
    def login(cls, data):
        email = data['email']
        password = data['password']
        logging.info(f'Attempting login for email: {email}')

        try:
            # Fetch user credentials (email is backed by a secondary index)
            query = "SELECT * FROM user_credentials WHERE email = %s"
            rows = cassandra_session.execute(query, (email,))

            for row in rows:
                if check_password_hash(row.password, password):
                    # Fetch additional user details like name
                    user_details_query = "SELECT user_id, name FROM users WHERE user_id = %s"
                    user_details = cassandra_session.execute(user_details_query, (row.user_id,)).one()

                    if user_details:
                        # Create User instance with all required fields
                        user = cls(name=user_details.name, email=row.email, user_id=row.user_id)

                        # Get existing session ID, if any
                        existing_session_id = cls.get_existing_session(user.user_id)
                        if existing_session_id:
                            user.session_id = str(existing_session_id)
                        else:
                            user.session_id = None

                        logging.info(f'User logged in with session_id: {user.session_id}')
                        return user
                    else:
                        logging.error('User details not found in the users table')
                        return None
            
            logging.error('Invalid email or password')
            return None

        except Exception as e:
            logging.error(f'Error during login: {e}')
            return None

    @classmethod
    def get_existing_session(cls, user_id):
        # user_id is backed by a secondary index; filter expiry in Python so we
        # avoid a non-key range predicate (which would force ALLOW FILTERING).
        query = "SELECT session_id, expire_at FROM sessions WHERE user_id = %s"
        rows = cassandra_session.execute(query, (user_id,))

        now = datetime.utcnow()
        for row in rows:
            if row.expire_at and row.expire_at > now:
                return row.session_id

        return None

    @classmethod
    def check_session(cls, session_id):
        try:
            logging.info(f'Checking session with session_id: {session_id}')
            query = "SELECT * FROM sessions WHERE session_id = %s"
            rows = cassandra_session.execute(query, (uuid.UUID(session_id),))  # Ensure session_id is converted to UUID

            for row in rows:
                if row.expire_at > datetime.utcnow():
                    logging.info(f'Session is active for session_id: {session_id}')
                    if isinstance(row.user_id, uuid.UUID):
                        return row.user_id
                    else:
                        logging.error(f"Invalid user_id found: {row.user_id}")
                        return None
            logging.error(f'Session is inactive or expired for session_id: {session_id}')
            return None
        except Exception as e:
            logging.error(f'Error during session check: {e}')
            return None

    @classmethod
    def logout(cls, session_id):
        try:
            logging.info(f'Logging out session with session_id: {session_id}')
            session_uuid = uuid.UUID(session_id)
            query = "DELETE FROM sessions WHERE session_id = %s"
            result = cassandra_session.execute(query, (session_uuid,))
            logging.info(f'Session with session_id {session_id} has been deleted. Result: {result}')
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
            query = "SELECT user_id, email, name, surname, location, profile_picture FROM users WHERE user_id = %s"
            rows = cassandra_session.execute(query, (user_id,))

            for row in rows:
                user = cls(name=row.name, email=row.email, user_id=row.user_id)
                user.surname = row.surname
                user.location = row.location
                user.profile_picture = row.profile_picture
                return user

            logging.error(f'User not found with user_id: {user_id}')
            return None
        except Exception as e:
            logging.error(f'Error fetching user: {e}')
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
        
        if name:
            update_fields.append("name = %s")
            update_values.append(name)
        if surname:
            update_fields.append("surname = %s")
            update_values.append(surname)
        if location:
            update_fields.append("location = %s")
            update_values.append(location)
        if profile_picture:
            update_fields.append("profile_picture = %s")
            update_values.append(profile_picture)
        
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
