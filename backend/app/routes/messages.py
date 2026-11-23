"""Private messages (app/utils/messaging.py has who may write to whom):

  GET  /api/messages                                 your conversations
  GET  /api/messages/<person>?before=&about=kind:id  one of them, and whether you may write
                                                     (`opening=<id>` still means about=opening:<id>)
  POST /api/messages/<person>                        {text, about?: {kind, id}, opening_id?}

A conversation can be about an opening, a sphere, alliance or project, or an event.
  POST /api/messages/<person>/read                   {up_to?}
  POST /api/openings/<id>/message_respondents        {text}: privately, to each who responded
"""
from flask import current_app as app, jsonify, request

from app.middleware.session_middleware import validate_session
from app.models.notification import Notification
from app.models.openings import Service
from app.utils import mailer, messaging, safety
from app.utils.access import as_uuid
from app.utils.names import resolve_user_names

GONE = 'A former member'
SLOW_DOWN = 'That is a lot of messages. Please wait a while before sending more.'


def _options():
    return app.make_default_options_response(), 200


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _text(data):
    """(the words, None) or (None, what's wrong with them)."""
    given = data.get('text')
    text = given.strip() if isinstance(given, str) else ''
    if not text:
        return None, 'Write a few words first.'
    if len(text) > messaging.TEXT_MAX:
        return None, f'Keep it under {messaging.TEXT_MAX} characters.'
    return text, None


def _subject(value, opening, me, other):
    """What it is about: `about` as {kind, id} or "kind:id", or the older opening id."""
    if isinstance(value, dict):
        kind, ident = value.get('kind'), value.get('id')
    elif isinstance(value, str) and ':' in value:
        kind, _, ident = value.partition(':')
    elif opening:
        kind, ident = 'opening', opening
    else:
        return None
    return messaging.subject(kind, ident, me, other) if isinstance(kind, str) else None


def _about(found):
    return {'kind': found.kind, 'id': str(found.id), 'title': found.title, 'link': found.link} if found else None


def _opening_only(about):
    """The older shape, which apps from before 2026-11-23 read."""
    return {'id': about['id'], 'title': about['title']} if about and about['kind'] == 'opening' else None


def _link(person_id):
    return f'/messages?with={person_id}'


def _tell(sender, recipient):
    name = resolve_user_names([sender]).get(sender) or 'A member'
    # The words stay out of notifications: those reach lock screens and mailboxes.
    Notification.create(user_id=recipient, actor_id=sender, actor_name=name, type_='message',
                        message=f'{name} sent you a message', link=_link(sender))


@validate_session
def list_conversations(user_id=None):
    me = as_uuid(user_id)
    rows = messaging.conversations(me)
    names = resolve_user_names([r.other_id for r in rows])
    out = [{'person': {'id': str(r.other_id), 'name': names.get(r.other_id) or GONE},
            'last': {'text': r.last_body or '', 'at': r.last_at.isoformat(), 'mine': r.last_from == me},
            'unread': messaging.is_unread(r)} for r in rows]
    return jsonify({'conversations': out, 'unread_count': sum(c['unread'] for c in out)}), 200


@validate_session
def get_conversation(person_id, user_id=None):
    me, other = as_uuid(user_id), as_uuid(person_id)
    if not other or other == me:
        return jsonify({'message': 'Not found'}), 404
    them = messaging.person(other)
    if not them and not messaging.thread(me, other):
        return jsonify({'message': 'Not found'}), 404
    before = request.args.get('before')
    if before and not messaging.message_key(before):
        return jsonify({'message': 'That page is not there.'}), 400
    rows, more = messaging.history(me, other, messaging.message_key(before))
    found = _subject(request.args.get('about'), request.args.get('opening'), me, other) if them else None
    named = {}
    for key in {s for r in rows if (s := messaging.subject_of(r))}:
        named[key] = messaging.described(*key)
    why = messaging.why_not(me, other, found)
    name = f"{them.name or ''} {them.surname or ''}".strip() or 'A member' if them else GONE
    return jsonify({
        'person': {'id': str(other), 'name': name, 'is_agent': bool(them and them.is_agent)},
        'messages': [{'id': str(r.message_id), 'text': r.body, 'at': messaging.sent_at(r.message_id).isoformat(),
                      'mine': r.sender_id == me, 'about': named.get(messaging.subject_of(r)),
                      'opening': _opening_only(named.get(messaging.subject_of(r)))} for r in rows],
        'more': more,
        'about': _about(found),
        'can_send': why is None,
        'why_not': why,
        'blocked': safety.blocked(me, other),
    }), 200


@validate_session
def send_message(person_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    me, other = as_uuid(user_id), as_uuid(person_id)
    if not other or not messaging.person(other):
        return jsonify({'message': 'Not found'}), 404
    data = _body()
    text, wrong = _text(data)
    if wrong:
        return jsonify({'message': wrong}), 400
    found = _subject(data.get('about'), data.get('opening_id'), me, other)
    why = messaging.why_not(me, other, found)
    if why:
        return jsonify({'message': why}), 403
    if not messaging.thread(me, other) and not mailer.take(f'talks:{me}', messaging.NEW_PER_DAY):
        return jsonify({'message': 'You started many conversations today. More can start tomorrow.'}), 429
    if not mailer.take(f'messages:{me}', messaging.PER_HOUR, mailer.HOUR):
        return jsonify({'message': SLOW_DOWN}), 429
    message_id, at, notify = messaging.write(me, other, text, found)
    if notify:
        _tell(me, other)
    about = _about(found)
    return jsonify({'message': 'Sent', 'sent': {
        'id': str(message_id), 'text': text, 'at': at.isoformat(), 'mine': True,
        'about': about, 'opening': _opening_only(about)}}), 201


@validate_session
def read_conversation(person_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    me, other = as_uuid(user_id), as_uuid(person_id)
    if not other:
        return jsonify({'message': 'Not found'}), 404
    given = _body().get('up_to')
    up_to = messaging.message_key(given)
    if given and not up_to:
        return jsonify({'message': "That isn't one of these messages."}), 400
    all_read = messaging.mark_read(me, other, up_to)
    if all_read:
        Notification.withdraw(me, 'message', _link(other))
    return jsonify({'unread': not all_read}), 200


@validate_session
def message_respondents(service_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    me, key = as_uuid(user_id), as_uuid(service_id)
    opening = Service.get_by_id(key) if key else None
    if not opening:
        return jsonify({'message': 'Not found'}), 404
    if not messaging.runs(opening, me):
        return jsonify({'message': 'Only whoever runs this opening can write to everyone who responded.'}), 403
    text, wrong = _text(_body())
    if wrong:
        return jsonify({'message': wrong}), 400
    waiting = messaging.respondents(opening) - {me}
    about = messaging.opening_subject(opening)
    # As respondents they may be written to; a block or a persona still says no.
    to = sorted((p for p in waiting if messaging.why_not(me, p, about) is None), key=str)
    if not to:
        return jsonify({'message': 'There is nobody here you can write to.'}), 400
    if not mailer.take(f'messages:{me}', messaging.PER_HOUR, mailer.HOUR):
        return jsonify({'message': SLOW_DOWN}), 429
    for person_id in to:
        if messaging.write(me, person_id, text, about)[2]:
            _tell(me, person_id)
    return jsonify({'message': 'Sent privately to each: their answers come to you alone.',
                    'sent': len(to), 'skipped': len(waiting) - len(to)}), 200


def register(app_):
    messaging.ensure_tables()
    app_.add_url_rule('/api/messages', view_func=list_conversations, methods=['GET'])
    app_.add_url_rule('/api/messages/<person_id>', view_func=get_conversation, methods=['GET'])
    app_.add_url_rule('/api/messages/<person_id>', view_func=send_message, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/messages/<person_id>/read', view_func=read_conversation, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/openings/<service_id>/message_respondents', view_func=message_respondents,
                      methods=['POST', 'OPTIONS'])
