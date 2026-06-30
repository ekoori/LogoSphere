import logging
import uuid
from flask import request, jsonify, current_app as app
from app.models.openings import Service
from app.models.user import User
from app.models.meaning_trail import MeaningTrail
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


@validate_session
def accept_service(service_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        service_uuid = uuid.UUID(service_id)
        service = Service.get_by_id(service_uuid)
        if not service:
            return jsonify({'message': 'Opening not found'}), 404
        if str(service.provider_id) == str(user_id):
            return jsonify({'message': 'You cannot accept your own opening'}), 400
        if service.cadence != 'perpetual' and service.status == 'Accepted':
            return jsonify({'message': 'This opening has already been accepted'}), 409

        accepter = User.get(str(user_id))
        if not accepter:
            return jsonify({'message': 'User not found'}), 404
        accepter_name = f"{accepter.name or ''} {accepter.surname or ''}".strip() or accepter.email

        if service.cadence != 'perpetual':
            Service.mark_accepted(service_uuid, uuid.UUID(str(user_id)), accepter_name)

        exchange_id = MeaningTrail.create_for_opening(
            initiator_id=service.provider_id,
            other_user_id=user_id,
            other_user_name=accepter_name,
            description=service.title,
            project_name=service.project_name,
        )
        if not exchange_id:
            return jsonify({'message': 'Failed to create exchange'}), 500
        logger.info(f"Opening {service_id} accepted by {user_id}, exchange {exchange_id}")
        return jsonify({'message': 'Accepted', 'exchange_id': str(exchange_id)}), 200
    except ValueError:
        return jsonify({'message': 'Invalid opening id'}), 400
    except Exception as e:
        logger.error(f"Error in accept_service: {e}")
        return jsonify({'message': 'Internal server error'}), 500
