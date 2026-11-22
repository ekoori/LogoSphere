"""Blocking and reporting.

A block is private: whoever is blocked isn't told, and what they're refused
reads like any other refusal. While one stands, in either direction, the two
can't message each other, follow each other, take up each other's openings,
acknowledge on each other's trails or exchanges, or be found near each other.

A report goes to the platform's administrators with what was reported as it
read then. It is the only way an administrator sees anything of a message.
"""
import uuid
from datetime import datetime

from app.db import session
from app.utils.access import as_uuid

DDL = (
    'CREATE TABLE IF NOT EXISTS blocks ('
    'user_id uuid, blocked_id uuid, made_at timestamp, PRIMARY KEY (user_id, blocked_id))',
    'CREATE TABLE IF NOT EXISTS reports ('
    'report_id uuid PRIMARY KEY, reporter_id uuid, subject_id uuid, kind text, item_id text, context_id uuid, '
    'excerpt text, note text, made_at timestamp, status text, handled_by uuid, handled_at timestamp, outcome text)',
)
# Notifications that are only social: none arrive from someone you blocked.
SOCIAL = ('message', 'new_follower', 'acknowledgement', 'acknowledgement_highlighted', 'event_new', 'announcement',
          'invite_accepted')

OPEN, HANDLED, DISMISSED = 'open', 'handled', 'dismissed'
EXCERPT_MAX, NOTE_MAX = 500, 1000


def ensure_tables():
    for statement in DDL:
        session.execute(statement)


def blocked(by, person):
    a, b = as_uuid(by), as_uuid(person)
    if not a or not b:
        return False
    return bool(session.execute('SELECT blocked_id FROM blocks WHERE user_id = %s AND blocked_id = %s', [a, b]).one())


def between(one, other):
    return blocked(one, other) or blocked(other, one)


def hidden_from(user_id):
    """Everyone with a block between them and this member (the table is small)."""
    me = as_uuid(user_id)
    out = set()
    for row in session.execute('SELECT user_id, blocked_id FROM blocks'):
        if row.user_id == me:
            out.add(row.blocked_id)
        elif row.blocked_id == me:
            out.add(row.user_id)
    return out


def blocked_by(user_id):
    """[(who, since)] that this member blocked."""
    rows = session.execute('SELECT blocked_id, made_at FROM blocks WHERE user_id = %s', [as_uuid(user_id)])
    return [(row.blocked_id, row.made_at) for row in rows]


def block(by, person):
    a, b = as_uuid(by), as_uuid(person)
    session.execute('INSERT INTO blocks (user_id, blocked_id, made_at) VALUES (%s, %s, %s)', [a, b, datetime.utcnow()])
    for follower, followed in ((a, b), (b, a)):
        session.execute('DELETE FROM follows WHERE follower_id = %s AND followee_id = %s', [follower, followed])


def unblock(by, person):
    session.execute('DELETE FROM blocks WHERE user_id = %s AND blocked_id = %s', [as_uuid(by), as_uuid(person)])


# -- Reports -------------------------------------------------------------------
def file_report(reporter, subject, kind, item_id, context_id, excerpt, note):
    report_id = uuid.uuid4()
    session.execute(
        'INSERT INTO reports (report_id, reporter_id, subject_id, kind, item_id, context_id, excerpt, note, made_at, status) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        [report_id, as_uuid(reporter), as_uuid(subject), kind, str(item_id), as_uuid(context_id),
         (excerpt or '')[:EXCERPT_MAX], (note or '')[:NOTE_MAX], datetime.utcnow(), OPEN])
    return report_id


def report(report_id):
    rid = as_uuid(report_id)
    return session.execute('SELECT * FROM reports WHERE report_id = %s', [rid]).one() if rid else None


def all_reports():
    return sorted(session.execute('SELECT * FROM reports'), key=lambda r: r.made_at or datetime.min, reverse=True)


def settle(report_id, admin, status, outcome):
    session.execute('UPDATE reports SET status = %s, handled_by = %s, handled_at = %s, outcome = %s WHERE report_id = %s',
                    [status, as_uuid(admin), datetime.utcnow(), (outcome or '')[:NOTE_MAX], as_uuid(report_id)])


def administrators():
    return [row.user_id for row in session.execute('SELECT user_id, is_platform_admin FROM users') if row.is_platform_admin]


# -- Accounts ------------------------------------------------------------------
def forget(user_id):
    """A removed account's blocks, both ways. Reports stay: they are the safety record."""
    me = as_uuid(user_id)
    for row in session.execute('SELECT user_id, blocked_id FROM blocks'):
        if me in (row.user_id, row.blocked_id):
            session.execute('DELETE FROM blocks WHERE user_id = %s AND blocked_id = %s', [row.user_id, row.blocked_id])
