"""The phones a member gets push notifications on (see app/utils/push).

  POST /api/push/devices         {"token": "<FCM token>", "platform": "android"}
  POST /api/push/devices/forget  {"token": "<FCM token>"}
"""
import logging

from flask import request, jsonify, current_app as app

from app.middleware.session_middleware import validate_session, get_session_token
from app.utils import push

logger = logging.getLogger(__name__)


def _token():
    token = ((request.get_json(silent=True) or {}).get('token') or '').strip()
    return token if 0 < len(token) <= 4096 else None


@validate_session
def register_device(user_id=None):
    """This phone gets the signed-in member's notifications until this session ends."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    token = _token()
    platform = (request.get_json(silent=True) or {}).get('platform') or 'android'
    if token is None or platform not in push.PLATFORMS:
        return jsonify({'message': 'A device token and a known platform are needed'}), 400
    push.register(user_id, token, get_session_token(), platform)
    return jsonify({'registered': True, 'sending': push.enabled()}), 200


@validate_session
def forget_device(user_id=None):
    """This phone stops getting the member's notifications (at sign-out)."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    token = _token()
    if token is None:
        return jsonify({'message': 'A device token is needed'}), 400
    push.forget(user_id, token)
    return jsonify({'forgotten': True}), 200
