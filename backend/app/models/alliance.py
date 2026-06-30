# File: ./backend/app/models/alliance.py
# Description: Alliance model. Alliances are federations/partnerships between
# spheres — groups of users, usually nested in a Sphere.
# Class: Alliance — create() and get_all() backed by the trustsphere.alliances table.

from cassandra.cluster import Cluster
import uuid
import logging
import os
from datetime import datetime
import base64

# Host(s) configurable via CASSANDRA_HOST (comma-separated), defaults to localhost.
CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(CASSANDRA_HOSTS)
cassandra_session = cluster.connect('trustsphere')


class Alliance:
    def __init__(self, alliance_id, name, description, admin1, sphere_id, sphere_name,
                 members, member_names, projects, values, value_graph, image, member_roles=None):
        self.alliance_id = alliance_id
        self.name = name
        self.description = description
        self.admin1 = admin1
        self.sphere_id = sphere_id
        self.sphere_name = sphere_name
        self.members = members
        self.member_names = member_names
        self.projects = projects
        self.values = values
        self.value_graph = value_graph
        self.image = image
        self.member_roles = member_roles or {}

    def to_dict(self):
        members_with_roles = [
            {
                'id': str(mid),
                'name': (self.member_names[i] if self.member_names and i < len(self.member_names) else 'Member'),
                'role': self.member_roles.get(mid, 'member') if self.member_roles else 'member',
            }
            for i, mid in enumerate(self.members or [])
        ]
        return {
            'alliance_id': str(self.alliance_id),
            'id': str(self.alliance_id),
            'name': self.name,
            'description': self.description,
            'admin1': str(self.admin1) if self.admin1 else None,
            'sphere_id': str(self.sphere_id) if self.sphere_id else None,
            'sphere_name': self.sphere_name,
            'participants': self.member_names or [],
            'members': members_with_roles,
            'projects': self.projects or [],
            'values': self.values or [],
            'value_graph': self.value_graph,
            'image': base64.b64encode(self.image).decode('utf-8') if self.image else None,
        }

    @classmethod
    def create(cls, data, admin1):
        alliance_id = uuid.uuid4()
        name = data['name']
        description = data.get('description', '')
        sphere_id = data.get('sphere_id')
        if isinstance(sphere_id, str) and sphere_id:
            sphere_id = uuid.UUID(sphere_id)
        else:
            sphere_id = None
        sphere_name = data.get('sphere_name')
        members = [admin1]
        member_names = data.get('member_names', [])
        projects = data.get('projects', [])
        values = data.get('values', [])
        value_graph = data.get('value_graph', '')
        image = data.get('image')

        logging.info(f'Creating alliance with alliance_id: {alliance_id}')
        query = """
        INSERT INTO alliances (alliance_id, name, description, admin1, sphere_id, sphere_name,
                            created_at, members, member_names, projects, values, value_graph, image)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cassandra_session.execute(query, (
            alliance_id, name, description, admin1, sphere_id, sphere_name,
            datetime.utcnow(), members, member_names, projects, values, value_graph, image
        ))
        return cls(alliance_id, name, description, admin1, sphere_id, sphere_name,
                   members, member_names, projects, values, value_graph, image)

    @classmethod
    def get_all(cls):
        rows = cassandra_session.execute("SELECT * FROM alliances")
        alliances = []
        for r in rows:
            alliances.append(cls(
                r.alliance_id, r.name, r.description, r.admin1, r.sphere_id,
                getattr(r, 'sphere_name', None), r.members, getattr(r, 'member_names', None),
                r.projects, r.values, r.value_graph, r.image,
                getattr(r, 'member_roles', None),
            ))
        return alliances

    @classmethod
    def join(cls, alliance_id, user_uuid, user_name):
        """Add user as a member. Returns already_member=True if they're already in."""
        result = cassandra_session.execute(
            "SELECT members, member_roles FROM alliances WHERE alliance_id = %s",
            [alliance_id]
        ).one()
        if result and result.members and user_uuid in result.members:
            return True
        cassandra_session.execute(
            "UPDATE alliances SET members = members + %s, member_names = member_names + %s, "
            "member_roles = member_roles + %s WHERE alliance_id = %s",
            [[user_uuid], [user_name], {user_uuid: 'member'}, alliance_id]
        )
        return False
