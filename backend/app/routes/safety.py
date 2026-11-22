"""Blocking and reporting (app/utils/safety.py):

  GET  /api/blocks                     whom you blocked
  POST /api/blocks/<person>            {blocked}
  POST /api/reports                    {kind: person|message|acknowledgement|opening|event|announcement, id, note,
                                        person_id (a message), trail_id (an acknowledgement),
                                        group_id (an announcement)}
  GET  /api/admin/reports?status=      the administrators' queue
  POST /api/admin/reports/<id>         {status: handled|dismissed, note, remove}
"""
from flask import current_app as app, jsonify, request

from app.db import session
from app.middleware.session_middleware import validate_session
from app.models.acknowledgement import Acknowledgement
from app.models.notification import Notification
from app.models.openings import Service
from app.routes.admin import admin_only
from app.utils import announcements, events, groups, mailer, messaging, safety
from app.utils.access import Sight, as_uuid
from app.utils.names import resolve_user_names
from app.utils.trails import Trail

REPORTS_A_DAY = 20
REMOVABLE = ('message', 'acknowledgement', 'announcement')


def _options():
    return app.make_default_options_response(), 200


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _said(value):
    return value.strip() if isinstance(value, str) else ''


@validate_session
def list_blocks(user_id=None):
    found = safety.blocked_by(user_id)
    names = resolve_user_names([who for who, _ in found])
    out = [{'id': str(who), 'name': names.get(who) or 'A former member', 'since': since.isoformat() if since else None}
           for who, since in found]
    return jsonify(sorted(out, key=lambda b: b['name'].lower())), 200


@validate_session
def set_block(person_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    me, other = as_uuid(user_id), as_uuid(person_id)
    on = _body().get('blocked')
    if not isinstance(on, bool):
        return jsonify({'message': 'Say whether to block or unblock.'}), 400
    if not other:
        return jsonify({'message': 'Not found'}), 404
    if other == me:
        return jsonify({'message': "You can't block yourself."}), 400
    if not on:
        safety.unblock(me, other)       # someone who left can still be unblocked
        return jsonify({'blocked': False}), 200
    if not messaging.person(other):
        return jsonify({'message': 'Not found'}), 404
    safety.block(me, other)
    for kind, link in (('message', f'/messages?with={other}'), ('new_follower', f'/user?id={other}')):
        Notification.withdraw(me, kind, link)
    return jsonify({'blocked': True}), 200


def _reported(me, data):
    """(whom, its id, where it is, what it said), read here and never taken from
    the client; or None when it isn't there or isn't theirs to see."""
    kind, item = data.get('kind'), data.get('id')
    if kind == 'person':
        them = messaging.person(item)
        return (them.user_id, them.user_id, None, '') if them else None
    if kind == 'opening':
        key = as_uuid(item)
        opening = Service.get_by_id(key) if key else None
        if not opening or not Sight(me).sphere(opening.sphere_id):
            return None
        words = f"{opening.title or ''}: {opening.description or ''}"
        return messaging.contact(opening), opening.service_id, None, words
    if kind == 'event':
        event = events.get(item)
        if not event or not event.visible(Sight(me)):
            return None
        return event.creator_id, event.event_id, None, f"{event.title or ''}: {event.description or ''}"
    if kind == 'announcement':
        group = groups.find(data.get('group_id'))
        if not group or not announcements.readable(Sight(me), group):
            return None
        said = announcements.get(group.id, item)
        return (said.author_id, said.announcement_id, group.id, said.body) if said else None
    if kind == 'message':
        other, key = as_uuid(data.get('person_id')), messaging.message_key(item)
        if not other or not key:
            return None
        place = messaging.conversation(me, other)
        row = session.execute('SELECT sender_id, body FROM direct_messages WHERE conversation_id = %s AND message_id = %s',
                              [place, key]).one()
        return (other, key, place, row.body) if row and row.sender_id == other else None
    if kind == 'acknowledgement':
        trail = Trail.find(data.get('trail_id'))
        key = as_uuid(item)
        if not key or not trail or not trail.readable(Sight(me)):
            return None
        ack = Acknowledgement.find(trail.id, key)
        return (ack.author_id, ack.ack_id, trail.id, ack.body) if ack else None
    return None


@validate_session
def make_report(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    me, data = as_uuid(user_id), _body()
    if data.get('kind') not in ('person', 'message', 'acknowledgement', 'opening', 'event', 'announcement'):
        return jsonify({'message': 'Say what you are reporting.'}), 400
    note = _said(data.get('note'))
    if len(note) > safety.NOTE_MAX:
        return jsonify({'message': f'Keep it under {safety.NOTE_MAX} characters.'}), 400
    if data['kind'] == 'person' and not note:
        return jsonify({'message': 'Say in a few words what happened.'}), 400
    found = _reported(me, data)
    if not found:
        return jsonify({'message': 'Not found'}), 404
    subject, item, where, words = found
    if subject == me:
        return jsonify({'message': "That's your own."}), 400
    if not mailer.take(f'reports:{me}', REPORTS_A_DAY):
        return jsonify({'message': 'That is a lot of reports for one day. Try again tomorrow.'}), 429
    safety.file_report(me, subject, data['kind'], item, where, words, note)
    for admin in safety.administrators():
        if admin != me:
            Notification.create(user_id=admin, actor_id=None, actor_name='LogoSphere', type_='report',
                                message='A report is waiting for an administrator', link='/admin?tab=reports')
    return jsonify({'message': "Thank you. The platform's administrators will look at it. Nobody else is told."}), 201


@admin_only
def list_reports(user_id=None):
    wanted = request.args.get('status', safety.OPEN)
    rows = safety.all_reports()
    waiting = sum(r.status == safety.OPEN for r in rows)
    if wanted != 'all':
        rows = [r for r in rows if r.status == wanted]
    rows = rows[:200]
    names = resolve_user_names([i for r in rows for i in (r.reporter_id, r.subject_id, r.handled_by) if i])
    who = lambda uid: {'id': str(uid), 'name': names.get(uid) or 'A former member'} if uid else None
    return jsonify({'open': waiting, 'reports': [{
        'id': str(r.report_id), 'kind': r.kind, 'item_id': r.item_id,
        'context_id': str(r.context_id) if r.context_id else None,
        'reporter': who(r.reporter_id), 'subject': who(r.subject_id),
        'excerpt': r.excerpt or '', 'note': r.note or '', 'status': r.status,
        'made_at': r.made_at.isoformat() if r.made_at else None,
        'handled_by': who(r.handled_by), 'handled_at': r.handled_at.isoformat() if r.handled_at else None,
        'outcome': r.outcome or '', 'removable': r.kind in REMOVABLE and r.status == safety.OPEN,
    } for r in rows]}), 200


@admin_only
def settle_report(report_id, user_id=None):
    report = safety.report(report_id)
    if not report:
        return jsonify({'message': 'Not found'}), 404
    data = _body()
    if data.get('status') not in (safety.HANDLED, safety.DISMISSED):
        return jsonify({'message': 'Handled or dismissed?'}), 400
    if data.get('remove') is True:
        if report.kind not in REMOVABLE or data['status'] != safety.HANDLED:
            return jsonify({'message': 'Only a message, acknowledgement or announcement can be removed, when handling it.'}), 400
        if report.kind == 'message':
            key = messaging.message_key(report.item_id)
            messaging.remove(report.context_id, key, report.reporter_id, report.subject_id)
        elif report.kind == 'announcement':
            announcements.remove(report.context_id, report.item_id)
        else:
            ack = Acknowledgement.find(report.context_id, report.item_id)
            if ack:
                ack.remove()
    safety.settle(report.report_id, user_id, data['status'], _said(data.get('note')))
    return jsonify({'message': 'Saved.', 'status': data['status']}), 200


def register(app_):
    safety.ensure_tables()
    app_.add_url_rule('/api/blocks', view_func=list_blocks, methods=['GET'])
    app_.add_url_rule('/api/blocks/<person_id>', view_func=set_block, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/reports', view_func=make_report, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/admin/reports', view_func=list_reports, methods=['GET', 'OPTIONS'])
    app_.add_url_rule('/api/admin/reports/<report_id>', view_func=settle_report, methods=['POST', 'OPTIONS'])
