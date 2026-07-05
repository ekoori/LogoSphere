# File: ./backend/app/models/project.py
# Description: Project model. Projects are mission-driven collaborations within a Sphere.
# Class: Project — create() and get_all() backed by the logosphere.projects table.

from cassandra.cluster import Cluster
import uuid
import logging
import os
import base64
from datetime import datetime

# Host(s) configurable via CASSANDRA_HOST (comma-separated), defaults to localhost.
CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(CASSANDRA_HOSTS)
cassandra_session = cluster.connect('logosphere')


class Project:
    def __init__(self, project_id, name, description, owner, owner_alliance, status,
                 sphere_id, sphere_name, participants, participant_names, values,
                 participant_roles=None, image=None):
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
        self.image = image

    def to_dict(self, include_image=True):
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
            'has_image': bool(self.image),
            'image': (base64.b64encode(self.image).decode('utf-8') if self.image else None) if include_image else None,
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
        image = data.get('image')
        # The founder manages the project from the outset.
        participant_roles = {owner_id: 'manager'}

        logging.info(f'Creating project with project_id: {project_id}')
        query = """
        INSERT INTO projects (project_id, name, description, owner, owner_alliance, status,
                              sphere_id, sphere_name, created_at, participants, participant_names,
                              participant_roles, values, image)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cassandra_session.execute(query, (
            project_id, name, description, owner, owner_alliance, status,
            sphere_id, sphere_name, datetime.utcnow(), participants, participant_names,
            participant_roles, values, image
        ))
        return cls(project_id, name, description, owner, owner_alliance, status,
                   sphere_id, sphere_name, participants, participant_names, values,
                   participant_roles=participant_roles, image=image)

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
                getattr(r, 'image', None),
            ))
        return projects

    @classmethod
    def set_image(cls, project_id, image_bytes):
        cassandra_session.execute(
            "UPDATE projects SET image = %s WHERE project_id = %s",
            [image_bytes, project_id]
        )

    @classmethod
    def get_image(cls, project_id):
        """Just the image bytes for one project (served via a dedicated GET so
        the projects list needn't carry every banner blob)."""
        row = cassandra_session.execute(
            "SELECT image FROM projects WHERE project_id = %s", [project_id]
        ).one()
        return row.image if row and row.image else None

    @classmethod
    def set_role(cls, project_id, target_uuid, role):
        """Set a participant's role. Roles: 'manager', 'steward' (acts on behalf
        of the manager), 'contributor'."""
        cassandra_session.execute(
            "UPDATE projects SET participant_roles = participant_roles + %s WHERE project_id = %s",
            [{target_uuid: role}, project_id]
        )

    @classmethod
    def manager_ids(cls, project_id):
        """Set of user ids allowed to manage the project (owner + role=manager)."""
        row = cassandra_session.execute(
            "SELECT owner, participant_roles FROM projects WHERE project_id = %s", [project_id]
        ).one()
        if not row:
            return set()
        mgrs = set()
        if row.owner:
            try:
                mgrs.add(uuid.UUID(str(row.owner)))
            except (ValueError, TypeError):
                pass
        for uid, r in (getattr(row, 'participant_roles', None) or {}).items():
            if r == 'manager':
                mgrs.add(uid)
        return mgrs

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
