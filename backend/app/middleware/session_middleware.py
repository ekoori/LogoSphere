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


def _refused(message, status=401):
    response = jsonify({'message': message})
    response.headers.add('Access-Control-Allow-Origin', request.headers.get('Origin'))
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response, status


def validate_session(f):
    """Runs the route with the session's user_id, or answers 401. Only the
    session lookup is guarded here: an error inside the route used to come back
    as 401 "Session validation failed" too, which signs clients out (the app on
    any 401) for what was really a bug or a database outage."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if request.method == 'OPTIONS':
            return f(*args, **kwargs)

        session_id = get_session_token()
        if not session_id:
            return _refused('No session found')
        try:
            token = uuid.UUID(session_id)
        except ValueError:
            return _refused('Invalid or expired session')

        try:
            # session_id is the partition key, so look it up directly and check
            # expiry in Python (avoids a non-key range predicate / ALLOW FILTERING).
            result = current_app.session_interface.cassandra_session.execute(
                "SELECT user_id, user_email, expire_at FROM sessions WHERE session_id = %s",
                [token]
            ).one()
        except Exception as e:
            from app.db import is_unavailable, UNAVAILABLE
            if is_unavailable(e):
                logger.warning('Session lookup failed, database unavailable: %s', e)
                return _refused(UNAVAILABLE['message'], 503)
            logger.error(f"Session validation error: {e}")
            return _refused('Session validation failed')

        if not (result and result.expire_at and result.expire_at > datetime.utcnow()):
            logger.info("Invalid or expired session")
            return _refused('Invalid or expired session')

        kwargs['user_id'] = result.user_id
        return f(*args, **kwargs)

    return decorated_function
