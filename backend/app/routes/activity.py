"""Activity and connections (app/utils/activity.py):

  GET /api/activity             what the people you follow did lately
  GET /api/users/<id>/known     whom you both know
"""
from flask import jsonify

from app.middleware.session_middleware import validate_session
from app.utils import activity


@validate_session
def get_activity(user_id=None):
    return jsonify({'activity': activity.of_followed(user_id)}), 200


@validate_session
def get_known(target_id, user_id=None):
    return jsonify({'people': activity.both_know(user_id, target_id)}), 200


def register(app_):
    app_.add_url_rule('/api/activity', view_func=get_activity, methods=['GET'])
    app_.add_url_rule('/api/users/<target_id>/known', view_func=get_known, methods=['GET'])
