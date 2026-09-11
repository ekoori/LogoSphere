# Shared entity-permission helpers — used wherever an action can be taken
# "as" a sphere, alliance, or project (value cards, entity-authored openings).
import time
import uuid
from app.db import session as cassandra_session

# ── Platform administrators ───────────────────────────────────────────────────
# A platform admin is a user whose `users.is_platform_admin` flag is set. The
# flag is granted out-of-band by an operator (backend/grant_platform_admin.py),
# never by anything a user can do themselves — registration doesn't verify
# email ownership, so keying admin status off an email address would let anyone
# who registered that address become an admin.
_admin_flag_cache = {}          # user_id -> (is_admin, ts)
_ADMIN_TTL = 60.0


def is_platform_admin(user_id):
    """True if the given user is a platform administrator (cached briefly)."""
    if not user_id:
        return False
    try:
        uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        return False
    now = time.time()
    hit = _admin_flag_cache.get(uid)
    if hit and now - hit[1] < _ADMIN_TTL:
        return hit[0]
    try:
        row = cassandra_session.execute(
            "SELECT is_platform_admin FROM users WHERE user_id = %s", [uid]).one()
        flag = bool(row and getattr(row, 'is_platform_admin', False))
    except Exception:
        flag = False
    _admin_flag_cache[uid] = (flag, now)
    return flag


def forget_admin_flag(user_id=None):
    """Drop the cached admin flag (all users when None) after a grant/revoke."""
    if user_id is None:
        _admin_flag_cache.clear()
    else:
        _admin_flag_cache.pop(uuid.UUID(str(user_id)), None)


def can_manage_entity(entity_id, user_id):
    """True if `user_id` is allowed to act on behalf of the sphere, alliance,
    or project identified by `entity_id`: sphere admin, alliance admin/steward,
    or project manager/steward/owner. Platform admins can manage anything."""
    if is_platform_admin(user_id):
        return True
    try:
        eid = uuid.UUID(str(entity_id))
        uid = uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        return False

    row = cassandra_session.execute(
        "SELECT admin1, member_roles FROM spheres WHERE sphere_id = %s", [eid]
    ).one()
    if row:
        # Only the sphere's admins manage it — being a participant is not enough
        # (any user can join an open sphere).
        if row.admin1 == uid:
            return True
        return (row.member_roles or {}).get(uid) == 'admin'

    row = cassandra_session.execute(
        "SELECT admin1, member_roles FROM alliances WHERE alliance_id = %s", [eid]
    ).one()
    if row:
        if row.admin1 == uid:
            return True
        roles = row.member_roles or {}
        return roles.get(uid) in ('admin', 'steward')

    row = cassandra_session.execute(
        "SELECT owner, participant_roles FROM projects WHERE project_id = %s", [eid]
    ).one()
    if row:
        # Stewards act on behalf of the project manager, so they can manage too.
        roles = row.participant_roles or {}
        return roles.get(uid) in ('manager', 'steward') or str(row.owner) == str(uid)

    return False


def entity_sphere_ids(entity_id):
    """The set of sphere ids (as str) an entity belongs to, for enforcing that
    an entity acting in an opening is within that opening's sphere. A sphere is
    'in' itself; an alliance or project is in its single `sphere_id`. Returns an
    empty set if the entity isn't found or has no sphere."""
    try:
        eid = uuid.UUID(str(entity_id))
    except (ValueError, TypeError):
        return set()

    row = cassandra_session.execute(
        "SELECT sphere_id FROM spheres WHERE sphere_id = %s", [eid]
    ).one()
    if row:
        return {str(eid)}

    row = cassandra_session.execute(
        "SELECT sphere_id FROM alliances WHERE alliance_id = %s", [eid]
    ).one()
    if row:
        return {str(row.sphere_id)} if row.sphere_id else set()

    row = cassandra_session.execute(
        "SELECT sphere_id FROM projects WHERE project_id = %s", [eid]
    ).one()
    if row:
        return {str(row.sphere_id)} if row.sphere_id else set()

    return set()


def get_entity_info(entity_id):
    """Return {'kind': 'sphere'|'alliance'|'project', 'name': str} for an
    entity id, or None if it doesn't identify a sphere/alliance/project."""
    try:
        eid = uuid.UUID(str(entity_id))
    except (ValueError, TypeError):
        return None

    row = cassandra_session.execute(
        "SELECT name FROM spheres WHERE sphere_id = %s", [eid]
    ).one()
    if row:
        return {'kind': 'sphere', 'name': row.name}

    row = cassandra_session.execute(
        "SELECT name FROM alliances WHERE alliance_id = %s", [eid]
    ).one()
    if row:
        return {'kind': 'alliance', 'name': row.name}

    row = cassandra_session.execute(
        "SELECT name FROM projects WHERE project_id = %s", [eid]
    ).one()
    if row:
        return {'kind': 'project', 'name': row.name}

    return None
