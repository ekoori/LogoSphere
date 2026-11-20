"""One-time password reset tokens. An admin issues one for a member who forgot
their password (app/routes/admin.py); the member redeems it on the web's
/reset-password page (app/routes/account.py). Only a hash of the token is
stored, rows expire on their own after a day, and a token works once."""
import hashlib
import secrets
import uuid
from datetime import datetime, timedelta

from app.db import session

VALID_HOURS = 24


def ensure_tables():
    # Not `token`: CQL reserves it (a column named so took production down once).
    session.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            token_hash text PRIMARY KEY, user_id uuid, created_by uuid, expires_at timestamp)""")


def _hash(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def issue_reset_token(user_id, created_by=None):
    """A fresh token for `user_id`: (token, expires_at)."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=VALID_HOURS)
    session.execute(
        'INSERT INTO password_resets (token_hash, user_id, created_by, expires_at) VALUES (%s, %s, %s, %s) '
        f'USING TTL {VALID_HOURS * 3600}',
        [_hash(token), uuid.UUID(str(user_id)), created_by, expires_at])
    return token, expires_at


def holder(token):
    """The member a live token belongs to, or None (unknown, used or expired)."""
    if not token or len(token) > 200:
        return None
    row = session.execute('SELECT user_id, expires_at FROM password_resets WHERE token_hash = %s', [_hash(token)]).one()
    if not row or not row.expires_at or row.expires_at <= datetime.utcnow():
        return None
    return row.user_id


def spend(token):
    session.execute('DELETE FROM password_resets WHERE token_hash = %s', [_hash(token)])
