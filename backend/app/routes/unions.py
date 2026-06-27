import logging
import uuid
from flask import request, jsonify, current_app as app
from app.models.union import Union
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


@validate_session
def create_union(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        if not data.get('name'):
            return jsonify({'message': 'Union name is required'}), 400
        new_union = Union.create(data=data, admin1=uuid.UUID(str(user_id)))
        logger.info(f"Created union {new_union.union_id}")
        return jsonify(new_union.to_dict()), 201
    except Exception as e:
        logger.error(f"Error in create_union: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def get_unions(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        unions = [u.to_dict() for u in Union.get_all()]
        logger.info(f"Retrieved {len(unions)} unions")
        return jsonify(unions), 200
    except Exception as e:
        logger.error(f"Error in get_unions: {e}")
        return jsonify({'message': 'Internal server error'}), 500
