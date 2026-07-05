# Shared entity-permission helpers — used wherever an action can be taken
# "as" a sphere, alliance, or project (value cards, entity-authored openings).
import time
import uuid
from app.models.value_card import cassandra_session

# ── Platform administrators ───────────────────────────────────────────────────
# Identified by email (not user_id) so a named admin becomes one the moment they
# register with that address — no account needs to pre-exist, no migration. A
# platform admin can see all data and manage any sphere/entity.
PLATFORM_ADMIN_EMAILS = frozenset({
    'igor.krbavcic@gmail.com',
    'joe.rogan@example.com',
})

# Resolved admin user_ids are cached briefly to avoid an index lookup per request.
_admin_ids_cache = {'ids': set(), 'ts': 0.0}
_ADMIN_TTL = 60.0


def platform_admin_ids():
    """Set of user_ids belonging to a platform-admin email. Cached for _ADMIN_TTL
    seconds so a freshly-registered admin is recognised within a minute."""
    now = time.time()
    if now - _admin_ids_cache['ts'] < _ADMIN_TTL:
        return _admin_ids_cache['ids']
    ids = set()
    for email in PLATFORM_ADMIN_EMAILS:
        try:
            for r in cassandra_session.execute(
                    "SELECT user_id FROM user_credentials WHERE email = %s", [email]):
                ids.add(r.user_id)
        except Exception:
            pass
    _admin_ids_cache['ids'] = ids
    _admin_ids_cache['ts'] = now
    return ids


def is_platform_admin(user_id):
    """True if the given user is a platform administrator."""
    if not user_id:
        return False
    try:
        uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        return False
    return uid in platform_admin_ids()


def can_manage_entity(entity_id, user_id):
    """True if `user_id` is allowed to act on behalf of the sphere, alliance,
    or project identified by `entity_id`: sphere participant/admin, alliance
    admin/steward, or project manager/owner. Platform admins can manage anything."""
    if is_platform_admin(user_id):
        return True
    try:
        eid = uuid.UUID(str(entity_id))
        uid = uuid.UUID(str(user_id))
    except (ValueError, TypeError):
        return False

    row = cassandra_session.execute(
        "SELECT admin1, participants FROM spheres WHERE sphere_id = %s", [eid]
    ).one()
    if row:
        return row.admin1 == uid or (bool(row.participants) and uid in row.participants)

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
