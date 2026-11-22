"""Private messages, always between two people.

"Message everyone who responded" is many private messages rather than a group:
respondents don't learn who else responded, and answers come to the sender alone.

Who may start: people who share a sphere; someone who follows you, or who chose
to be found nearby; and about an opening, its poster and those who responded.
Whoever has already talked may carry on, until one blocks the other. AI
personas neither read nor send messages, so none reach an AI provider.

A conversation's id comes from the pair, so it can only be reached as one of
the two. No administrator reads it: only what is reported (app/utils/safety).
"""
import uuid
from datetime import datetime

from cassandra.util import unix_time_from_uuid1, uuid_from_time

from app.db import session
from app.models.follow import Follow
from app.models.openings import Service
from app.models.spheres import Sphere
from app.utils import places, safety
from app.utils.access import Sight, as_uuid
from app.utils.permissions import can_manage_entity, is_platform_admin

DDL = (
    'CREATE TABLE IF NOT EXISTS message_inbox ('
    'user_id uuid, other_id uuid, last_at timestamp, last_from uuid, last_body text, read_at timestamp, '
    'PRIMARY KEY (user_id, other_id))',
    'CREATE TABLE IF NOT EXISTS direct_messages ('
    'conversation_id uuid, message_id timeuuid, sender_id uuid, body text, opening_id uuid, '
    'PRIMARY KEY (conversation_id, message_id)) WITH CLUSTERING ORDER BY (message_id DESC)',
)
PAIRS = uuid.UUID('6f0b7f52-3c1e-4d4a-9a7e-2f6c8d1b5e30')     # the namespace of conversation ids
TEXT_MAX, PREVIEW_MAX, PAGE = 2000, 140, 50
PER_HOUR, NEW_PER_DAY = 100, 20
REMOVED = '(removed)'

# One refusal for "not allowed" and "they blocked you": a block isn't told.
NOT_ALLOWED = ("You can't message this person. You can write to people in your spheres, to people who follow you "
               'or chose to be found nearby, and about an opening you both have a part in.')
PERSONA = "AI personas don't read messages. You can take up their openings, or acknowledge them on their trail."
YOU_BLOCKED = 'You blocked them. Unblock them to write.'


def ensure_tables():
    for statement in DDL:
        session.execute(statement)


def now():
    """Cassandra keeps milliseconds; times must read back as they were written."""
    t = datetime.utcnow()
    return t.replace(microsecond=t.microsecond // 1000 * 1000)


def sent_at(message_id):
    at = datetime.utcfromtimestamp(round(unix_time_from_uuid1(message_id), 3))
    return at.replace(microsecond=round(at.microsecond / 1000) % 1000 * 1000)


def conversation(one, other):
    low, high = sorted((str(as_uuid(one)), str(as_uuid(other))))
    return uuid.uuid5(PAIRS, f'{low}:{high}')


def message_key(value):
    key = as_uuid(value)
    return key if key and key.version == 1 else None     # only a timeuuid fits that column


def person(user_id):
    uid = as_uuid(user_id)
    return session.execute('SELECT user_id, name, surname, is_agent, place FROM users WHERE user_id = %s',
                           [uid]).one() if uid else None


def thread(user_id, other_id):
    return session.execute('SELECT * FROM message_inbox WHERE user_id = %s AND other_id = %s',
                           [as_uuid(user_id), as_uuid(other_id)]).one()


def is_unread(row):
    return bool(row and row.last_at and row.last_from != row.user_id
                and (not row.read_at or row.read_at < row.last_at))


# -- Openings --------------------------------------------------------------------
def contact(opening):
    """The human to write to about an opening: groups have no inbox."""
    who = getattr(opening, 'acting_user_id', None) or opening.provider_id
    found = person(who) if who else None
    return found.user_id if found else None


def runs(opening, user_id):
    me = as_uuid(user_id)
    if me in (opening.provider_id, getattr(opening, 'acting_user_id', None)):
        return True
    return bool(opening.provider_id) and can_manage_entity(opening.provider_id, me, include_platform_admin=False)


def respondents(opening):
    """The humans waiting on or confirmed for it, its earlier versions included."""
    out = set()
    for version in [opening, *Service.get_history(opening.service_id)]:
        for a in Service.acceptances(version.service_id):
            if a['status'] in ('pending', 'confirmed'):
                out.add(as_uuid(a['acting_user_id'] or a['accepter_id']))
    return out


def linked(opening, sender, other):
    """Whether these two have a part in this opening, so may write about it."""
    a, b = as_uuid(sender), as_uuid(other)
    poster = contact(opening)
    if b == poster and Sight(a).sphere(opening.sphere_id):
        return True
    took_part = respondents(opening)
    if b in took_part and (a == poster or runs(opening, a)):
        return True
    return a in took_part and (b == poster or runs(opening, b))


def about(opening_id, sender, other):
    """The opening a message is about, if they may name it."""
    key = as_uuid(opening_id)
    opening = Service.get_by_id(key) if key else None
    return opening if opening and linked(opening, sender, other) else None


# -- Who may write -----------------------------------------------------------------
def why_not(sender, other, opening=None):
    """Why `sender` can't write to `other`, or None. `opening`: what about() found."""
    a, b = as_uuid(sender), as_uuid(other)
    me, them = person(a), person(b)
    if not me or not them:
        return 'That member is no longer here.'
    if a == b:
        return "That's you."
    if me.is_agent or them.is_agent:
        return PERSONA
    if safety.blocked(a, b):
        return YOU_BLOCKED
    if safety.blocked(b, a):
        return NOT_ALLOWED
    if opening or thread(a, b) or is_platform_admin(a):
        return None
    if Sphere.member_sphere_ids(a) & Sphere.member_sphere_ids(b):
        return None
    if (places.load(them.place) or {}).get('findable') is True or Follow.is_following(b, a):
        return None
    return NOT_ALLOWED


# -- Reading and writing ---------------------------------------------------------
def write(sender, other, body, opening=None):
    """(message id, when, whether to notify: not again while they haven't read)."""
    a, b = as_uuid(sender), as_uuid(other)
    notify = not is_unread(thread(b, a))
    at = now()
    message_id = uuid_from_time(at)         # a random node: uuid1() would carry the machine's address
    session.execute('INSERT INTO direct_messages (conversation_id, message_id, sender_id, body, opening_id) '
                    'VALUES (%s, %s, %s, %s, %s)',
                    [conversation(a, b), message_id, a, body, opening.service_id if opening else None])
    preview = ' '.join(body.split())[:PREVIEW_MAX]
    session.execute('UPDATE message_inbox SET last_at = %s, last_from = %s, last_body = %s, read_at = %s '
                    'WHERE user_id = %s AND other_id = %s', [at, a, preview, at, a, b])
    session.execute('UPDATE message_inbox SET last_at = %s, last_from = %s, last_body = %s '
                    'WHERE user_id = %s AND other_id = %s', [at, a, preview, b, a])
    return message_id, at, notify


def history(user_id, other_id, before=None):
    """(a page, oldest first; whether there are older ones)."""
    cql = 'SELECT message_id, sender_id, body, opening_id FROM direct_messages WHERE conversation_id = %s'
    values = [conversation(user_id, other_id)]
    if before:
        cql += ' AND message_id < %s'
        values.append(before)
    rows = list(session.execute(f'{cql} LIMIT {PAGE + 1}', values))
    return rows[:PAGE][::-1], len(rows) > PAGE


def mark_read(user_id, other_id, up_to=None):
    """Whether nothing is left unread."""
    row = thread(user_id, other_id)
    if not row or not row.last_at:
        return True
    seen = min(sent_at(up_to), row.last_at) if up_to else row.last_at
    if not row.read_at or seen > row.read_at:
        session.execute('UPDATE message_inbox SET read_at = %s WHERE user_id = %s AND other_id = %s',
                        [seen, row.user_id, row.other_id])
    return seen >= row.last_at


def conversations(user_id):
    rows = [r for r in session.execute('SELECT * FROM message_inbox WHERE user_id = %s', [as_uuid(user_id)]) if r.last_at]
    return sorted(rows, key=lambda r: r.last_at, reverse=True)


def remove(conversation_id, message_id, one, other):
    """An administrator's, after a report."""
    session.execute('DELETE FROM direct_messages WHERE conversation_id = %s AND message_id = %s',
                    [conversation_id, message_id])
    at = sent_at(message_id)
    for mine, theirs in ((one, other), (other, one)):
        row = thread(mine, theirs)
        if row and row.last_at == at:
            session.execute('UPDATE message_inbox SET last_body = %s WHERE user_id = %s AND other_id = %s',
                            [REMOVED, row.user_id, row.other_id])


# -- Accounts ----------------------------------------------------------------------
def export(user_id):
    out = []
    for row in conversations(user_id):
        rows = session.execute('SELECT message_id, sender_id, body FROM direct_messages WHERE conversation_id = %s',
                               [conversation(row.user_id, row.other_id)])
        out.append({'with': str(row.other_id),
                    'messages': [{'from_you': m.sender_id == row.user_id, 'text': m.body, 'at': sent_at(m.message_id)}
                                 for m in reversed(list(rows))]})
    return out


def forget(user_id):
    """Their inbox goes; what they sent stays in the other person's."""
    session.execute('DELETE FROM message_inbox WHERE user_id = %s', [as_uuid(user_id)])
