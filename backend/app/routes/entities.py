# File: ./backend/app/routes/entities.py
# Description: One generic route set for the three governance entities —
# spheres, alliances and projects. They used to have near-identical copies of
# detail/join/role/image handlers each; the differences (id column, member
# list, role vocabulary, who may manage) live in KINDS below and everything
# else is shared.
#
#   GET    /api/<kind>s/<id>                       detail (+members, value cards)
#   PATCH  /api/<kind>s/<id>                       name / description / join_policy
#   POST   /api/<kind>s/<id>/join                  join (or request to join)
#   POST   /api/<kind>s/<id>/members/<uid>/role    set role / approve / remove
#   GET    /api/<kind>s/<id>/image                 banner (public, cacheable)
#   POST   /api/<kind>s/<id>/image                 upload banner
import logging
import uuid

from flask import request, jsonify, current_app as app

from app.db import session
from app.models.spheres import Sphere
from app.models.alliance import Alliance
from app.models.project import Project
from app.models.user import User
from app.models.value_card import ValueCard
from app.utils.permissions import can_manage_entity, is_platform_admin
from app.utils.validation import is_supported_image, entity_image_response
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)

JOIN_POLICIES = ('open', 'approval')

KINDS = {
    'sphere': dict(
        table='spheres', id_col='sphere_id', model=Sphere,
        members_col='participants', roles_col='member_roles',
        default_role='member', assignable=('admin', 'member'),
        can_set_roles=lambda e, uid: uid in Sphere.admin_ids(e.sphere_id),
        needs_sphere=False, noun='sphere',
    ),
    'alliance': dict(
        table='alliances', id_col='alliance_id', model=Alliance,
        members_col='members', roles_col='member_roles',
        # Lead ('admin') is the founder and isn't assignable.
        default_role='member', assignable=('steward', 'member'),
        can_set_roles=lambda e, uid: uid in Alliance.lead_ids(e.alliance_id),
        needs_sphere=True, noun='alliance',
    ),
    'project': dict(
        table='projects', id_col='project_id', model=Project,
        members_col='participants', roles_col='participant_roles',
        default_role='contributor', assignable=('manager', 'steward', 'contributor'),
        can_set_roles=lambda e, uid: uid in Project.manager_ids(e.project_id),
        needs_sphere=True, noun='project',
    ),
}


def _kind(kind):
    k = KINDS.get(kind)
    if not k:
        raise KeyError(kind)
    return k


def _entity_id(entity, k):
    return getattr(entity, k['id_col'])


def _members(entity, k):
    return list(getattr(entity, k['members_col']) or [])


def _roles(entity, k):
    return dict(getattr(entity, k['roles_col']) or {})


def _can_view(entity, k, viewer):
    """Spheres are discoverable by every signed-in member (so they can be
    joined); alliances and projects are only visible inside their sphere."""
    if is_platform_admin(viewer):
        return True
    if not k['needs_sphere']:
        return True
    if viewer in _members(entity, k):
        return True
    if entity.sphere_id and entity.sphere_id in Sphere.member_sphere_ids(viewer):
        return True
    return not entity.sphere_id


def _detail_dict(entity, k, viewer):
    d = entity.to_dict(include_image=False)
    if k['noun'] == 'sphere':
        d['members'] = entity.members_list()
        d['alliance_list'] = Alliance.list_for_sphere(entity.sphere_id)
        d['project_list'] = Project.list_for_sphere(entity.sphere_id)
    d['value_cards'] = [c.to_dict() for c in ValueCard.get_for_user(_entity_id(entity, k))]
    d['can_manage'] = can_manage_entity(_entity_id(entity, k), viewer)
    if d['can_manage']:
        # Join requests awaiting approval (only meaningful to managers).
        roles = _roles(entity, k)
        pending_ids = [uid for uid, r in roles.items() if r == 'pending']
        from app.utils.names import resolve_user_names
        names = resolve_user_names(pending_ids)
        d['pending_members'] = [{'id': str(u), 'name': names.get(u, 'Member')} for u in pending_ids]
    return d


# ── Detail / basic edit ──────────────────────────────────────────────────────
@validate_session
def get_entity(kind, entity_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        k = _kind(kind)
        viewer = uuid.UUID(str(user_id))
        entity = k['model'].get_by_id(entity_id)
        if not entity or not _can_view(entity, k, viewer):
            return jsonify({'message': f'{k["noun"].capitalize()} not found'}), 404
        return jsonify(_detail_dict(entity, k, viewer)), 200
    except (KeyError, ValueError):
        return jsonify({'message': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in get_entity({kind}): {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def patch_entity(kind, entity_id, user_id=None):
    """Edit name / description / join_policy. Managers only."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        k = _kind(kind)
        eid = uuid.UUID(str(entity_id))
        entity = k['model'].get_by_id(eid)
        if not entity:
            return jsonify({'message': f'{k["noun"].capitalize()} not found'}), 404
        if not can_manage_entity(eid, user_id):
            return jsonify({'message': f'Not authorized to manage this {k["noun"]}'}), 403
        data = request.get_json(silent=True) or {}
        sets, params = [], []
        if 'name' in data:
            name = (data.get('name') or '').strip()
            if not name:
                return jsonify({'message': 'Name cannot be empty'}), 400
            sets.append('name = %s'); params.append(name)
        if 'description' in data:
            sets.append('description = %s'); params.append((data.get('description') or '').strip())
        if 'join_policy' in data:
            if data['join_policy'] not in JOIN_POLICIES:
                return jsonify({'message': 'join_policy must be "open" or "approval"'}), 400
            sets.append('join_policy = %s'); params.append(data['join_policy'])
        if not sets:
            return jsonify({'message': 'Nothing to update'}), 400
        params.append(eid)
        session.execute(f"UPDATE {k['table']} SET {', '.join(sets)} WHERE {k['id_col']} = %s", params)
        updated = k['model'].get_by_id(eid)
        return jsonify(_detail_dict(updated, k, uuid.UUID(str(user_id)))), 200
    except (KeyError, ValueError):
        return jsonify({'message': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in patch_entity({kind}): {e}")
        return jsonify({'message': 'Internal server error'}), 500


# ── Membership ───────────────────────────────────────────────────────────────
def _add_member(entity, k, uid, name):
    if k['noun'] == 'sphere':
        return Sphere.join(entity.sphere_id, uid)
    if k['noun'] == 'alliance':
        return Alliance.join(entity.alliance_id, uid, name)
    return Project.join(entity.project_id, uid, name)


def _set_role(entity, k, uid, role):
    k['model'].set_role(_entity_id(entity, k), uid, role)


def _remove_member(entity, k, uid):
    eid = _entity_id(entity, k)
    session.execute(
        f"UPDATE {k['table']} SET {k['members_col']} = {k['members_col']} - %s, "
        f"{k['roles_col']} = {k['roles_col']} - %s WHERE {k['id_col']} = %s",
        [[uid], {uid}, eid])


@validate_session
def join_entity(kind, entity_id, user_id=None):
    """Join an entity. With join_policy='approval' this records a pending
    request that a manager approves (or declines) from the members tab."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        k = _kind(kind)
        eid = uuid.UUID(str(entity_id))
        uid = uuid.UUID(str(user_id))
        # A Cassandra UPDATE is an upsert: joining a non-existent id would
        # otherwise create a phantom row. Verify it exists first.
        entity = k['model'].get_by_id(eid)
        if not entity:
            return jsonify({'message': f'{k["noun"].capitalize()} not found'}), 404
        if uid in _members(entity, k):
            return jsonify({'message': 'Already a member', 'already_member': True}), 200
        # An alliance/project lives inside a sphere: belong to that sphere first.
        if k['needs_sphere'] and entity.sphere_id \
                and entity.sphere_id not in Sphere.member_sphere_ids(uid) and not is_platform_admin(uid):
            return jsonify({'message': f"Join the {k['noun']}'s sphere first"}), 403

        user = User.get(str(uid))
        name = (f"{user.name or ''} {user.surname or ''}".strip() or user.email) if user else 'Member'

        policy = getattr(entity, 'join_policy', None) or 'open'
        if policy == 'approval' and not is_platform_admin(uid):
            if _roles(entity, k).get(uid) == 'pending':
                return jsonify({'message': 'Your request is awaiting approval', 'pending': True}), 200
            _set_role(entity, k, uid, 'pending')
            return jsonify({'message': 'Request sent - a manager will approve it', 'pending': True}), 202

        _add_member(entity, k, uid, name)
        return jsonify({'message': 'Joined successfully', 'already_member': False}), 200
    except (KeyError, ValueError):
        return jsonify({'message': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in join_entity({kind}): {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def set_entity_role(kind, entity_id, target_id, user_id=None):
    """Set a member's role. Also approves a pending join request (any
    assignable role) or, with role='remove', declines it / removes a member."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        k = _kind(kind)
        eid = uuid.UUID(str(entity_id))
        tid = uuid.UUID(str(target_id))
        actor = uuid.UUID(str(user_id))
        entity = k['model'].get_by_id(eid)
        if not entity:
            return jsonify({'message': f'{k["noun"].capitalize()} not found'}), 404
        if not (k['can_set_roles'](entity, actor) or is_platform_admin(actor)):
            return jsonify({'message': f'Only a {k["noun"]} manager can change roles'}), 403
        role = (request.get_json(silent=True) or {}).get('role')
        if role not in k['assignable'] and role != 'remove':
            return jsonify({'message': 'Invalid role'}), 400

        members = _members(entity, k)
        roles = _roles(entity, k)
        is_pending = roles.get(tid) == 'pending'
        if tid not in members and not is_pending:
            return jsonify({'message': f'That user is not a member of this {k["noun"]}'}), 404

        if role == 'remove':
            if tid == getattr(entity, 'admin1', None) or (k['noun'] == 'project' and roles.get(tid) == 'manager'):
                return jsonify({'message': 'The founder cannot be removed'}), 400
            _remove_member(entity, k, tid)
            return jsonify({'message': 'Removed', 'role': None}), 200

        if is_pending:
            user = User.get(str(tid))
            name = (f"{user.name or ''} {user.surname or ''}".strip() or user.email) if user else 'Member'
            _add_member(entity, k, tid, name)
        _set_role(entity, k, tid, role)
        return jsonify({'message': 'Role updated', 'role': role}), 200
    except (KeyError, ValueError):
        return jsonify({'message': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in set_entity_role({kind}): {e}")
        return jsonify({'message': 'Internal server error'}), 500


# ── Banner image ─────────────────────────────────────────────────────────────
def get_entity_image(kind, entity_id):
    """Serve the banner for <img src> - public + cacheable, keeping the blob
    out of list/detail JSON (loaded lazily per card)."""
    try:
        k = _kind(kind)
        return entity_image_response(k['model'].get_image(uuid.UUID(str(entity_id))))
    except (KeyError, ValueError, TypeError):
        return ('', 404)
    except Exception as e:
        logger.error(f"Error in get_entity_image({kind}): {e}")
        return ('', 404)


@validate_session
def update_entity_image(kind, entity_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        k = _kind(kind)
        eid = uuid.UUID(str(entity_id))
        if not k['model'].get_by_id(eid):
            return jsonify({'message': f'{k["noun"].capitalize()} not found'}), 404
        if not can_manage_entity(eid, user_id):
            return jsonify({'message': f'Not authorized to manage this {k["noun"]}'}), 403
        image_file = request.files.get('image')
        if not image_file:
            return jsonify({'message': 'image file is required'}), 400
        image_bytes = image_file.read()
        if not is_supported_image(image_bytes):
            return jsonify({'message': 'Unsupported image format (use JPEG, PNG, GIF or WebP)'}), 400
        k['model'].set_image(eid, image_bytes)
        return jsonify({'message': 'Image updated'}), 200
    except (KeyError, ValueError):
        return jsonify({'message': 'Not found'}), 404
    except Exception as e:
        logger.error(f"Error in update_entity_image({kind}): {e}")
        return jsonify({'message': 'Internal server error'}), 500


def register(app_):
    """Bind the generic handlers to the three kinds' URL prefixes."""
    for kind, k in KINDS.items():
        p = f"/api/{k['table']}"
        d = {'kind': kind}
        app_.add_url_rule(f'{p}/<entity_id>', endpoint=f'get_{kind}', view_func=get_entity, defaults=d, methods=['GET', 'OPTIONS'])
        app_.add_url_rule(f'{p}/<entity_id>', endpoint=f'patch_{kind}', view_func=patch_entity, defaults=d, methods=['PATCH'])
        app_.add_url_rule(f'{p}/<entity_id>/join', endpoint=f'join_{kind}', view_func=join_entity, defaults=d, methods=['POST', 'OPTIONS'])
        app_.add_url_rule(f'{p}/<entity_id>/members/<target_id>/role', endpoint=f'role_{kind}', view_func=set_entity_role, defaults=d, methods=['POST', 'OPTIONS'])
        app_.add_url_rule(f'{p}/<entity_id>/image', endpoint=f'image_get_{kind}', view_func=get_entity_image, defaults=d, methods=['GET'])
        app_.add_url_rule(f'{p}/<entity_id>/image', endpoint=f'image_put_{kind}', view_func=update_entity_image, defaults=d, methods=['POST', 'OPTIONS'])
