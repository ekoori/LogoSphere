import logging
import uuid
from flask import request, jsonify, current_app as app, Response
from app.models.project import Project
from app.models.user import User
from app.models.spheres import Sphere
from app.utils.permissions import can_manage_entity, get_entity_info, entity_sphere_ids, is_platform_admin
from app.utils.validation import is_supported_image, entity_image_response
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


def get_project_image(project_id):
    """Serve a project's banner for <img src> — public + cacheable, keeping the
    blob out of the projects list JSON (loaded lazily per card)."""
    try:
        return entity_image_response(Project.get_image(uuid.UUID(project_id)))
    except (ValueError, TypeError):
        return ('', 404)
    except Exception as e:
        logger.error(f"Error in get_project_image: {e}")
        return ('', 404)


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
        projects = []
        for p in Project.get_all():
            # Sphere-scoped projects are only visible to that sphere's members
            # (an existing participant sees it regardless). Projects with no
            # sphere_id remain visible to everyone. Platform admins see all.
            is_participant = viewer in (p.participants or [])
            if not see_all and p.sphere_id and p.sphere_id not in joined_spheres and not is_participant:
                continue
            # Image served via GET /api/projects/<id>/image (see has_image).
            projects.append(p.to_dict(include_image=False))
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
        project = Project.get_by_id(project_uuid)
        if not project:
            return jsonify({'message': 'Project not found'}), 404
        # A project lives inside a sphere: you must belong to that sphere first.
        if project.sphere_id and project.sphere_id not in Sphere.member_sphere_ids(user_uuid) \
                and not is_platform_admin(user_uuid):
            return jsonify({'message': "Join the project's sphere first"}), 403
        already_member = Project.join(project_uuid, user_uuid, user_name)
        return jsonify({'message': 'Already a contributor' if already_member else 'Joined successfully',
                        'already_member': already_member}), 200
    except ValueError:
        return jsonify({'message': 'Invalid project id'}), 400
    except Exception as e:
        logger.error(f"Error in join_project: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def set_project_role(project_id, target_id, user_id=None):
    """A manager promotes/demotes a contributor. Roles: 'steward' (acts on behalf
    of the manager) or 'contributor'."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        pid = uuid.UUID(project_id)
        tid = uuid.UUID(target_id)
        if uuid.UUID(str(user_id)) not in Project.manager_ids(pid):
            return jsonify({'message': 'Only a project manager can change roles'}), 403
        role = (request.get_json() or {}).get('role')
        if role not in ('steward', 'contributor', 'manager'):
            return jsonify({'message': 'Invalid role'}), 400
        project = Project.get_by_id(pid)
        if not project:
            return jsonify({'message': 'Project not found'}), 404
        if tid not in (project.participants or []):
            return jsonify({'message': 'That user is not a contributor to this project'}), 404
        Project.set_role(pid, tid, role)
        return jsonify({'message': 'Role updated', 'role': role}), 200
    except ValueError:
        return jsonify({'message': 'Invalid id'}), 400
    except Exception as e:
        logger.error(f"Error in set_project_role: {e}")
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
        image_bytes = image_file.read()
        if not is_supported_image(image_bytes):
            return jsonify({'message': 'Unsupported image format (use JPEG, PNG, GIF or WebP)'}), 400
        Project.set_image(project_uuid, image_bytes)
        return jsonify({'message': 'Image updated'}), 200
    except ValueError:
        return jsonify({'message': 'Invalid project id'}), 400
    except Exception as e:
        logger.error(f"Error in update_project_image: {e}")
        return jsonify({'message': 'Internal server error'}), 500
