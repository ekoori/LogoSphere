"""Your own account (Settings on the web, the Me tab in the app):

  POST /api/account/password   change your password; other devices are signed out
  POST /api/account/preferences  Simple or Advanced
  GET  /api/account/export     everything LogoSphere holds about you, as a JSON file
  POST /api/account/delete     delete your account (asks for your password)
  POST /api/password/reset     set a new password with an admin's one-time reset link
"""
import json
import logging
import uuid
from datetime import datetime

from flask import Response, current_app as app, jsonify, request

from app.db import session
from app.middleware.session_middleware import get_session_token, validate_session
from app.models.governance import _row_to_dict as proposal_dict
from app.models.meaning_trail import MeaningTrail
from app.models.notification import Notification
from app.models.openings import Service
from app.models.value_card import ValueCard
from app.routes.entities import KINDS, _entity_id, _members, _roles
from app.utils import password_reset, preferences
from app.utils.accounts import MIN_PASSWORD_LEN, end_sessions, password_matches, remove_account, set_password

logger = logging.getLogger(__name__)


def _options():
    return app.make_default_options_response(), 200


def _too_short(password):
    return len(password or '') < MIN_PASSWORD_LEN


@validate_session
def change_password(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    data = request.get_json(silent=True) or {}
    current, new = data.get('current_password') or '', data.get('new_password') or ''
    if not password_matches(user_id, current):
        return jsonify({'message': "That isn't your current password."}), 403
    if _too_short(new):
        return jsonify({'message': f'A password needs at least {MIN_PASSWORD_LEN} characters.'}), 400
    if new == current:
        return jsonify({'message': "That's the password you have already."}), 400
    set_password(user_id, new)
    ended = end_sessions(user_id, keep=get_session_token())
    logger.info(f'User {user_id} changed their password ({ended} other sessions ended)')
    return jsonify({
        'message': 'Password changed.' + (' Your other devices were signed out.' if ended else ''),
        'signed_out': ended,
    }), 200


@validate_session
def set_preferences(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    data = request.get_json(silent=True)
    mode = data.get('ui_mode') if isinstance(data, dict) else None
    if mode not in preferences.MODES:
        return jsonify({'message': 'Choose simple or advanced.'}), 400
    preferences.set_mode(user_id, mode)
    return jsonify({'ui_mode': mode}), 200


def _profile(uid):
    # writetime() tells whether a picture is set without loading it (as app/models/user.py does).
    row = session.execute(
        'SELECT user_id, name, surname, email, location, joined_datetime, is_platform_admin, ui_mode, '
        'picture_object, writetime(profile_picture) AS picture_wt FROM users WHERE user_id = %s', [uid]).one()
    if not row:
        return None
    return {
        'user_id': str(row.user_id), 'name': row.name, 'surname': row.surname, 'email': row.email,
        'location': row.location, 'joined': row.joined_datetime,
        'is_platform_admin': bool(getattr(row, 'is_platform_admin', False)),
        'ui_mode': preferences.mode_of(getattr(row, 'ui_mode', None)),
        'has_profile_picture': row.picture_wt is not None or bool(getattr(row, 'picture_object', None)),
    }


@validate_session
def export_data(user_id=None):
    """Everything about you, in one file: profile, value cards, memberships,
    openings, exchanges (with what both sides wrote), follows, your votes and
    notifications. Your password (stored only as a hash) and session tokens
    are never part of it; pictures are listed, not embedded."""
    uid = uuid.UUID(str(user_id))
    profile = _profile(uid)
    if not profile:
        return jsonify({'message': 'User not found'}), 404
    memberships = []
    for kind, k in KINDS.items():
        for entity in k['model'].get_all():
            roles = _roles(entity, k)
            if uid in _members(entity, k) or uid in roles:
                memberships.append({'kind': kind, 'id': str(_entity_id(entity, k)), 'name': entity.name,
                                    'role': roles.get(uid) or 'member'})
    openings = [s.to_dict(include_image=False) for s in Service.get_all()
                if s.provider_id == uid or getattr(s, 'acting_user_id', None) == uid]
    exchanges = MeaningTrail.get_meaning_trail(uid, viewer_id=uid) or []
    following = [str(r.followee_id) for r in session.execute('SELECT followee_id FROM follows WHERE follower_id = %s', [uid])]
    followers = [str(r.follower_id) for r in session.execute('SELECT follower_id, followee_id FROM follows') if r.followee_id == uid]
    # The governance tables are small: a scan beats a secondary index here.
    votes = [{'proposal_id': str(r.proposal_id), 'choice': r.choice, 'at': r.created_at}
             for r in session.execute('SELECT proposal_id, user_id, choice, created_at FROM governance_votes') if r.user_id == uid]
    proposals = [proposal_dict(r) for r in session.execute('SELECT * FROM governance_proposals') if r.created_by == uid]
    from app.models.acknowledgement import Acknowledgement
    acknowledgements = [
        {'on_trail': str(x.trail_id), 'text': x.body, 'cards': [c.get('title') for c in x.cards],
         'at': x.created_at, 'highlighted': bool(x.highlighted_at)}
        for x in Acknowledgement.everything() if x.author_id == uid]
    from app.utils.assist import uses_by
    from app.utils.meaning_graph import judgements_by
    out = {
        'exported_at': datetime.utcnow().isoformat() + 'Z',
        'note': 'Everything LogoSphere holds about you. Your password is stored only as a hash and is not included.',
        'profile': profile,
        'value_cards': [c.to_dict() for c in ValueCard.get_for_user(uid)],
        'memberships': memberships,
        'openings': openings,
        'exchanges': exchanges,
        'acknowledgements': acknowledgements,
        'meaning_graph_judgements': judgements_by(uid),
        'ai_help_used_lately': uses_by(uid),
        'following': following,
        'followers': followers,
        'governance': {'votes': votes, 'proposals': proposals},
        'notifications': Notification.list_for_user(uid),
    }
    body = json.dumps(out, default=str, indent=2, ensure_ascii=False)
    name = f"logosphere-data-{datetime.utcnow().strftime('%Y-%m-%d')}.json"
    return Response(body, mimetype='application/json',
                    headers={'Content-Disposition': f'attachment; filename="{name}"', 'Cache-Control': 'no-store'})


@validate_session
def delete_account(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    data = request.get_json(silent=True) or {}
    if not password_matches(user_id, data.get('password') or ''):
        return jsonify({'message': "That isn't your password."}), 403
    uid = uuid.UUID(str(user_id))
    me = session.execute('SELECT is_platform_admin FROM users WHERE user_id = %s', [uid]).one()
    if me and getattr(me, 'is_platform_admin', False):
        admins = [r for r in session.execute('SELECT user_id, is_platform_admin FROM users') if getattr(r, 'is_platform_admin', False)]
        if len(admins) <= 1:
            return jsonify({'message': "You're the only platform administrator. Make someone else one first."}), 400
    remove_account(uid)
    logger.info(f'User {uid} deleted their own account')
    resp = jsonify({'message': 'Your account was deleted.'})
    resp.delete_cookie('session_id')
    return resp, 200


def reset_password():
    """Redeems a one-time reset link: a new password, and every session ends."""
    if request.method == 'OPTIONS':
        return _options()
    data = request.get_json(silent=True) or {}
    token, new = (data.get('token') or '').strip(), data.get('password') or ''
    uid = password_reset.holder(token)
    if not uid:
        return jsonify({'message': 'This reset link has expired or was already used. Ask for a new one.'}), 400
    if _too_short(new):
        return jsonify({'message': f'A password needs at least {MIN_PASSWORD_LEN} characters.'}), 400
    set_password(uid, new)
    password_reset.spend(token)
    end_sessions(uid)
    logger.info(f'User {uid} reset their password with a link')
    return jsonify({'message': 'Your password was changed. Sign in with the new one.'}), 200


def register(app_):
    password_reset.ensure_tables()
    preferences.ensure_tables()
    app_.add_url_rule('/api/account/preferences', view_func=set_preferences, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/account/password', view_func=change_password, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/account/export', view_func=export_data, methods=['GET'])
    app_.add_url_rule('/api/account/delete', view_func=delete_account, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/password/reset', view_func=reset_password, methods=['POST', 'OPTIONS'])
