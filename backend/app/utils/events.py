"""Events: what's on, where, and who's coming.

An event is a group's (any of its members may put one on) or, with no group,
for everyone signed in. It is seen by whoever may look inside its sphere, like
an opening. Attendance is for one date, since events repeat.
"""
import uuid
from datetime import date, datetime

from app.db import session
from app.utils import ai_pictures, groups, image_store, recurrence
from app.utils.access import as_uuid
from app.utils.permissions import can_manage_entity, is_platform_admin

DDL = (
    'CREATE TABLE IF NOT EXISTS events ('
    'event_id uuid PRIMARY KEY, title text, description text, host_id uuid, host_kind text, sphere_id uuid, '
    'creator_id uuid, starts_local text, tz text, length_min int, repeats text, until_day text, skipped set<text>, '
    'place text, image blob, image_object text, has_image boolean, cancelled_at timestamp, made_at timestamp)',
    'CREATE TABLE IF NOT EXISTS event_replies ('
    'event_id uuid, on_day text, user_id uuid, answer text, answered_at timestamp, '
    'PRIMARY KEY ((event_id), on_day, user_id))',
)
COLS = ('event_id, title, description, host_id, host_kind, sphere_id, creator_id, starts_local, tz, length_min, '
        'repeats, until_day, skipped, place, image_object, has_image, cancelled_at, made_at')
LOCAL = '%Y-%m-%dT%H:%M'
GOING, MAYBE, CANT = 'going', 'maybe', 'no'
ANSWERS = (GOING, MAYBE, CANT)
EDITABLE = ('title', 'description', 'starts_local', 'tz', 'length_min', 'repeats', 'until_day')


def ensure_tables():
    for statement in DDL:
        session.execute(statement)


class Event:
    def __init__(self, row):
        for name in (c.strip() for c in COLS.split(',')):
            setattr(self, name, getattr(row, name, None))
        self.skipped = set(self.skipped or ())
        self.repeats = self.repeats or recurrence.NEVER
        self.length_min = self.length_min or 60
        self.first = datetime.strptime(self.starts_local, LOCAL) if self.starts_local else datetime.min
        self.until = date.fromisoformat(self.until_day) if self.until_day else None

    @property
    def link(self):
        return f'/event?id={self.event_id}'

    # -- when --------------------------------------------------------------
    def upcoming(self, now):
        if self.cancelled_at:
            return None
        return recurrence.upcoming(self.first, self.tz, self.repeats, self.until, self.length_min, now, self.skipped)

    def times(self, now, count):
        """The next few, skipped ones marked; the first, for one that's over."""
        found = recurrence.times(self.first, self.tz, self.repeats, self.until, self.length_min, now, count, self.skipped)
        return found or recurrence.times(self.first, self.tz, self.repeats, self.until, self.length_min, None, 1, self.skipped)

    def falls_on(self, day):
        return recurrence.falls_on(self.first, self.repeats, self.until, day)

    # -- who ---------------------------------------------------------------
    def visible(self, sight):
        # Having made it is no pass: whoever left the sphere is outside it.
        return sight.sphere(self.sphere_id)

    def managed(self, user_id):
        me = as_uuid(user_id)
        if not me:
            return False
        if is_platform_admin(me):
            return True
        if not self.host_id:
            return me == self.creator_id
        if can_manage_entity(self.host_id, me):
            return True
        host = self.host() if me == self.creator_id else None
        return bool(host) and me in host.members        # whoever made it, while they're in the group

    def host(self):
        return groups.find(self.host_id) if self.host_id else None


def get(event_id):
    eid = as_uuid(event_id)
    row = session.execute(f'SELECT {COLS} FROM events WHERE event_id = %s', [eid]).one() if eid else None
    return Event(row) if row and row.starts_local else None


def everything():
    return [Event(row) for row in session.execute(f'SELECT {COLS} FROM events') if row.starts_local]


def create(fields, host, creator):
    eid = uuid.uuid4()
    session.execute(
        'INSERT INTO events (event_id, title, description, host_id, host_kind, sphere_id, creator_id, starts_local, tz, '
        'length_min, repeats, until_day, made_at) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        [eid, fields['title'], fields['description'], host.id if host else None, host.kind if host else None,
         host.sphere_id if host else None, as_uuid(creator), fields['starts_local'], fields['tz'], fields['length_min'],
         fields['repeats'], fields['until_day'], datetime.utcnow()])
    return get(eid)


def update(event, changed):
    names = [name for name in EDITABLE if name in changed]
    if names:
        session.execute(f"UPDATE events SET {', '.join(f'{n} = %s' for n in names)} WHERE event_id = %s",
                        [changed[n] for n in names] + [event.event_id])
    return get(event.event_id)


def cancel(event, day=None):
    if day:
        session.execute('UPDATE events SET skipped = skipped + %s WHERE event_id = %s', [{day}, event.event_id])
    else:
        session.execute('UPDATE events SET cancelled_at = %s WHERE event_id = %s', [datetime.utcnow(), event.event_id])


def put_back(event, day):
    session.execute('UPDATE events SET skipped = skipped - %s WHERE event_id = %s', [{day}, event.event_id])


def of_group(group_id):
    gid = as_uuid(group_id)
    return [e for e in everything() if gid in (e.host_id, e.sphere_id)]


def delete(event):
    for table in ('event_replies', 'events'):
        session.execute(f'DELETE FROM {table} WHERE event_id = %s', [event.event_id])


def set_image(event, data):
    key, blob = image_store.store(data, 'banner')
    ai_pictures.note_upload(data, key)
    session.execute('UPDATE events SET image = %s, image_object = %s, has_image = true WHERE event_id = %s',
                    [blob, key, event.event_id])


def image(event):
    row = session.execute('SELECT image, image_object FROM events WHERE event_id = %s', [event.event_id]).one()
    return image_store.fetch(row.image_object, row.image) if row else None


# -- Attendance --------------------------------------------------------------
def replies(event_id):
    """{day: {who: answer}}"""
    out = {}
    for row in session.execute('SELECT on_day, user_id, answer FROM event_replies WHERE event_id = %s', [event_id]):
        if row.answer:
            out.setdefault(row.on_day, {})[row.user_id] = row.answer
    return out


def reply(event, day, user_id, answer):
    key = [event.event_id, day, as_uuid(user_id)]
    if answer is None:
        session.execute('DELETE FROM event_replies WHERE event_id = %s AND on_day = %s AND user_id = %s', key)
    else:
        session.execute('INSERT INTO event_replies (event_id, on_day, user_id, answer, answered_at) '
                        'VALUES (%s, %s, %s, %s, %s)', key + [answer, datetime.utcnow()])


def expecting(event, day=None, now=None):
    """Whom a change matters to: going or maybe, on that date or any still to come."""
    today = (now or datetime.utcnow()).date().isoformat()
    out = set()
    for on, answers in replies(event.event_id).items():
        # A day's slack: the event's date can be behind UTC's.
        if (day and on != day) or (not day and on < today and event.repeats != recurrence.NEVER):
            continue
        out |= {who for who, answer in answers.items() if answer in (GOING, MAYBE)}
    return out


# -- Accounts -----------------------------------------------------------------
def export(user_id):
    me = as_uuid(user_id)
    made = [{'id': str(e.event_id), 'title': e.title, 'starts': e.starts_local, 'time_zone': e.tz}
            for e in everything() if e.creator_id == me]
    answered = [{'id': str(r.event_id), 'date': r.on_day, 'answer': r.answer}
                for r in session.execute('SELECT event_id, on_day, user_id, answer FROM event_replies') if r.user_id == me]
    return {'made': made, 'replies': answered}


def forget(user_id):
    """Their replies go. Their events with no group are cancelled, keeping only
    name and time (the place may be their home); a group's stay its own."""
    from app.models.notification import Notification        # models import utils
    me, now = as_uuid(user_id), datetime.utcnow()
    for row in session.execute('SELECT event_id, on_day, user_id FROM event_replies'):
        if row.user_id == me:
            session.execute('DELETE FROM event_replies WHERE event_id = %s AND on_day = %s AND user_id = %s',
                            [row.event_id, row.on_day, me])
    for event in everything():
        if event.creator_id != me or event.host_id:
            continue
        waiting = expecting(event) - {me} if event.upcoming(now) else ()
        session.execute("UPDATE events SET cancelled_at = %s, description = %s, place = null, image = null, "
                        "image_object = null, has_image = false WHERE event_id = %s",
                        [event.cancelled_at or now, '', event.event_id])
        for person in waiting:
            Notification.create(user_id=person, actor_id=None, actor_name='LogoSphere', type_='event_changed',
                                message=f'Cancelled: "{event.title}"', link=event.link)
