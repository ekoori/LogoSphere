"""A sphere, alliance or project by its id alone, as events, announcements and
invitations need one: the same few facts whichever it is."""
from collections import namedtuple

from app.db import session
from app.models.alliance import Alliance
from app.models.project import Project
from app.models.spheres import Sphere
from app.utils.access import as_uuid

# sphere_id: the sphere it is inside; for a sphere, itself.
Group = namedtuple('Group', 'id kind name sphere_id members join_policy closed')
ROLES = {'sphere': ('spheres', 'sphere_id', 'member_roles'), 'alliance': ('alliances', 'alliance_id', 'member_roles'),
         'project': ('projects', 'project_id', 'participant_roles')}


def find(group_id):
    gid = as_uuid(group_id)
    if not gid:
        return None
    for table, column, members in (('spheres', 'sphere_id', 'participants'), ('alliances', 'alliance_id', 'members'),
                                   ('projects', 'project_id', 'participants')):
        extra = {'spheres': '', 'alliances': ', sphere_id', 'projects': ', sphere_id, phase'}[table]
        row = session.execute(f'SELECT name, join_policy, {members} AS people{extra} FROM {table} WHERE {column} = %s',
                              [gid]).one()
        if row:
            kind = table[:-1]
            return Group(gid, kind, row.name, gid if kind == 'sphere' else row.sphere_id, set(row.people or ()),
                         row.join_policy or 'open', kind == 'project' and row.phase == 'closed')
    return None


def link(group, tab=None):
    return f'/{group.kind}?id={group.id}' + (f'&tab={tab}' if tab else '')


def summary(group):
    return {'id': str(group.id), 'kind': group.kind, 'name': group.name} if group else None


def add_member(group, user_id, name):
    uid = as_uuid(user_id)
    table, column, roles = ROLES[group.kind]
    row = session.execute(f'SELECT {roles} AS roles FROM {table} WHERE {column} = %s', [group.id]).one()
    if not row:
        return
    if (row.roles or {}).get(uid) == 'pending':
        session.execute(f'UPDATE {table} SET {roles} = {roles} - %s WHERE {column} = %s', [{uid}, group.id])
    if group.kind == 'sphere':
        Sphere.join(group.id, uid)
    elif group.kind == 'alliance':
        Alliance.join(group.id, uid, name)
    else:
        Project.join(group.id, uid, name)
