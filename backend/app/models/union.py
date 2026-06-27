# File: ./backend/app/models/union.py
# Description: Union model. Unions are groups of users, usually nested in a Sphere.
# Class: Union — create() and get_all() backed by the trustsphere.unions table.

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


class Union:
    def __init__(self, union_id, name, description, admin1, sphere_id, sphere_name,
                 members, member_names, projects, values, value_graph, image):
        self.union_id = union_id
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

    def to_dict(self):
        return {
            'union_id': str(self.union_id),
            'id': str(self.union_id),
            'name': self.name,
            'description': self.description,
            'admin1': str(self.admin1) if self.admin1 else None,
            'sphere_id': str(self.sphere_id) if self.sphere_id else None,
            'sphere_name': self.sphere_name,
            # `participants` mirrors what the frontend UnionCard expects (names);
            # `members` pairs each id with a name so members link to their profile.
            'participants': self.member_names or [],
            'members': [
                {'id': str(mid), 'name': (self.member_names[i] if self.member_names and i < len(self.member_names) else 'Member')}
                for i, mid in enumerate(self.members or [])
            ],
            'projects': self.projects or [],
            'values': self.values or [],
            'value_graph': self.value_graph,
            'image': base64.b64encode(self.image).decode('utf-8') if self.image else None,
        }

    @classmethod
    def create(cls, data, admin1):
        union_id = uuid.uuid4()
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

        logging.info(f'Creating union with union_id: {union_id}')
        query = """
        INSERT INTO unions (union_id, name, description, admin1, sphere_id, sphere_name,
                            created_at, members, member_names, projects, values, value_graph, image)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cassandra_session.execute(query, (
            union_id, name, description, admin1, sphere_id, sphere_name,
            datetime.utcnow(), members, member_names, projects, values, value_graph, image
        ))
        return cls(union_id, name, description, admin1, sphere_id, sphere_name,
                   members, member_names, projects, values, value_graph, image)

    @classmethod
    def get_all(cls):
        rows = cassandra_session.execute("SELECT * FROM unions")
        unions = []
        for r in rows:
            unions.append(cls(
                r.union_id, r.name, r.description, r.admin1, r.sphere_id,
                getattr(r, 'sphere_name', None), r.members, getattr(r, 'member_names', None),
                r.projects, r.values, r.value_graph, r.image
            ))
        return unions
