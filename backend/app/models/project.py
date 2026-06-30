# File: ./backend/app/models/project.py
# Description: Project model. Projects are mission-driven collaborations within a Sphere.
# Class: Project — create() and get_all() backed by the logosphere.projects table.

from cassandra.cluster import Cluster
import uuid
import logging
import os
from datetime import datetime

# Host(s) configurable via CASSANDRA_HOST (comma-separated), defaults to localhost.
CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(CASSANDRA_HOSTS)
cassandra_session = cluster.connect('logosphere')


class Project:
    def __init__(self, project_id, name, description, owner, owner_alliance, status,
                 sphere_id, sphere_name, participants, participant_names, values,
                 participant_roles=None):
        self.project_id = project_id
        self.name = name
        self.description = description
        self.owner = owner
        self.owner_alliance = owner_alliance
        self.status = status
        self.sphere_id = sphere_id
        self.sphere_name = sphere_name
        self.participants = participants
        self.participant_names = participant_names
        self.values = values
        self.participant_roles = participant_roles or {}

    def to_dict(self):
        members_with_roles = [
            {
                'id': str(pid),
                'name': (self.participant_names[i] if self.participant_names and i < len(self.participant_names) else 'Member'),
                'role': self.participant_roles.get(pid, 'contributor') if self.participant_roles else 'contributor',
            }
            for i, pid in enumerate(self.participants or [])
        ]
        return {
            'project_id': str(self.project_id),
            'id': str(self.project_id),
            'name': self.name,
            'description': self.description,
            'owner': self.owner,
            'owner_alliance': self.owner_alliance,
            'status': self.status,
            'sphere_id': str(self.sphere_id) if self.sphere_id else None,
            'sphere_name': self.sphere_name,
            'participants': self.participant_names or [],
            'members': members_with_roles,
            'values': self.values or [],
        }

    @classmethod
    def create(cls, data, owner_id):
        project_id = uuid.uuid4()
        name = data['name']
        description = data.get('description', '')
        owner = data.get('owner') or str(owner_id)
        owner_alliance = data.get('owner_alliance', '')
        status = data.get('status', 'Active')
        sphere_id = data.get('sphere_id')
        if isinstance(sphere_id, str) and sphere_id:
            sphere_id = uuid.UUID(sphere_id)
        else:
            sphere_id = None
        sphere_name = data.get('sphere_name')
        participants = [owner_id]
        participant_names = data.get('participant_names', [])
        values = data.get('values', [])

        logging.info(f'Creating project with project_id: {project_id}')
        query = """
        INSERT INTO projects (project_id, name, description, owner, owner_alliance, status,
                              sphere_id, sphere_name, created_at, participants, participant_names, values)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cassandra_session.execute(query, (
            project_id, name, description, owner, owner_alliance, status,
            sphere_id, sphere_name, datetime.utcnow(), participants, participant_names, values
        ))
        return cls(project_id, name, description, owner, owner_alliance, status,
                   sphere_id, sphere_name, participants, participant_names, values)

    @classmethod
    def get_all(cls):
        rows = cassandra_session.execute("SELECT * FROM projects")
        projects = []
        for r in rows:
            projects.append(cls(
                r.project_id, r.name, getattr(r, 'description', None), r.owner,
                getattr(r, 'owner_alliance', None), getattr(r, 'status', None),
                getattr(r, 'sphere_id', None), getattr(r, 'sphere_name', None),
                getattr(r, 'participants', None), getattr(r, 'participant_names', None),
                getattr(r, 'values', None),
                getattr(r, 'participant_roles', None),
            ))
        return projects

    @classmethod
    def join(cls, project_id, user_uuid, user_name):
        """Add user as a contributor. Returns already_member=True if already present."""
        result = cassandra_session.execute(
            "SELECT participants, participant_roles FROM projects WHERE project_id = %s",
            [project_id]
        ).one()
        if result and result.participants and user_uuid in result.participants:
            return True
        cassandra_session.execute(
            "UPDATE projects SET participants = participants + %s, participant_names = participant_names + %s, "
            "participant_roles = participant_roles + %s WHERE project_id = %s",
            [[user_uuid], [user_name], {user_uuid: 'contributor'}, project_id]
        )
        return False
