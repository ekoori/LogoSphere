import logging
import uuid
from flask import request, jsonify, current_app as app
from app.models.project import Project
from app.models.user import User
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


@validate_session
def create_project(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
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
        projects = [p.to_dict() for p in Project.get_all()]
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
