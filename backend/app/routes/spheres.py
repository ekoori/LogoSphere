import logging
from flask import request, jsonify, current_app as app
from app.models.spheres import Sphere
from app.models.value_card import ValueCard
from app.utils.permissions import can_manage_entity, is_platform_admin
from app.utils.validation import is_supported_image, entity_image_response
from app.middleware.session_middleware import validate_session
import uuid

logger = logging.getLogger(__name__)


@validate_session
def create_sphere(user_id=None):
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response, 200

    try:
        if 'multipart/form-data' in request.content_type:
            data = request.form
            image = request.files.get('image')
            if image:
                image = image.read()
        else:
            data = request.get_json()
            image = data.get('image')

        logger.debug(f"Received sphere creation data: {data}")
        if not data:
            logger.error("No data provided for sphere creation")
            response = jsonify({'message': 'No data provided'})
            return response, 400

        logger.info(f"Creating new sphere by user_id: {user_id}")
        
        # Ensure user_id is a UUID
        user_id = uuid.UUID(str(user_id))
        
        # Create new sphere
        new_sphere = Sphere.create(
            data={
                'name': data.get('name'),
                'description': data.get('description'),
                'meaning_graph': data.get('meaning_graph'),
                'location': data.get('location'),
                'image': image
            },
            admin1=user_id
        )
        
        if new_sphere:
            logger.info(f"Successfully created new sphere with sphere_id: {new_sphere.sphere_id}")
            response = jsonify(new_sphere.to_dict())
            return response, 201
        else:
            logger.error("Failed to create new sphere")
            response = jsonify({'message': 'Failed to create new sphere'})
            return response, 400

    except Exception as e:
        logger.error(f"Error in create_sphere: {str(e)}")
        response = jsonify({'message': 'Internal server error'})
        return response, 500

@validate_session
def get_spheres(user_id=None):
    """Every sphere (they're discoverable so people can join), with members
    and current value cards embedded - no per-card follow-up requests."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        spheres = Sphere.get_all()
        cards = ValueCard.get_for_users([s.sphere_id for s in spheres])
        out = []
        for sp in spheres:
            d = sp.to_dict(include_members=True, include_image=False)
            d['participant_names'] = [m['name'] for m in d['members']]
            d['value_cards'] = [c.to_dict() for c in cards.get(sp.sphere_id, [])]
            out.append(d)
        return jsonify(out), 200
    except Exception as e:
        logger.error(f"Error in get_spheres: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def update_sphere_governance(sphere_id, user_id=None):
    """Update a sphere's governance flags from its management page.

    - `is_public` (logged-out visitors can view the sphere's activity) may be
      set by anyone who can manage the sphere — its admin or a platform admin.
    - `is_sandbox` (auto-enroll every new user) is a platform-wide decision, so
      only platform administrators may set it.
    """
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        sphere_uuid = uuid.UUID(sphere_id)
        data = request.get_json(silent=True) or {}

        is_public = data.get('is_public')
        is_sandbox = data.get('is_sandbox')

        if is_public is not None and not can_manage_entity(sphere_uuid, user_id):
            return jsonify({'message': 'Not authorized to manage this sphere'}), 403
        if is_sandbox is not None and not is_platform_admin(user_id):
            return jsonify({'message': 'Only a platform administrator can make a sphere a sandbox'}), 403

        Sphere.set_governance(
            sphere_uuid,
            is_sandbox=None if is_sandbox is None else bool(is_sandbox),
            is_public=None if is_public is None else bool(is_public))
        updated = Sphere.get_by_id(sphere_uuid)
        return jsonify({'message': 'Governance updated',
                        'is_sandbox': updated.is_sandbox if updated else False,
                        'is_public': updated.is_public if updated else False}), 200
    except ValueError:
        return jsonify({'message': 'Invalid sphere id'}), 400
    except Exception as e:
        logger.error(f"Error in update_sphere_governance: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


def get_public_sphere(sphere_id):
    """Public, no-auth view of a sphere's activity — only when the sphere has
    been flagged `is_public`. Returns the sphere plus its projects, alliances
    and openings so logged-out visitors can see what's happening inside."""
    try:
        sphere = Sphere.get_by_id(sphere_id)
        if not sphere or not sphere.is_public:
            return jsonify({'message': 'This sphere is not public'}), 404

        # Imported here to avoid a heavy import graph at module load.
        from app.models.project import Project
        from app.models.alliance import Alliance
        from app.models.openings import Service

        sid = sphere.sphere_id
        d = sphere.to_dict(include_members=True, include_image=False)

        d['project_list'] = [
            p.to_dict(include_image=False) for p in Project.get_all()
            if getattr(p, 'sphere_id', None) == sid]
        d['alliance_list'] = [
            a.to_dict(include_image=False) for a in Alliance.get_all()
            if getattr(a, 'sphere_id', None) == sid]
        d['openings'] = [
            s.to_dict(include_image=False) for s in Service.get_all()
            if getattr(s, 'sphere_id', None) == sid and s.is_current
            and (s.cadence == 'perpetual' or s.status not in ('In Progress', 'Completed'))]
        return jsonify(d), 200
    except ValueError:
        return jsonify({'message': 'Invalid sphere id'}), 400
    except Exception as e:
        logger.error(f"Error in get_public_sphere: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500
