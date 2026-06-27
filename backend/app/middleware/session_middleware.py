# File: ./backend/app/middleware/session_middleware.py
# Description: Middleware for session validation and management
from functools import wraps
from flask import request, jsonify, current_app
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

def validate_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)

        # Check both cookie and header for session_id
        session_id = request.cookies.get('session_id') or request.headers.get('session_id')
        logger.debug(f'Validating session: {session_id}')

        if not session_id:
            logger.error("No session_id found in cookies or headers")
            response = jsonify({'message': 'No session found'})
            response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response, 401

        try:
            # session_id is the partition key, so look it up directly and check
            # expiry in Python (avoids a non-key range predicate / ALLOW FILTERING).
            result = current_app.session_interface.cassandra_session.execute(
                "SELECT user_id, user_email, expire_at FROM sessions WHERE session_id = %s",
                [uuid.UUID(session_id)]
            ).one()

            if result and result.expire_at and result.expire_at > datetime.utcnow():
                # Add user_id to kwargs
                kwargs['user_id'] = result.user_id
                return f(*args, **kwargs)
            else:
                logger.error("Invalid or expired session")
                response = jsonify({'message': 'Invalid or expired session'})
                response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
                response.headers.add('Access-Control-Allow-Credentials', 'true')
                return response, 401

        except Exception as e:
            logger.error(f"Session validation error: {str(e)}")
            response = jsonify({'message': 'Session validation failed'})
            response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
            response.headers.add('Access-Control-Allow-Credentials', 'true')
            return response, 401

    return decorated_function