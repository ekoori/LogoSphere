import logging
import uuid
from flask import request, jsonify, current_app as app
from app.models.marketplace import Service
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


@validate_session
def create_service(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        if not data.get('title'):
            return jsonify({'message': 'Service title is required'}), 400
        new_service = Service.create(data=data, provider_id=uuid.UUID(str(user_id)))
        logger.info(f"Created service {new_service.service_id}")
        return jsonify(new_service.to_dict()), 201
    except Exception as e:
        logger.error(f"Error in create_service: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def get_services(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        services = [s.to_dict() for s in Service.get_all()]
        logger.info(f"Retrieved {len(services)} services")
        return jsonify(services), 200
    except Exception as e:
        logger.error(f"Error in get_services: {e}")
        return jsonify({'message': 'Internal server error'}), 500
