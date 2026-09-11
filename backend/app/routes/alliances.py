import logging
import uuid
from flask import request, jsonify, current_app as app
from app.models.alliance import Alliance
from app.models.value_card import ValueCard
from app.models.user import User
from app.models.spheres import Sphere
from app.utils.permissions import can_manage_entity, is_platform_admin
from app.utils.validation import is_supported_image, entity_image_response
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


@validate_session
def create_alliance(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.form.to_dict()
            image_file = request.files.get('image')
            if image_file:
                image_bytes = image_file.read()
                if not is_supported_image(image_bytes):
                    return jsonify({'message': 'Unsupported image format (use JPEG, PNG, GIF or WebP)'}), 400
                data['image'] = image_bytes
        else:
            data = request.get_json() or {}
        if not data.get('name'):
            return jsonify({'message': 'Alliance name is required'}), 400
        if not data.get('sphere_id'):
            return jsonify({'message': 'An operating sphere is required'}), 400
        # Record the founder's display name so they aren't shown as a generic member.
        creator = User.get(str(user_id))
        if creator:
            data['member_names'] = [f"{creator.name or ''} {creator.surname or ''}".strip() or creator.email]
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
        see_all = is_platform_admin(viewer)
        rows = Alliance.get_all()
        cards = ValueCard.get_for_users([a.alliance_id for a in rows])
        alliances = []
        for a in rows:
            # Sphere-scoped alliances are only visible to that sphere's members
            # (an existing alliance member sees it regardless). Alliances with
            # no sphere_id remain visible to everyone. Platform admins see all.
            is_member = viewer in (a.members or [])
            if not see_all and a.sphere_id and a.sphere_id not in joined_spheres and not is_member:
                continue
            d = a.to_dict(include_image=False)
            d['value_cards'] = [c.to_dict() for c in cards.get(a.alliance_id, [])]
            alliances.append(d)
        logger.info(f"Retrieved {len(alliances)} alliances")
        return jsonify(alliances), 200
    except Exception as e:
        logger.error(f"Error in get_alliances: {e}")
        return jsonify({'message': 'Internal server error'}), 500


