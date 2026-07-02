# Shared entity-permission helpers — used wherever an action can be taken
# "as" a sphere, alliance, or project (value cards, entity-authored openings).
import uuid
from app.models.value_card import cassandra_session


def can_manage_entity(entity_id, user_id):
    """True if `user_id` is allowed to act on behalf of the sphere, alliance,
    or project identified by `entity_id`: sphere participant/admin, alliance
    admin/steward, or project manager/owner."""
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
        roles = row.participant_roles or {}
        return roles.get(uid) == 'manager' or str(row.owner) == str(uid)

    return False


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
