# File: ./backend/app/routes/login.py
# Description: This file manages user authentication and session management for the TrustSphere platform.
#              It defines the routes for user login, logout, and session verification.
# Classes: None
# Properties: None
# Methods: 
#    [+] load_user(user_id): Retrieves a user by their user_id, used by Flask-Login for session management.
#    [+] login(): Handles the POST request for user login, verifies user credentials, creates a session, and sets the session cookie.
#    [+] logout(): Handles the POST request for user logout, clears the session cookie, and removes the session from the database.
#    [+] check_session(): Handles GET and POST requests to verify if a session is active or inactive.
#    [+] is_valid_uuid(uuid_to_test, version=4): Utility function to validate if a string is a valid UUID of a specified version.

import logging
import uuid
from datetime import datetime, timedelta

from flask import request, jsonify, session, make_response, current_app
from flask_login import login_user, logout_user, current_user

from app.models.user import User

logger = logging.getLogger(__name__)


def load_user(user_id):
    """Load user by ID."""
    logger.info(f'Loading user with user_id: {user_id}')
    return User.get(user_id)


def login():
    if request.method == 'OPTIONS':
        response = make_response('')
        return response, 200

    try:
        data = request.get_json()
        logger.debug(f'Login data received: {data}')
        
        # Authenticate user
        user = User.login(data)
        if user:
            session_id = str(uuid.uuid4())
            user_id = str(user.user_id)
            
            session_data = {
                'session_id': session_id,
                'user_email': user.email,
                'user_id': user_id,
                'fresh': 'true'
            }
            
            logger.info(f'User {user.email} logged in successfully')
            
            # Create response
            response = make_response(jsonify({
                'message': 'Login successful',
                'data': user.to_dict()
            }))

            # Set cookie. `secure` follows app config (SESSION_COOKIE_SECURE),
            # which is driven by an env var so production (HTTPS) can enable it.
            response.set_cookie(
                'session_id',
                session_id,
                httponly=True,
                secure=current_app.config.get('SESSION_COOKIE_SECURE', False),
                samesite=current_app.config.get('SESSION_COOKIE_SAMESITE', 'Lax'),
                path="/",
                max_age=24 * 60 * 60,
                domain=None  # Allow the browser to set the appropriate domain
            )

            # Save session
            now = datetime.utcnow()
            expire_at = now + timedelta(hours=24)
            
            current_app.session_interface.cassandra_session.execute(
                """
                INSERT INTO sessions (
                    session_id, user_email, user_id, creation_time, 
                    last_access_time, expire_at, data
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    uuid.UUID(session_id),
                    user.email,
                    uuid.UUID(user_id),
                    now,
                    now,
                    expire_at,
                    {str(k): str(v) for k, v in session_data.items()}
                )
            )

            logger.info(f'Session saved with ID: {session_id}')
            return response, 200

        else:
            logger.warning('Invalid login credentials')
            response = jsonify({'message': 'Invalid email or password'})
            return response, 401

    except Exception as e:
        logger.error(f'Login error: {str(e)}')
        response = jsonify({'error': 'Internal server error during login'})
        return response, 500

def check_session():
    """Check if the current session is valid."""
    if request.method == 'OPTIONS':
        response = make_response('')
        return response, 200

    try:
        session_id = request.cookies.get('session_id')
        logger.info(f'Checking session for session_id: {str(session_id)}')

        if not session_id:
            logger.info(f'No valid session_id found in cookies')
            response = jsonify({'status': 'inactive', 'user_id': None})
            return response, 200

        # Convert session_id to string before querying
        session_id_str = str(session_id)

        # Query session directly
        result = current_app.session_interface.cassandra_session.execute(
            "SELECT user_id, user_email FROM sessions WHERE session_id = %s",
            [uuid.UUID(session_id_str)]
        ).one()

        if result:
            # User.get expects a string user_id (it calls uuid.UUID() on it);
            # result.user_id comes back from the driver as a UUID object.
            user = User.get(str(result.user_id))
            if user:
                response = jsonify({
                    'status': 'active',
                    'user_id': str(user.user_id),
                    'user_data': user.to_dict()
                })
                logger.info(f'Active session found for user: {user.user_id}')
            else:
                response = jsonify({'status': 'inactive', 'user_id': None})
                logger.warning(f'User not found for user_id: {result.user_id}')
        else:
            response = jsonify({'status': 'inactive', 'user_id': None})
            logger.info('Session is inactive or expired')

        return response, 200

    except Exception as e:
        logger.error(f'Session check error: {str(e)}')
        response = jsonify({'error': 'Internal server error during session check'})
        return response, 500

def logout():
    """Handle user logout."""
    if request.method == 'OPTIONS':
        response = make_response('')
        return response, 200
    
    try:
        session_id = request.cookies.get('session_id')
        logger.info(f'Retrieved session_id from cookie: {session_id}')

        if not session_id or not is_valid_uuid(session_id):
            logger.error(f'Invalid session_id retrieved from cookie: {session_id}')
            response = jsonify({'error': 'Invalid session_id'})
            return response, 400

        # Call the logout function to delete the session from the database
        User.logout(session_id)
        logout_user()

        # Clear the session cookie and remove session data
        response = jsonify({'success': True})
        response.set_cookie('session_id', '', expires=0, path='/')
        session.clear()  # Clear the session data
        
        logger.info(f'Session deleted and user logged out with session_id: {session_id}')
        return response, 200
    except Exception as e:
        logger.error(f'Error during logout: {e}')
        response = jsonify({'error': 'Logout failed due to an internal error'})
        return response, 500
 

def is_valid_uuid(uuid_to_test, version=4):
    """Validate UUID string."""
    try:
        uuid_obj = uuid.UUID(uuid_to_test, version=version)
        return str(uuid_obj) == uuid_to_test
    except (ValueError, AttributeError):
        return False

# Make sure to export all the functions that are imported elsewhere
__all__ = ['load_user', 'login', 'logout', 'check_session']