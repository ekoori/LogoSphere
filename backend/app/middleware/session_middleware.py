# File: ./backend/app/middleware/session_middleware.py
# Description: Middleware for session validation and management
#
# Auth model: sessions are server-stored (Cassandra `sessions` table, opaque
# random session_id, 30-day TTL, instantly revocable on logout) — not JWT.
# We keep the DB-backed model because it gives us cheap, immediate revocation
# and doesn't require rotating a signing key; a stateless JWT would need a
# blacklist for logout/revocation anyway, which is most of the complexity of
# a session store without the benefit.
#
# Token transport: the documented API contract is a standard
# `Authorization: Bearer <session_id>` header — never a query parameter (query
# strings end up in server logs, proxy logs, and browser history). The
# reference web client additionally receives the same token as an httpOnly,
# Secure, SameSite=Lax cookie on login; that cookie is what the browser SPA
# actually authenticates with (a JS-readable Authorization header would be
# strictly worse for the SPA, since it'd be stealable via XSS — the httpOnly
# cookie can't be read by injected script). Both transports resolve to the
# same server-stored session row, so either is valid on any request.
from functools import wraps
from flask import request, jsonify, current_app
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)


def get_session_token():
    """Extract the bearer token for this request: the standard
    `Authorization: Bearer <token>` header takes priority, falling back to the
    session cookie the browser SPA sends. Never accepts a query parameter."""
    auth_header = request.headers.get('Authorization', '')
    if auth_header.startswith('Bearer '):
        token = auth_header[len('Bearer '):].strip()
        if token:
            return token
    return request.cookies.get('session_id')


def validate_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)

        session_id = get_session_token()
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