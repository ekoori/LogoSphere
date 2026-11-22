"""Announcements: a few words from a group's managers to its members.

A sphere's are read by its members. An alliance's or project's by its own
members and the rest of its sphere, who see the group anyway.
"""
from datetime import datetime

from cassandra.util import unix_time_from_uuid1, uuid_from_time

from app.db import session
from app.utils.access import as_uuid

DDL = ('CREATE TABLE IF NOT EXISTS announcements ('
       'group_id uuid, announcement_id timeuuid, author_id uuid, body text, '
       'PRIMARY KEY (group_id, announcement_id)) WITH CLUSTERING ORDER BY (announcement_id DESC)')
TEXT_MAX, SHOWN, PER_DAY = 2000, 50, 10


def ensure_tables():
    session.execute(DDL)


def readable(sight, group):
    if sight.id is None:
        return False
    if sight.admin or sight.id in group.members:
        return True
    return group.kind != 'sphere' and bool(group.sphere_id) and sight.member_of(group.sphere_id)


def key_of(value):
    key = as_uuid(value)
    return key if key and key.version == 1 else None


def said_at(announcement_id):
    return datetime.utcfromtimestamp(round(unix_time_from_uuid1(announcement_id), 3))


def make(group, author, body):
    key = uuid_from_time(datetime.utcnow())
    session.execute('INSERT INTO announcements (group_id, announcement_id, author_id, body) VALUES (%s, %s, %s, %s)',
                    [group.id, key, as_uuid(author), body])
    return key


def of(group_id):
    return list(session.execute(
        f'SELECT announcement_id, author_id, body FROM announcements WHERE group_id = %s LIMIT {SHOWN}',
        [as_uuid(group_id)]))


def get(group_id, announcement_id):
    gid, key = as_uuid(group_id), key_of(announcement_id)
    if not gid or not key:
        return None
    return session.execute('SELECT announcement_id, author_id, body FROM announcements '
                           'WHERE group_id = %s AND announcement_id = %s', [gid, key]).one()


def remove(group_id, announcement_id):
    session.execute('DELETE FROM announcements WHERE group_id = %s AND announcement_id = %s',
                    [as_uuid(group_id), key_of(announcement_id)])


def forget_group(group_id):
    session.execute('DELETE FROM announcements WHERE group_id = %s', [as_uuid(group_id)])


def export(user_id):
    me = as_uuid(user_id)
    return [{'group_id': str(r.group_id), 'text': r.body, 'at': said_at(r.announcement_id)}
            for r in session.execute('SELECT group_id, announcement_id, author_id, body FROM announcements')
            if r.author_id == me]
