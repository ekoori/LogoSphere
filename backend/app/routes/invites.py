"""Invitation links (app/utils/invites.py):

  GET  /api/invites                 those you made
  POST /api/invites                 {group_id?}: a new link
  POST /api/invites/<id>/revoke     stop one
  POST /api/invites/look            {code}: who invites to what; signed out too
  POST /api/invites/accept          {code}

Signing up with one: POST /api/register takes `invite`, the code.
"""
import logging
from datetime import timedelta

from flask import current_app as app, jsonify, request

from app.middleware.session_middleware import validate_session
from app.models.notification import Notification
from app.utils import groups, invites
from app.utils.access import as_uuid
from app.utils.names import resolve_user_names

logger = logging.getLogger(__name__)
NO_LONGER = {'message': "This invitation doesn't work any more. Ask for a new one."}


def _options():
    return app.make_default_options_response(), 200


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def welcomed(invite_hash, user_id, arriving=False):
    """Joins with an invitation and tells who made it; None when it doesn't work."""
    done = invites.accept(invite_hash, user_id, arriving)
    if not done:
        return None
    maker, group, news = done
    if news:
        who = as_uuid(user_id)
        name = resolve_user_names([who]).get(who) or 'A member'
        where = group.name if group else 'LogoSphere'
        Notification.create(user_id=maker.user_id, actor_id=who, actor_name=name, type_='invite_accepted',
                            message=f'{name} joined {where} with your invitation', link=f'/user?id={who}')
    return maker, group


def arrived(invite_hash, user_id):
    """An account just made with an invitation. Best-effort: never spoils joining."""
    if not invite_hash:
        return None
    try:
        return welcomed(invite_hash, user_id, arriving=True)
    except Exception as e:  # noqa: BLE001 - the account is made whatever happens here
        logger.error('An invitation failed for new user %s: %s', user_id, e)
        return None


@validate_session
def list_invites(user_id=None):
    out = []
    for row in invites.made_by(user_id):
        group = groups.find(row.group_id) if row.group_id else None
        out.append({'id': row.invite_hash, 'group': groups.summary(group), 'made_at': row.made_at.isoformat(),
                    'expires_at': (row.made_at + timedelta(days=invites.DAYS)).isoformat(),
                    'joined': len(invites.uses(row.invite_hash)), 'works': bool(invites.live(row.invite_hash))})
    return jsonify(out), 200


@validate_session
def make_invite(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    given = _body().get('group_id')
    group = groups.find(given) if given else None
    if given and not group:
        return jsonify({'message': 'That group is not there.'}), 404
    if not invites.may_invite(user_id, group):
        return jsonify({'message': ("You can't invite to that. Where joining needs approval, its managers invite; "
                                    "and an alliance's or project's link also needs the right to invite to its sphere.")
                        if group else "AI personas don't invite."}), 403
    if len(invites.made_by(user_id)) >= invites.MOST_LIVE:
        return jsonify({'message': 'You have many invitations out. Revoke one first.'}), 429
    code, key, until = invites.make(user_id, group)
    return jsonify({'id': key, 'path': f'/invite#{code}', 'expires_at': until.isoformat(),
                    'most_uses': invites.MOST_USES, 'group': groups.summary(group)}), 201


@validate_session
def revoke_invite(invite_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    if not any(r.invite_hash == invite_id for r in invites.made_by(user_id)):
        return jsonify({'message': 'Not found'}), 404
    invites.revoke(invite_id)
    return jsonify({'message': 'That link no longer works.'}), 200


def look_invite():
    """For whoever holds the code: who invites, and to what."""
    if request.method == 'OPTIONS':
        return _options()
    found = invites.live(invites.hashed(_body().get('code')))
    if not found:
        return jsonify(NO_LONGER), 404
    _, maker, group = found
    return jsonify({'inviter': invites.name_of(maker), 'group': groups.summary(group)}), 200


@validate_session
def accept_invite(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    done = welcomed(invites.hashed(_body().get('code')), user_id)
    if not done:
        return jsonify(NO_LONGER), 404
    group = done[1]
    return jsonify({'message': f"You're in {group.name}." if group else "You're here already: welcome.",
                    'group': groups.summary(group)}), 200


def register(app_):
    invites.ensure_tables()
    app_.add_url_rule('/api/invites', view_func=list_invites, methods=['GET'])
    app_.add_url_rule('/api/invites', view_func=make_invite, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/invites/look', view_func=look_invite, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/invites/accept', view_func=accept_invite, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/invites/<invite_id>/revoke', view_func=revoke_invite, methods=['POST', 'OPTIONS'])
