import logging
import uuid
from flask import request, jsonify, current_app as app
from app.models.alliance import Alliance
from app.models.user import User
from app.models.spheres import Sphere
from app.utils.permissions import can_manage_entity
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
        viewer = uuid.UUID(str(user_id))
        joined_spheres = Sphere.member_sphere_ids(viewer)
        alliances = []
        for a in Alliance.get_all():
            # Sphere-scoped alliances are only visible to that sphere's members
            # (an existing alliance member sees it regardless). Alliances with
            # no sphere_id remain visible to everyone.
            is_member = viewer in (a.members or [])
            if a.sphere_id and a.sphere_id not in joined_spheres and not is_member:
                continue
            alliances.append(a.to_dict())
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


@validate_session
def update_alliance_image(alliance_id, user_id=None):
    """Set the alliance's banner image — from its management page."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        alliance_uuid = uuid.UUID(alliance_id)
        if not can_manage_entity(alliance_uuid, user_id):
            return jsonify({'message': 'Not authorized to manage this alliance'}), 403
        image_file = request.files.get('image')
        if not image_file:
            return jsonify({'message': 'image file is required'}), 400
        Alliance.set_image(alliance_uuid, image_file.read())
        return jsonify({'message': 'Image updated'}), 200
    except ValueError:
        return jsonify({'message': 'Invalid alliance id'}), 400
    except Exception as e:
        logger.error(f"Error in update_alliance_image: {e}")
        return jsonify({'message': 'Internal server error'}), 500
