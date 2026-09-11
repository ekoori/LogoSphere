import logging
import uuid
from flask import request, jsonify, current_app as app, Response
from app.models.project import Project
from app.models.value_card import ValueCard
from app.models.user import User
from app.models.spheres import Sphere
from app.utils.permissions import can_manage_entity, get_entity_info, entity_sphere_ids, is_platform_admin
from app.utils.validation import is_supported_image, entity_image_response
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


@validate_session
def create_project(user_id=None):
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
            return jsonify({'message': 'Project name is required'}), 400
        if not data.get('sphere_id'):
            return jsonify({'message': 'A sphere is required'}), 400
        # Record the founder's display name so they aren't shown as a generic member.
        creator = User.get(str(user_id))
        creator_name = None
        if creator:
            creator_name = f"{creator.name or ''} {creator.surname or ''}".strip() or creator.email
            data['participant_names'] = [creator_name]
        # Optionally run the project on behalf of an alliance the founder manages
        # (must be an alliance within the project's sphere). Stored as the
        # alliance name (like the seed data) so the card can link to it.
        alliance_id = data.get('owner_alliance_id')
        if alliance_id:
            info = get_entity_info(alliance_id)
            if not info or info['kind'] != 'alliance':
                return jsonify({'message': 'That is not an alliance'}), 400
            if not can_manage_entity(alliance_id, user_id):
                return jsonify({'message': 'Not authorized to act on behalf of this alliance'}), 403
            if str(data['sphere_id']) not in entity_sphere_ids(alliance_id):
                return jsonify({'message': "That alliance isn't part of the project's sphere"}), 400
            data['owner_alliance'] = info['name']
        else:
            data['owner_alliance'] = ''
        # Owner text = the founder's name (display); linking uses owner_id from
        # the manager member in to_dict.
        data['owner'] = creator_name or str(user_id)
        new_project = Project.create(data=data, owner_id=uuid.UUID(str(user_id)))
        logger.info(f"Created project {new_project.project_id}")
        return jsonify(new_project.to_dict()), 201
    except Exception as e:
        logger.error(f"Error in create_project: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def get_projects(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        viewer = uuid.UUID(str(user_id))
        joined_spheres = Sphere.member_sphere_ids(viewer)
        see_all = is_platform_admin(viewer)
        rows = Project.get_all()
        cards = ValueCard.get_for_users([p.project_id for p in rows])
        projects = []
        for p in rows:
            # Sphere-scoped projects are only visible to that sphere's members
            # (an existing participant sees it regardless). Projects with no
            # sphere_id remain visible to everyone. Platform admins see all.
            is_participant = viewer in (p.participants or [])
            if not see_all and p.sphere_id and p.sphere_id not in joined_spheres and not is_participant:
                continue
            d = p.to_dict(include_image=False)
            d['value_cards'] = [c.to_dict() for c in cards.get(p.project_id, [])]
            projects.append(d)
        logger.info(f"Retrieved {len(projects)} projects")
        return jsonify(projects), 200
    except Exception as e:
        logger.error(f"Error in get_projects: {e}")
        return jsonify({'message': 'Internal server error'}), 500


