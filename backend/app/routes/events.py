"""Events (app/utils/events.py):

  GET   /api/events?group=             what's on, soonest first
  POST  /api/events                    put one on
  GET   /api/events/<id>               one, with its next dates and who's coming
  PATCH /api/events/<id>               change it
  POST  /api/events/<id>/cancel        {day?, cancelled?}: all of it, or one date
  POST  /api/events/<id>/reply         {day, answer: going|maybe|no|null}
  GET   /api/events/<id>/image         its picture, for who may see it
  POST  /api/events/<id>/image         set it

Where it is, is /api/places/events/<id>.
"""
from datetime import date, datetime, timedelta

from flask import current_app as app, jsonify, request

from app.middleware.session_middleware import validate_session
from app.models.notification import Notification
from app.utils import ai_pictures, demo, events, groups, image_store, mailer, places, recurrence
from app.utils.access import Sight, as_uuid
from app.utils.names import resolve_user_names
from app.utils.permissions import can_manage_entity
from app.utils.pictures import picture_response
from app.utils.validation import is_supported_image

NEW_A_DAY = 20
TOLD_A_DAY = 3              # a member's events a group hears of in a day; more are only listed
SHOWN_TIMES, MOST_SHOWN = 6, 30
EARLIEST_YEAR = 2000        # a series may have begun long ago, not in the year 1
TITLE_MAX, DESCRIPTION_MAX = 120, 4000
LENGTHS = (15, 7 * 24 * 60)
AHEAD_DAYS = 3 * 366
NOT_FOUND = {'message': 'Event not found'}


def _options():
    return app.make_default_options_response(), 200


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _said(value):
    return value.strip() if isinstance(value, str) else ''


def _fields(data, existing=None):
    """(the fields as stored, None) or (None, what's wrong)."""
    was = {name: getattr(existing, name) for name in events.EDITABLE} if existing else {}
    given = {
        'title': ' '.join(_said(data['title']).split()) if 'title' in data else was.get('title'),
        'description': _said(data['description']) if 'description' in data else was.get('description') or '',
        'starts_local': _said(data['starts']) if 'starts' in data else was.get('starts_local'),
        'tz': _said(data['tz']) if 'tz' in data else was.get('tz'),
        'length_min': data['length_min'] if 'length_min' in data else was.get('length_min', 60),
        'repeats': data['repeats'] if 'repeats' in data else was.get('repeats', recurrence.NEVER),
        'until_day': (data['until'] or None) if 'until' in data else was.get('until_day'),
    }
    if not given['title']:
        return None, 'Give it a name.'
    if len(given['title']) > TITLE_MAX:
        return None, f'Keep the name under {TITLE_MAX} characters.'
    if len(given['description']) > DESCRIPTION_MAX:
        return None, f'Keep the description under {DESCRIPTION_MAX} characters.'
    try:
        first = datetime.strptime(given['starts_local'] or '', events.LOCAL)
    except (TypeError, ValueError):
        return None, 'Say which day and time it starts.'
    if first.year < EARLIEST_YEAR:
        return None, 'That time has passed.'
    given['starts_local'] = first.strftime(events.LOCAL)
    if not recurrence.zone(given['tz']):
        return None, "That time zone isn't one we know."
    minutes = given['length_min']
    if isinstance(minutes, bool) or not isinstance(minutes, int) or not LENGTHS[0] <= minutes <= LENGTHS[1]:
        return None, 'It can last from 15 minutes to 7 days.'
    if given['repeats'] not in recurrence.REPEATS:
        return None, "Choose how it repeats, or that it doesn't."
    until = None
    if given['repeats'] == recurrence.NEVER:
        given['until_day'] = None
    elif given['until_day']:
        try:
            until = date.fromisoformat(given['until_day'])
        except (TypeError, ValueError):
            return None, "That last date isn't a date."
        if until < first.date():
            return None, 'Its last date is before its first.'
        given['until_day'] = until.isoformat()
    when_changed = any(given[k] != was.get(k) for k in ('starts_local', 'tz', 'repeats', 'until_day'))
    if when_changed:
        now = datetime.utcnow()
        if first > now + timedelta(days=AHEAD_DAYS):
            return None, 'That is too far ahead.'
        if not recurrence.upcoming(first, given['tz'], given['repeats'], until, minutes, now):
            return None, 'That time has passed.'
    return given, None


def _time(t):
    return {'day': t.day, 'starts_at': t.starts.isoformat(), 'ends_at': t.ends.isoformat(), 'skipped': t.skipped}


def _attendance(t, answers, me):
    return {**_time(t),
            'going': sum(a == events.GOING for a in answers.values()),
            'maybe': sum(a == events.MAYBE for a in answers.values()),
            'my_answer': answers.get(me)}


def _dict(event, me, host, origin, sphere_places):
    return {
        'id': str(event.event_id),
        'title': event.title,
        'description': event.description or '',
        'host': groups.summary(host),
        'sphere_id': str(event.sphere_id) if event.sphere_id else None,
        'creator_id': str(event.creator_id) if event.creator_id else None,
        'starts': event.starts_local,
        'tz': event.tz,
        'length_min': event.length_min,
        'repeats': event.repeats,
        'until': event.until_day,
        'cancelled': bool(event.cancelled_at),
        'has_image': bool(event.has_image),
        'image_is_ai': ai_pictures.is_ai_key(event.image_object),
        'is_demo': demo.is_demo_sphere(event.sphere_id),
        'location': places.label_of(event.place),
        'distance': places.how_far(origin, event.place, sphere_places.get(event.sphere_id)) if origin else None,
        'can_manage': event.managed(me),
    }


@validate_session
def list_events(user_id=None):
    sight, now = Sight(user_id), datetime.utcnow()
    given = request.args.get('group')
    only = as_uuid(given)
    if given and not only:
        return jsonify({'message': "That isn't a group."}), 400
    origin = places.of_person(sight.id)
    sphere_places = places.sphere_places() if origin else {}
    found, hosts = [], {}
    for event in events.everything():
        if (only and only not in (event.host_id, event.sphere_id)) or not event.visible(sight):
            continue
        upcoming = event.upcoming(now)
        if upcoming:
            found.append((upcoming, event))
    found.sort(key=lambda pair: (pair[0].starts, str(pair[1].event_id)))
    out = []
    for upcoming, event in found[:200]:
        if event.host_id and event.host_id not in hosts:
            hosts[event.host_id] = event.host()
        answers = events.replies(event.event_id).get(upcoming.day, {})
        out.append({**_dict(event, sight.id, hosts.get(event.host_id), origin, sphere_places),
                    'upcoming': _attendance(upcoming, answers, sight.id)})
    return jsonify({'events': out}), 200


def _shown(event, sight):
    now = datetime.utcnow()
    origin = places.of_person(sight.id)
    answered = events.replies(event.event_id)
    today = (now - timedelta(days=1)).date().isoformat()        # a day's slack for zones
    dates = event.times(now, min(MOST_SHOWN, SHOWN_TIMES + sum(day >= today for day in event.skipped)))
    coming = [who for t in dates for who, answer in answered.get(t.day, {}).items() if answer != events.CANT]
    creator = [event.creator_id] if event.creator_id else []
    names = resolve_user_names(coming + creator)
    upcoming = event.upcoming(now)
    body = _dict(event, sight.id, event.host(), origin, places.sphere_places() if origin else {})
    body.update({
        'creator': {'id': str(event.creator_id), 'name': names.get(event.creator_id) or 'A former member'} if creator else None,
        'point': places.exact_spot(event.place),
        'over': upcoming is None,
        'times': [{
            **_attendance(t, answered.get(t.day, {}), sight.id),
            'people': [{'id': str(who), 'name': names[who], 'answer': answer}
                       for who, answer in sorted(answered.get(t.day, {}).items(), key=lambda p: (p[1], str(p[0])))
                       if answer != events.CANT and who in names],
        } for t in dates],
    })
    return body


@validate_session
def get_event(event_id, user_id=None):
    sight, event = Sight(user_id), events.get(event_id)
    if not event or not event.visible(sight):
        return jsonify(NOT_FOUND), 404
    return jsonify(_shown(event, sight)), 200


@validate_session
def create_event(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    me, data = as_uuid(user_id), _body()
    host = None
    if data.get('host_id'):
        host = groups.find(data['host_id'])
        if not host:
            return jsonify({'message': 'That group is not there.'}), 404
        if me not in host.members and not can_manage_entity(host.id, me):
            return jsonify({'message': f'Join the {host.kind} first to put on its events.'}), 403
        if host.closed:
            return jsonify({'message': 'A closed project takes no new events.'}), 400
    fields, wrong = _fields(data)
    if wrong:
        return jsonify({'message': wrong}), 400
    if not mailer.take(f'events:{me}', NEW_A_DAY):
        return jsonify({'message': 'That is a lot of events for one day. More can be added tomorrow.'}), 429
    event = events.create(fields, host, me)
    if host and mailer.take(f'event_new:{host.id}:{me}', TOLD_A_DAY):
        name = resolve_user_names([me]).get(me) or 'A member'
        for member in host.members - {me}:
            Notification.create(user_id=member, actor_id=me, actor_name=name, type_='event_new',
                                message=f'A new event in {host.name}: "{event.title}"', link=event.link)
    return jsonify(_shown(event, Sight(me))), 201


def tell_expecting(event, actor, message, day=None, link=None):
    me = as_uuid(actor)
    name = resolve_user_names([me]).get(me) or 'A member'
    for person in events.expecting(event, day) - {me}:
        if event.visible(Sight(person)):        # they may have left since they answered
            Notification.create(user_id=person, actor_id=me, actor_name=name, type_='event_changed',
                                message=message, link=link or event.link)


def group_deleted(group_id, actor):
    """Called while the group is still there, so those coming can still be told."""
    for event in events.of_group(group_id):
        if event.upcoming(datetime.utcnow()):
            tell_expecting(event, actor, f'Cancelled: "{event.title}"', link='/events')
        events.delete(event)


def _mine_to_change(event_id, me):
    """(event, None) or (None, the refusal)."""
    event = events.get(event_id)
    if not event or not event.visible(Sight(me)):
        return None, (jsonify(NOT_FOUND), 404)
    if not event.managed(me):
        return None, (jsonify({'message': "Only whoever put it on, or the group's managers, can change it."}), 403)
    return event, None


@validate_session
def edit_event(event_id, user_id=None):
    event, refused = _mine_to_change(event_id, user_id)
    if refused:
        return refused
    if event.cancelled_at:
        return jsonify({'message': 'It was cancelled.'}), 409
    fields, wrong = _fields(_body(), existing=event)
    if wrong:
        return jsonify({'message': wrong}), 400
    changed = {name: value for name, value in fields.items() if value != getattr(event, name)}
    after = events.update(event, changed)
    if {'starts_local', 'tz', 'repeats', 'until_day', 'length_min'} & set(changed):
        tell_expecting(event, user_id, f'The time changed: "{after.title}"')
    return jsonify(_shown(after, Sight(user_id))), 200


@validate_session
def cancel_event(event_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    event, refused = _mine_to_change(event_id, user_id)
    if refused:
        return refused
    data = _body()
    day, cancelled = data.get('day'), data.get('cancelled', True)
    if not isinstance(cancelled, bool):
        return jsonify({'message': 'Cancelled, or not?'}), 400
    if day is not None:
        if event.cancelled_at:
            return jsonify({'message': 'It was cancelled.'}), 409
        found = event.falls_on(day)
        if not found or event.repeats == recurrence.NEVER:
            return jsonify({'message': "It doesn't repeat on that date."}), 400
        day = found.isoformat()
        if cancelled and day not in event.skipped:
            events.cancel(event, day)
            tell_expecting(event, user_id, f'Not on {found.day} {found:%b}: "{event.title}"', day)
        elif not cancelled and day in event.skipped:
            events.put_back(event, day)
            tell_expecting(event, user_id, f'On again on {found.day} {found:%b}: "{event.title}"', day)
    elif not cancelled:
        return jsonify({'message': 'A cancelled event stays cancelled. Put on a new one.'}), 400
    elif not event.cancelled_at:
        events.cancel(event)
        tell_expecting(event, user_id, f'Cancelled: "{event.title}"')
    return jsonify(_shown(events.get(event.event_id), Sight(user_id))), 200


@validate_session
def reply_event(event_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    sight, event = Sight(user_id), events.get(event_id)
    if not event or not event.visible(sight):
        return jsonify(NOT_FOUND), 404
    data = _body()
    answer = data.get('answer')
    if 'answer' not in data or answer not in (*events.ANSWERS, None):
        return jsonify({'message': 'Going, maybe, or no?'}), 400
    found = event.falls_on(data.get('day'))
    if not found:
        return jsonify({'message': "It isn't on that date."}), 400
    day = found.isoformat()
    if answer:
        ends = recurrence.to_utc(datetime.combine(found, event.first.time()), event.tz) + timedelta(minutes=event.length_min)
        if event.cancelled_at or day in event.skipped or ends <= datetime.utcnow():
            return jsonify({'message': "That one isn't on."}), 409
    events.reply(event, day, sight.id, answer)
    return jsonify(_shown(event, sight)), 200


@validate_session
def get_event_image(event_id, user_id=None):
    event = events.get(event_id)
    if not event or not event.visible(Sight(user_id)):
        return '', 404
    return picture_response(events.image(event), private=True)


@validate_session
def set_event_image(event_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    event, refused = _mine_to_change(event_id, user_id)
    if refused:
        return refused
    given = request.files.get('image')
    data = given.read() if given else None
    if not data:
        return jsonify({'message': 'image file is required'}), 400
    if not is_supported_image(data):
        return jsonify({'message': 'Unsupported image format (use JPEG, PNG, GIF or WebP)'}), 400
    try:
        events.set_image(event, data)
    except image_store.UnreadableImage:
        return jsonify({'message': "That picture can't be read. Try another."}), 400
    return jsonify({'message': 'Image updated'}), 200


def register(app_):
    events.ensure_tables()
    app_.add_url_rule('/api/events', view_func=list_events, methods=['GET'])
    app_.add_url_rule('/api/events', view_func=create_event, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/events/<event_id>', view_func=get_event, methods=['GET'])
    app_.add_url_rule('/api/events/<event_id>', view_func=edit_event, methods=['PATCH'])
    app_.add_url_rule('/api/events/<event_id>/cancel', view_func=cancel_event, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/events/<event_id>/reply', view_func=reply_event, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/events/<event_id>/image', view_func=get_event_image, methods=['GET'])
    app_.add_url_rule('/api/events/<event_id>/image', view_func=set_event_image, methods=['POST', 'OPTIONS'])
