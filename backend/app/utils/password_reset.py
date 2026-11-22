"""One-time password reset tokens. Emailed to a member who forgot their
password (app/utils/email_accounts.py), or issued by an admin to pass on
(app/routes/admin.py); the member redeems it on the web's /reset-password page
(app/routes/account.py). Only a hash of the token is stored, rows expire on
their own, and a token works once."""
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


def issue_reset_token(user_id, created_by=None, hours=VALID_HOURS):
    """A fresh token for `user_id`: (token, expires_at). No `created_by`: it was emailed."""
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(hours=hours)
    session.execute(
        'INSERT INTO password_resets (token_hash, user_id, created_by, expires_at) VALUES (%s, %s, %s, %s) '
        f'USING TTL {int(hours * 3600)}',
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


def was_emailed(token):
    """Using such a token shows the member has the mailbox."""
    row = session.execute('SELECT created_by FROM password_resets WHERE token_hash = %s', [_hash(token)]).one()
    return bool(row) and row.created_by is None


def revoke(user_id):
    """Every link still out for this member (the table holds a day's at most)."""
    uid = uuid.UUID(str(user_id))
    for row in session.execute('SELECT token_hash, user_id FROM password_resets'):
        if row.user_id == uid:
            session.execute('DELETE FROM password_resets WHERE token_hash = %s', [row.token_hash])


def spend(token):
    session.execute('DELETE FROM password_resets WHERE token_hash = %s', [_hash(token)])
