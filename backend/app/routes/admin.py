# File: ./backend/app/routes/admin.py
# Description: Platform administration - every endpoint here requires the
# caller's users.is_platform_admin flag (see utils/permissions.py). The admin
# page lists everything and can correct it: users (grant/revoke admin, fix a
# name, delete an account), spheres / alliances / projects (edit via the
# normal PATCH endpoints, delete here with a dependency check) and openings
# (withdraw via the normal cancel endpoint, delete here when nothing hangs
# off them).
#
#   GET    /api/admin/overview
#   GET    /api/admin/users              PATCH/DELETE /api/admin/users/<id>
#   GET    /api/admin/spheres            DELETE /api/admin/spheres/<id>
#   GET    /api/admin/alliances          DELETE /api/admin/alliances/<id>
#   GET    /api/admin/projects           DELETE /api/admin/projects/<id>
#   GET    /api/admin/openings           DELETE /api/admin/openings/<id>
import logging
import uuid
from functools import wraps

from flask import request, jsonify, current_app as app

from app.db import session
from app.middleware.session_middleware import validate_session
from app.models.alliance import Alliance
from app.models.openings import Service
from app.models.project import Project
from app.models.spheres import Sphere
from app.models.value_card import ValueCard
from app.routes.entities import KINDS, _members, _roles, _remove_member
from app.utils.permissions import is_platform_admin, forget_admin_flag
from app.utils.search_vectors import invalidate_index

logger = logging.getLogger(__name__)


def admin_only(fn):
    """validate_session + platform-admin gate + OPTIONS preflight, in one."""
    @wraps(fn)
    @validate_session
    def wrapper(*args, user_id=None, **kwargs):
        if request.method == 'OPTIONS':
            return app.make_default_options_response(), 200
        if not is_platform_admin(user_id):
            return jsonify({'message': 'Platform administrators only'}), 403
        try:
            return fn(*args, user_id=user_id, **kwargs)
        except ValueError:
            return jsonify({'message': 'Invalid id'}), 400
        except Exception as e:
            logger.error(f"Error in admin.{fn.__name__}: {e}")
            return jsonify({'message': 'Internal server error'}), 500
    return wrapper


def _user_rows():
    return list(session.execute(
        "SELECT user_id, email, name, surname, location, is_platform_admin, joined_datetime FROM users"))


def _full_name(r):
    return f"{getattr(r, 'name', '') or ''} {getattr(r, 'surname', '') or ''}".strip() or getattr(r, 'email', '') or 'Member'


def _card_counts():
    counts = {}
    for r in session.execute("SELECT user_id, is_current FROM value_cards"):
        if getattr(r, 'is_current', True) is not False:
            counts[r.user_id] = counts.get(r.user_id, 0) + 1
    return counts


# ── Overview ─────────────────────────────────────────────────────────────────
@admin_only
def overview(user_id=None):
    users = _user_rows()
    spheres = Sphere.get_all()
    alliances = Alliance.get_all()
    projects = Project.get_all()
    openings = [s for s in Service.get_all() if s.is_current]
    open_now = [s for s in openings if s.status not in ('Cancelled', 'Completed')
                and not (s.cadence != 'perpetual' and s.status == 'In Progress')]
    exchanges = {r.exchange_id for r in session.execute("SELECT exchange_id FROM meaning_trail")}
    admins = [{'id': str(r.user_id), 'name': _full_name(r), 'email': r.email}
              for r in users if getattr(r, 'is_platform_admin', False)]
    return jsonify({
        'counts': {
            'users': len(users), 'platform_admins': len(admins),
            'spheres': len(spheres), 'alliances': len(alliances), 'projects': len(projects),
            'openings': len(openings), 'openings_open': len(open_now), 'exchanges': len(exchanges),
            'sandbox_spheres': sum(1 for s in spheres if getattr(s, 'is_sandbox', False)),
            'public_spheres': sum(1 for s in spheres if getattr(s, 'is_public', False)),
        },
        'platform_admins': admins,
    }), 200


# ── Users ────────────────────────────────────────────────────────────────────
@admin_only
def list_users(user_id=None):
    sphere_counts = {}
    for s in Sphere.get_all():
        for m in s.participants or []:
            sphere_counts[m] = sphere_counts.get(m, 0) + 1
    cards = _card_counts()
    out = []
    for r in _user_rows():
        out.append({
            'id': str(r.user_id), 'name': r.name, 'surname': r.surname, 'full_name': _full_name(r),
            'email': r.email, 'location': r.location,
            'is_platform_admin': bool(getattr(r, 'is_platform_admin', False)),
            'joined_at': r.joined_datetime.isoformat() if getattr(r, 'joined_datetime', None) else None,
            'sphere_count': sphere_counts.get(r.user_id, 0),
            'card_count': cards.get(r.user_id, 0),
            'is_you': str(r.user_id) == str(user_id),
        })
    out.sort(key=lambda u: (u['full_name'] or '').lower())
    return jsonify({'users': out}), 200


@admin_only
def patch_user(target_id, user_id=None):
    tid = uuid.UUID(str(target_id))
    row = session.execute("SELECT user_id, email, name, is_platform_admin FROM users WHERE user_id = %s", [tid]).one()
    if not row:
        return jsonify({'message': 'User not found'}), 404
    data = request.get_json(silent=True) or {}
    sets, params = [], []
    if 'is_platform_admin' in data:
        want = bool(data['is_platform_admin'])
        if tid == uuid.UUID(str(user_id)):
            return jsonify({'message': "You can't change your own administrator flag"}), 400
        if not want and getattr(row, 'is_platform_admin', False):
            others = [r for r in _user_rows() if getattr(r, 'is_platform_admin', False) and r.user_id != tid]
            if not others:
                return jsonify({'message': 'There must be at least one platform administrator'}), 400
        sets.append('is_platform_admin = %s'); params.append(want)
    for field in ('name', 'surname', 'location'):
        if field in data:
            value = (data.get(field) or '').strip()
            if field == 'name' and not value:
                return jsonify({'message': 'Name cannot be empty'}), 400
            sets.append(f'{field} = %s'); params.append(value or None)
    if not sets:
        return jsonify({'message': 'Nothing to update'}), 400
    params.append(tid)
    session.execute(f"UPDATE users SET {', '.join(sets)} WHERE user_id = %s", params)
    forget_admin_flag(tid)
    invalidate_index()
    updated = session.execute(
        "SELECT user_id, email, name, surname, location, is_platform_admin FROM users WHERE user_id = %s", [tid]).one()
    return jsonify({'message': 'User updated', 'user': {
        'id': str(updated.user_id), 'name': updated.name, 'surname': updated.surname,
        'full_name': _full_name(updated), 'email': updated.email, 'location': updated.location,
        'is_platform_admin': bool(getattr(updated, 'is_platform_admin', False)),
    }}), 200


@admin_only
def delete_user(target_id, user_id=None):
    """Remove an account: credentials, sessions, profile, value cards,
    notifications, follows and memberships. What the person did stays (their
    openings are withdrawn; exchanges and receipts remain as history under
    their name)."""
    tid = uuid.UUID(str(target_id))
    if tid == uuid.UUID(str(user_id)):
        return jsonify({'message': "You can't delete your own account from here"}), 400
    row = session.execute("SELECT user_id, email, is_platform_admin FROM users WHERE user_id = %s", [tid]).one()
    if not row:
        return jsonify({'message': 'User not found'}), 404
    if getattr(row, 'is_platform_admin', False):
        return jsonify({'message': 'Revoke their administrator flag first'}), 400

    # Memberships (participants / members lists + role maps) in every entity.
    for kind, k in KINDS.items():
        for entity in k['model'].get_all():
            if tid in _members(entity, k) or tid in _roles(entity, k):
                _remove_member(entity, k, tid)
    # Their current openings are withdrawn (acceptances cleared with them).
    for s in Service.get_all():
        if s.is_current and s.provider_id == tid and s.status not in ('Cancelled', 'Completed'):
            Service.cancel(s.service_id)
            for a in Service.acceptances(s.service_id, status='pending'):
                Service.remove_acceptance(s.service_id, uuid.UUID(a['accepter_id']))
    # Follows in both directions (followee side needs a scan - the table is small).
    session.execute("DELETE FROM follows WHERE follower_id = %s", [tid])
    for r in session.execute("SELECT follower_id, followee_id FROM follows"):
        if r.followee_id == tid:
            session.execute("DELETE FROM follows WHERE follower_id = %s AND followee_id = %s", [r.follower_id, tid])
    for r in session.execute("SELECT session_id FROM sessions WHERE user_id = %s", [tid]):
        session.execute("DELETE FROM sessions WHERE session_id = %s", [r.session_id])
    session.execute("DELETE FROM value_cards WHERE user_id = %s", [tid])
    session.execute("DELETE FROM notifications WHERE user_id = %s", [tid])
    session.execute("DELETE FROM user_credentials WHERE user_id = %s", [tid])
    session.execute("DELETE FROM users WHERE user_id = %s", [tid])
    forget_admin_flag(tid)
    invalidate_index()
    logger.info(f"Admin {user_id} deleted user {tid}")
    return jsonify({'message': 'User deleted'}), 200


# ── Spheres / alliances / projects ───────────────────────────────────────────
def _entity_summary(kind, entity, k, cards):
    d = entity.to_dict(include_image=False)
    d['kind'] = kind
    d['id'] = str(getattr(entity, k['id_col']))
    members = _members(entity, k)
    d['member_count'] = len(members)
    d['pending_count'] = sum(1 for r in _roles(entity, k).values() if r == 'pending')
    d['card_count'] = len(cards.get(getattr(entity, k['id_col']), []))
    d.pop('members', None)
    d.pop('participants', None)
    d.pop('meaning_graph', None)
    return d


@admin_only
def list_entities(kind, user_id=None):
    k = KINDS[kind]
    entities = k['model'].get_all()
    cards = ValueCard.get_for_users([getattr(e, k['id_col']) for e in entities])
    out = [_entity_summary(kind, e, k, cards) for e in entities]
    if kind == 'sphere':
        alliance_counts, project_counts = {}, {}
        for a in Alliance.get_all():
            alliance_counts[a.sphere_id] = alliance_counts.get(a.sphere_id, 0) + 1
        for p in Project.get_all():
            project_counts[p.sphere_id] = project_counts.get(p.sphere_id, 0) + 1
        for d in out:
            sid = uuid.UUID(d['id'])
            d['alliance_count'] = alliance_counts.get(sid, 0)
            d['project_count'] = project_counts.get(sid, 0)
    out.sort(key=lambda d: (d.get('name') or '').lower())
    return jsonify({'items': out}), 200


def _cancel_openings(predicate):
    for s in Service.get_all():
        if s.is_current and s.status not in ('Cancelled', 'Completed') and predicate(s):
            Service.cancel(s.service_id)
            for a in Service.acceptances(s.service_id, status='pending'):
                Service.remove_acceptance(s.service_id, uuid.UUID(a['accepter_id']))


@admin_only
def delete_entity(kind, entity_id, user_id=None):
    k = KINDS[kind]
    eid = uuid.UUID(str(entity_id))
    entity = k['model'].get_by_id(eid)
    if not entity:
        return jsonify({'message': f'{kind.capitalize()} not found'}), 404

    if kind == 'sphere':
        inside = [a.name for a in Alliance.get_all() if a.sphere_id == eid] + \
                 [p.name for p in Project.get_all() if p.sphere_id == eid]
        if inside:
            return jsonify({'message': 'Delete or move its alliances and projects first: ' + ', '.join(inside[:5])
                            + ('…' if len(inside) > 5 else '')}), 409
        _cancel_openings(lambda s: s.provider_id == eid or s.sphere_id == eid)
    elif kind == 'alliance':
        owned = [p.name for p in Project.get_all() if getattr(p, 'owner_alliance', None) == entity.name]
        if owned:
            return jsonify({'message': 'This alliance still runs projects: ' + ', '.join(owned[:5])}), 409
        _cancel_openings(lambda s: s.provider_id == eid)
        if entity.sphere_id:
            session.execute("UPDATE spheres SET alliances = alliances - %s WHERE sphere_id = %s",
                            [[entity.name], entity.sphere_id])
    else:  # project
        _cancel_openings(lambda s: s.provider_id == eid or (s.project_name and s.project_name == entity.name))
        if entity.sphere_id:
            session.execute("UPDATE spheres SET projects = projects - %s WHERE sphere_id = %s",
                            [[entity.name], entity.sphere_id])

    session.execute("DELETE FROM value_cards WHERE user_id = %s", [eid])
    session.execute(f"DELETE FROM {k['table']} WHERE {k['id_col']} = %s", [eid])
    invalidate_index()
    logger.info(f"Admin {user_id} deleted {kind} {eid} ({entity.name})")
    return jsonify({'message': f'{kind.capitalize()} deleted'}), 200


# ── Openings ─────────────────────────────────────────────────────────────────
@admin_only
def list_openings(user_id=None):
    out = []
    for s in Service.get_all():
        if not s.is_current:
            continue
        d = s.to_dict(include_image=False)
        accs = Service.acceptances(s.service_id)
        d['pending_count'] = sum(1 for a in accs if a['status'] == 'pending')
        d['confirmed_count'] = sum(1 for a in accs if a['status'] == 'confirmed')
        d['is_open'] = s.status not in ('Cancelled', 'Completed') and not (s.cadence != 'perpetual' and s.status == 'In Progress')
        out.append(d)
    out.sort(key=lambda d: d.get('created_at') or '', reverse=True)
    return jsonify({'items': out}), 200


@admin_only
def delete_opening(service_id, user_id=None):
    sid = uuid.UUID(str(service_id))
    s = Service.get_by_id(sid)
    if not s:
        return jsonify({'message': 'Opening not found'}), 404
    if Service.has_related_exchange(sid):
        return jsonify({'message': 'An exchange was created from this opening - cancel it instead of deleting'}), 409
    session.execute("DELETE FROM opening_acceptances WHERE service_id = %s", [sid])
    session.execute("DELETE FROM opening_likes WHERE service_id = %s", [sid])
    session.execute("DELETE FROM services WHERE service_id = %s", [sid])
    invalidate_index()
    logger.info(f"Admin {user_id} deleted opening {sid} ({s.title})")
    return jsonify({'message': 'Opening deleted'}), 200


def register(app_):
    app_.add_url_rule('/api/admin/overview', view_func=overview, methods=['GET', 'OPTIONS'])
    app_.add_url_rule('/api/admin/users', view_func=list_users, methods=['GET', 'OPTIONS'])
    app_.add_url_rule('/api/admin/users/<target_id>', view_func=patch_user, methods=['PATCH', 'OPTIONS'])
    app_.add_url_rule('/api/admin/users/<target_id>', endpoint='admin_delete_user', view_func=delete_user, methods=['DELETE'])
    for kind, k in KINDS.items():
        app_.add_url_rule(f"/api/admin/{k['table']}", endpoint=f'admin_list_{kind}', view_func=list_entities,
                          defaults={'kind': kind}, methods=['GET', 'OPTIONS'])
        app_.add_url_rule(f"/api/admin/{k['table']}/<entity_id>", endpoint=f'admin_delete_{kind}', view_func=delete_entity,
                          defaults={'kind': kind}, methods=['DELETE', 'OPTIONS'])
    app_.add_url_rule('/api/admin/openings', view_func=list_openings, methods=['GET', 'OPTIONS'])
    app_.add_url_rule('/api/admin/openings/<service_id>', view_func=delete_opening, methods=['DELETE', 'OPTIONS'])
