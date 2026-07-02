import logging
import uuid
from flask import request, jsonify, current_app as app
from app.models.project import Project
from app.models.user import User
from app.models.spheres import Sphere
from app.utils.permissions import can_manage_entity
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
                data['image'] = image_file.read()
        else:
            data = request.get_json() or {}
        if not data.get('name'):
            return jsonify({'message': 'Project name is required'}), 400
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
        projects = []
        for p in Project.get_all():
            # Sphere-scoped projects are only visible to that sphere's members
            # (an existing participant sees it regardless). Projects with no
            # sphere_id remain visible to everyone.
            is_participant = viewer in (p.participants or [])
            if p.sphere_id and p.sphere_id not in joined_spheres and not is_participant:
                continue
            projects.append(p.to_dict())
        logger.info(f"Retrieved {len(projects)} projects")
        return jsonify(projects), 200
    except Exception as e:
        logger.error(f"Error in get_projects: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def join_project(project_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        project_uuid = uuid.UUID(project_id)
        user_uuid = uuid.UUID(str(user_id))
        user = User.get(str(user_id))
        if not user:
            return jsonify({'message': 'User not found'}), 404
        user_name = f"{user.name or ''} {user.surname or ''}".strip() or user.email
        already_member = Project.join(project_uuid, user_uuid, user_name)
        return jsonify({'message': 'Already a contributor' if already_member else 'Joined successfully',
                        'already_member': already_member}), 200
    except Exception as e:
        logger.error(f"Error in join_project: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def update_project_image(project_id, user_id=None):
    """Set the project's banner image — from its management page."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        project_uuid = uuid.UUID(project_id)
        if not can_manage_entity(project_uuid, user_id):
            return jsonify({'message': 'Not authorized to manage this project'}), 403
        image_file = request.files.get('image')
        if not image_file:
            return jsonify({'message': 'image file is required'}), 400
        Project.set_image(project_uuid, image_file.read())
        return jsonify({'message': 'Image updated'}), 200
    except ValueError:
        return jsonify({'message': 'Invalid project id'}), 400
    except Exception as e:
        logger.error(f"Error in update_project_image: {e}")
        return jsonify({'message': 'Internal server error'}), 500
