"""Invitation links, to LogoSphere or into a group.

The link's code is kept only as a hash, and it rides in the URL's fragment. A
link works for two weeks and 25 people, until it's revoked, and only while
whoever made it could still invite: in an open group any member may, where
joining needs approval only its managers (their link is the approval). A link
into an alliance or project also takes people into its sphere, so it needs
the right to invite there too.
"""
import hashlib
import secrets
from datetime import datetime, timedelta

from app.db import session
from app.utils import groups, safety
from app.utils.access import as_uuid
from app.utils.permissions import can_manage_entity

DAYS, MOST_USES, MOST_LIVE = 14, 25, 20
TTL = DAYS * 86400
DDL = (
    'CREATE TABLE IF NOT EXISTS invites ('
    'invite_hash text PRIMARY KEY, made_by uuid, group_id uuid, made_at timestamp) '
    f'WITH default_time_to_live = {TTL}',
    'CREATE TABLE IF NOT EXISTS invite_uses ('
    'invite_hash text, user_id uuid, used_at timestamp, PRIMARY KEY (invite_hash, user_id)) '
    f'WITH default_time_to_live = {TTL}',
)


def ensure_tables():
    for statement in DDL:
        session.execute(statement)


def hashed(code):
    if not isinstance(code, str) or not 16 <= len(code) <= 100:
        return None
    return hashlib.sha256(code.encode('utf-8', 'replace')).hexdigest()       # JSON can hold half a character


def _person(user_id):
    uid = as_uuid(user_id)
    return session.execute('SELECT user_id, name, surname, is_agent FROM users WHERE user_id = %s', [uid]).one() if uid else None


def name_of(person):
    return f"{person.name or ''} {person.surname or ''}".strip() or 'A member'


def may_invite(user_id, group=None):
    me = _person(user_id)
    if not me or me.is_agent:
        return False
    if not group:
        return True
    if group.closed:
        return False
    manages = can_manage_entity(group.id, me.user_id)
    if not manages and (me.user_id not in group.members or group.join_policy != 'open'):
        return False
    if group.kind == 'sphere' or not group.sphere_id:
        return True
    return may_invite(me.user_id, groups.find(group.sphere_id))


def uses(invite_hash):
    return [r.user_id for r in session.execute('SELECT user_id FROM invite_uses WHERE invite_hash = %s', [invite_hash])]


def live(invite_hash):
    """(the invitation, who made it, its group) while it works, else None."""
    if not invite_hash:
        return None
    row = session.execute('SELECT invite_hash, made_by, group_id, made_at FROM invites WHERE invite_hash = %s',
                          [invite_hash]).one()
    if not row or not row.made_by:
        return None
    group = groups.find(row.group_id) if row.group_id else None
    if row.group_id and not group:
        return None
    maker = _person(row.made_by)
    if not maker or not may_invite(maker.user_id, group) or len(uses(invite_hash)) >= MOST_USES:
        return None
    return row, maker, group


def make(user_id, group=None):
    code = secrets.token_urlsafe(18)
    key = hashed(code)
    at = datetime.utcnow()
    session.execute('INSERT INTO invites (invite_hash, made_by, group_id, made_at) VALUES (%s, %s, %s, %s)',
                    [key, as_uuid(user_id), group.id if group else None, at])
    return code, key, at + timedelta(days=DAYS)


def made_by(user_id):
    me = as_uuid(user_id)
    rows = [r for r in session.execute('SELECT invite_hash, made_by, group_id, made_at FROM invites') if r.made_by == me]
    return sorted(rows, key=lambda r: r.made_at, reverse=True)


def revoke(invite_hash):
    session.execute('DELETE FROM invites WHERE invite_hash = %s', [invite_hash])
    session.execute('DELETE FROM invite_uses WHERE invite_hash = %s', [invite_hash])


def accept(invite_hash, user_id, arriving=False):
    """(who invited, the group, whether that was news), or None when it doesn't work.

    `arriving`: the account was just made with it. Someone who is here already
    and gains nothing by a link doesn't use one of its places up."""
    found, joiner = live(invite_hash), _person(user_id)
    if not found or not joiner or joiner.is_agent:
        return None
    row, maker, group = found
    if maker.user_id == joiner.user_id:
        return maker, group, False
    if safety.between(maker.user_id, joiner.user_id):
        return None
    joining = bool(group) and joiner.user_id not in group.members
    if not joining and not arriving:
        return maker, group, False
    if joining:
        name = name_of(joiner)
        if group.kind != 'sphere' and group.sphere_id:
            parent = groups.find(group.sphere_id)
            if parent and joiner.user_id not in parent.members:
                groups.add_member(parent, joiner.user_id, name)
        groups.add_member(group, joiner.user_id, name)
    # Dies with its invitation, rather than two weeks after the last use.
    left = max(60, TTL - int((datetime.utcnow() - row.made_at).total_seconds()))
    session.execute(f'INSERT INTO invite_uses (invite_hash, user_id, used_at) VALUES (%s, %s, %s) USING TTL {left}',
                    [invite_hash, joiner.user_id, datetime.utcnow()])
    return maker, group, True


def forget_group(group_id):
    gid = as_uuid(group_id)
    for row in session.execute('SELECT invite_hash, group_id FROM invites'):
        if row.group_id == gid:
            revoke(row.invite_hash)


def export(user_id):
    return [{'group_id': str(r.group_id) if r.group_id else None, 'made_at': r.made_at,
             'joined': len(uses(r.invite_hash))} for r in made_by(user_id)]


def forget(user_id):
    for row in made_by(user_id):
        revoke(row.invite_hash)
