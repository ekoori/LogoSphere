import logging
import uuid
from flask import request, jsonify, current_app as app
from app.models.alliance import Alliance
from app.models.user import User
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


@validate_session
def create_alliance(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        if not data.get('name'):
            return jsonify({'message': 'Alliance name is required'}), 400
        new_alliance = Alliance.create(data=data, admin1=uuid.UUID(str(user_id)))
        logger.info(f"Created alliance {new_alliance.alliance_id}")
        return jsonify(new_alliance.to_dict()), 201
    except Exception as e:
        logger.error(f"Error in create_alliance: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def get_alliances(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        alliances = [a.to_dict() for a in Alliance.get_all()]
        logger.info(f"Retrieved {len(alliances)} alliances")
        return jsonify(alliances), 200
    except Exception as e:
        logger.error(f"Error in get_alliances: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def join_alliance(alliance_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        alliance_uuid = uuid.UUID(alliance_id)
        user_uuid = uuid.UUID(str(user_id))
        user = User.get(str(user_id))
        if not user:
            return jsonify({'message': 'User not found'}), 404
        user_name = f"{user.name or ''} {user.surname or ''}".strip() or user.email
        already_member = Alliance.join(alliance_uuid, user_uuid, user_name)
        return jsonify({'message': 'Already a member' if already_member else 'Joined successfully',
                        'already_member': already_member}), 200
    except Exception as e:
        logger.error(f"Error in join_alliance: {e}")
        return jsonify({'message': 'Internal server error'}), 500
