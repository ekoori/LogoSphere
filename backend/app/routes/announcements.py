"""A group's announcements (app/utils/announcements.py):

  GET    /api/announcements/<group>          read them
  POST   /api/announcements/<group>          {text}: its managers
  DELETE /api/announcements/<group>/<id>     who wrote it, or a manager
"""
from flask import current_app as app, jsonify, request

from app.middleware.session_middleware import validate_session
from app.models.notification import Notification
from app.utils import announcements, groups, mailer
from app.utils.access import Sight, as_uuid
from app.utils.names import resolve_user_names
from app.utils.permissions import can_manage_entity

NOT_FOUND = {'message': 'Not found'}


@validate_session
def list_announcements(group_id, user_id=None):
    group, sight = groups.find(group_id), Sight(user_id)
    if not group or not announcements.readable(sight, group):
        return jsonify(NOT_FOUND), 404
    rows = announcements.of(group.id)
    names = resolve_user_names([r.author_id for r in rows if r.author_id])
    manages = can_manage_entity(group.id, sight.id)
    return jsonify({'can_announce': manages, 'announcements': [{
        'id': str(r.announcement_id), 'text': r.body or '',
        'at': announcements.said_at(r.announcement_id).isoformat(),
        'author': {'id': str(r.author_id), 'name': names.get(r.author_id) or 'A former member'} if r.author_id else None,
        'can_remove': manages or r.author_id == sight.id,
    } for r in rows]}), 200


@validate_session
def make_announcement(group_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    group, sight = groups.find(group_id), Sight(user_id)
    if not group or not announcements.readable(sight, group):
        return jsonify(NOT_FOUND), 404
    if not can_manage_entity(group.id, sight.id):
        return jsonify({'message': f"Only the {group.kind}'s managers can announce."}), 403
    data = request.get_json(silent=True)
    given = data.get('text') if isinstance(data, dict) else None
    text = given.strip() if isinstance(given, str) else ''
    if not text:
        return jsonify({'message': 'Write a few words first.'}), 400
    if len(text) > announcements.TEXT_MAX:
        return jsonify({'message': f'Keep it under {announcements.TEXT_MAX} characters.'}), 400
    if not mailer.take(f'announce:{group.id}', announcements.PER_DAY):
        return jsonify({'message': 'That is enough announcements for one day.'}), 429
    key = announcements.make(group, sight.id, text)
    me = as_uuid(user_id)
    name = resolve_user_names([me]).get(me) or 'A member'
    for member in group.members - {me}:
        # Not its words: notifications reach lock screens and mailboxes.
        Notification.create(user_id=member, actor_id=me, actor_name=name, type_='announcement',
                            message=f'A new announcement in {group.name}', link=groups.link(group))
    return jsonify({'id': str(key), 'message': 'Announced to its members.'}), 201


@validate_session
def remove_announcement(group_id, announcement_id, user_id=None):
    group, sight = groups.find(group_id), Sight(user_id)
    found = announcements.get(group.id, announcement_id) if group else None
    if not found:
        return jsonify(NOT_FOUND), 404
    if found.author_id != as_uuid(user_id) and not can_manage_entity(group.id, sight.id):
        if not announcements.readable(sight, group):
            return jsonify(NOT_FOUND), 404
        return jsonify({'message': 'Only who wrote it, or a manager, can remove it.'}), 403
    announcements.remove(group.id, found.announcement_id)
    return jsonify({'message': 'Removed.'}), 200


def register(app_):
    announcements.ensure_tables()
    app_.add_url_rule('/api/announcements/<group_id>', view_func=list_announcements, methods=['GET'])
    app_.add_url_rule('/api/announcements/<group_id>', view_func=make_announcement, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/announcements/<group_id>/<announcement_id>', view_func=remove_announcement, methods=['DELETE'])
