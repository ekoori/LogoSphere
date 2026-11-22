"""Passwords, sessions and removing an account — shared by the member's own
account routes (app/routes/account.py) and the admin console (app/routes/admin.py)."""
import logging
import uuid

from werkzeug.security import check_password_hash, generate_password_hash

from app.db import session
from app.models.openings import Service

logger = logging.getLogger(__name__)

MIN_PASSWORD_LEN = 8        # the same rule registration applies (app/models/user.py)


def password_matches(user_id, password):
    row = session.execute('SELECT password FROM user_credentials WHERE user_id = %s',
                          [uuid.UUID(str(user_id))]).one()
    return bool(row and row.password and password and check_password_hash(row.password, password))


def set_password(user_id, password):
    session.execute('UPDATE user_credentials SET password = %s WHERE user_id = %s',
                    [generate_password_hash(password), uuid.UUID(str(user_id))])


def end_sessions(user_id, keep=None):
    """Signs the member out everywhere except the session `keep`; returns how many ended."""
    keep = uuid.UUID(str(keep)) if keep else None
    ended = 0
    for r in session.execute('SELECT session_id FROM sessions WHERE user_id = %s', [uuid.UUID(str(user_id))]):
        if r.session_id != keep:
            session.execute('DELETE FROM sessions WHERE session_id = %s', [r.session_id])
            ended += 1
    return ended


def remove_account(user_id):
    """Removes an account: credentials, sessions, profile, value cards,
    notifications, follows and memberships. What the person did stays (their
    openings are withdrawn; exchanges and receipts remain as history under
    their name)."""
    # Imported here: the entity routes import models that import this module's neighbours.
    from app.routes.entities import KINDS, _members, _roles, _remove_member
    from app.utils.permissions import forget_admin_flag
    from app.utils.search_vectors import invalidate_index

    tid = uuid.UUID(str(user_id))
    # Memberships (participants / members lists + role maps) in every entity.
    for kind, k in KINDS.items():
        for entity in k['model'].get_all():
            if tid in _members(entity, k) or tid in _roles(entity, k):
                _remove_member(entity, k, tid)
    # Their current openings are withdrawn (acceptances cleared with them).
    for s in Service.get_all():
        if s.is_current and s.provider_id == tid and s.status not in ('Cancelled', 'Completed'):
            Service.cancel(s.service_id)
            for a in Service.acceptances(s.service_id, status='pending'):
                Service.remove_acceptance(s.service_id, uuid.UUID(a['accepter_id']))
    # Follows in both directions (followee side needs a scan - the table is small).
    session.execute('DELETE FROM follows WHERE follower_id = %s', [tid])
    for r in session.execute('SELECT follower_id, followee_id FROM follows'):
        if r.followee_id == tid:
            session.execute('DELETE FROM follows WHERE follower_id = %s AND followee_id = %s', [r.follower_id, tid])
    from app.utils.meaning_graph import forget_judge
    forget_judge(tid)
    end_sessions(tid)
    session.execute('DELETE FROM value_cards WHERE user_id = %s', [tid])
    session.execute('DELETE FROM notifications WHERE user_id = %s', [tid])
    session.execute('DELETE FROM user_credentials WHERE user_id = %s', [tid])
    session.execute('DELETE FROM users WHERE user_id = %s', [tid])
    forget_admin_flag(tid)
    invalidate_index()
