import logging
from flask import request, jsonify, current_app as app
from app.models.spheres import Sphere
from app.utils.permissions import can_manage_entity, is_platform_admin
from app.utils.validation import is_supported_image, entity_image_response
from app.middleware.session_middleware import validate_session
import uuid

logger = logging.getLogger(__name__)


def get_sphere_image(sphere_id):
    """Serve a sphere's banner for <img src> — public + cacheable, keeping the
    blob out of the spheres list JSON (loaded lazily per page)."""
    try:
        return entity_image_response(Sphere.get_image(uuid.UUID(sphere_id)))
    except (ValueError, TypeError):
        return ('', 404)
    except Exception as e:
        logger.error(f"Error in get_sphere_image: {e}")
        return ('', 404)

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
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response, 200

    try:
        logger.info(f"Fetching spheres for user_id: {user_id}")

        session = app.session_interface.cassandra_session

        # Build a {user_id: name} map once so participant UUIDs render as names.
        name_by_id = {}
        for u in session.execute("SELECT user_id, name FROM users"):
            name_by_id[u.user_id] = u.name

        rows = session.execute("SELECT * FROM spheres")

        spheres = []
        sphere_ids = set()
        for row in rows:
            if row.sphere_id in sphere_ids:
                logger.warning(f"Duplicate sphere_id found: {row.sphere_id}")
                continue
            sphere_ids.add(row.sphere_id)
            sphere = Sphere(
                sphere_id=row.sphere_id,
                name=row.name,
                description=row.description,
                meaning_graph=row.meaning_graph,
                location=row.location,
                image=row.image,
                admin1=row.admin1,
                participants=row.participants,
                alliances=row.alliances,
                projects=row.projects,
                values=row.values,
                member_roles=getattr(row, 'member_roles', None),
                is_sandbox=getattr(row, 'is_sandbox', False),
                is_public=getattr(row, 'is_public', False)
            )
            # Banner images are served separately via GET /api/spheres/<id>/image
            # (see has_image) — keeping the base64 blob out of the list response.
            sphere_dict = sphere.to_dict(include_image=False)
            # Resolve participant UUIDs to display names, and provide {id,name,role}
            # pairs so the frontend can link each member to their profile and show
            # their role. admin1 is 'admin'; an explicit member_roles entry wins.
            roles = getattr(row, 'member_roles', None) or {}
            sphere_dict['participant_names'] = [
                name_by_id.get(pid, 'Member') for pid in (row.participants or [])
            ]
            sphere_dict['members'] = [
                {'id': str(pid), 'name': name_by_id.get(pid, 'Member'),
                 'role': roles.get(pid) or ('admin' if row.admin1 and pid == row.admin1 else 'member')}
                for pid in (row.participants or [])
            ]
            spheres.append(sphere_dict)

        logger.info(f"Successfully retrieved {len(spheres)} spheres")
        response = jsonify(spheres)
        return response, 200

    except Exception as e:
        logger.error(f"Error in get_spheres: {str(e)}")
        response = jsonify({'message': 'Internal server error'})
        return response, 500


@validate_session
def join_sphere(sphere_id, user_id=None):
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response, 200
    try:
        sphere_uuid = uuid.UUID(sphere_id)
        user_uuid = uuid.UUID(str(user_id))
        # A Cassandra UPDATE is an upsert: joining a non-existent id would
        # otherwise create a phantom sphere row. Verify it exists first.
        if not Sphere.get_by_id(sphere_uuid):
            return jsonify({'message': 'Sphere not found'}), 404
        already_member = Sphere.join(sphere_uuid, user_uuid)
        return jsonify({
            'message': 'Already a member' if already_member else 'Joined successfully',
            'already_member': already_member,
        }), 200
    except ValueError:
        return jsonify({'message': 'Invalid sphere id'}), 400
    except Exception as e:
        logger.error(f"Error in join_sphere: {str(e)}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def set_sphere_role(sphere_id, target_id, user_id=None):
    """A sphere admin promotes/demotes another member (role: 'admin' | 'member')."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        sid = uuid.UUID(sphere_id)
        tid = uuid.UUID(target_id)
        if uuid.UUID(str(user_id)) not in Sphere.admin_ids(sid):
            return jsonify({'message': 'Only a sphere admin can change roles'}), 403
        role = (request.get_json() or {}).get('role')
        if role not in ('admin', 'member'):
            return jsonify({'message': 'Invalid role'}), 400
        sphere = Sphere.get_by_id(sid)
        if not sphere:
            return jsonify({'message': 'Sphere not found'}), 404
        if tid not in (sphere.participants or []):
            return jsonify({'message': 'That user is not a member of this sphere'}), 404
        Sphere.set_role(sid, tid, role)
        return jsonify({'message': 'Role updated', 'role': role}), 200
    except ValueError:
        return jsonify({'message': 'Invalid id'}), 400
    except Exception as e:
        logger.error(f"Error in set_sphere_role: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def update_sphere_image(sphere_id, user_id=None):
    """Set the sphere's banner image — from its management page."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        sphere_uuid = uuid.UUID(sphere_id)
        if not can_manage_entity(sphere_uuid, user_id):
            return jsonify({'message': 'Not authorized to manage this sphere'}), 403
        image_file = request.files.get('image')
        if not image_file:
            return jsonify({'message': 'image file is required'}), 400
        image_bytes = image_file.read()
        if not is_supported_image(image_bytes):
            return jsonify({'message': 'Unsupported image format (use JPEG, PNG, GIF or WebP)'}), 400
        Sphere.set_image(sphere_uuid, image_bytes)
        return jsonify({'message': 'Image updated'}), 200
    except ValueError:
        return jsonify({'message': 'Invalid sphere id'}), 400
    except Exception as e:
        logger.error(f"Error in update_sphere_image: {str(e)}")
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
