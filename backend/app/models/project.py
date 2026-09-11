# File: ./backend/app/models/project.py
# Description: Project model. Projects are mission-driven collaborations within a Sphere.
# Class: Project — create() and get_all() backed by the logosphere.projects table.

import uuid
import logging
import os
import base64
from datetime import datetime

from app.db import session as cassandra_session
from app.utils.names import resolve_user_names, dedupe


class Project:
    def __init__(self, project_id, name, description, owner, owner_alliance, status,
                 sphere_id, sphere_name, participants, participant_names, values,
                 participant_roles=None, image=None, join_policy=None, has_image=None,
                 decision_policy=None, phase=None):
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
        self.join_policy = join_policy or 'open'
        self.decision_policy = decision_policy or 'majority'
        # 'ongoing' | 'closed' - a closed (archived) project takes no new openings.
        self.phase = phase or 'ongoing'
        self._has_image = has_image

    def to_dict(self, include_image=True):
        # Names come from `users` at read time (the stored participant_names
        # list was positionally aligned to participants and drifted on rename).
        pids = dedupe(self.participants or [])
        names = resolve_user_names(pids)
        members_with_roles = [
            {
                'id': str(pid),
                'name': names.get(pid, 'Member'),
                'role': self.participant_roles.get(pid, 'contributor') if self.participant_roles else 'contributor',
            }
            for pid in pids
        ]
        # The project's manager is its creator/owner — expose their id + name so
        # a card can show "by <person>" (and link to them) when the project
        # isn't run on behalf of an alliance.
        mgr = next((m for m in members_with_roles if m['role'] == 'manager'), None) \
            or (members_with_roles[0] if members_with_roles else None)
        return {
            'project_id': str(self.project_id),
            'id': str(self.project_id),
            'name': self.name,
            'description': self.description,
            'owner': self.owner,
            'owner_id': mgr['id'] if mgr else None,
            'owner_name': mgr['name'] if mgr else (self.owner or None),
            'owner_alliance': self.owner_alliance,
            'status': self.status,
            'sphere_id': str(self.sphere_id) if self.sphere_id else None,
            'sphere_name': self.sphere_name,
            'participants': [m['name'] for m in members_with_roles],
            'members': members_with_roles,
            'values': self.values or [],
            'join_policy': self.join_policy,
            'decision_policy': self.decision_policy,
            'phase': self.phase,
            'has_image': bool(self.image) if self._has_image is None else bool(self._has_image),
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
        if image:
            cassandra_session.execute("UPDATE projects SET has_image = true WHERE project_id = %s", [project_id])
        return cls(project_id, name, description, owner, owner_alliance, status,
                   sphere_id, sphere_name, participants, participant_names, values,
                   participant_roles=participant_roles, image=image, has_image=bool(image))

    _COLS = ("project_id, name, description, owner, owner_alliance, status, sphere_id, sphere_name, "
             "participants, participant_names, values, participant_roles, join_policy, has_image, decision_policy, phase")

    @classmethod
    def get_all(cls):
        """All projects without their banner blobs (see has_image)."""
        rows = cassandra_session.execute(f"SELECT {cls._COLS} FROM projects")
        return [cls._from_row(r) for r in rows]

    @classmethod
    def list_for_sphere(cls, sphere_id):
        """[{id, name}] of the projects inside a sphere."""
        rows = cassandra_session.execute("SELECT project_id, name, sphere_id FROM projects")
        return [{'id': str(r.project_id), 'name': r.name} for r in rows if r.sphere_id == sphere_id]

    @classmethod
    def get_by_id(cls, project_id):
        """One project by id (point read), or None."""
        try:
            pid = project_id if isinstance(project_id, uuid.UUID) else uuid.UUID(str(project_id))
        except (ValueError, TypeError):
            return None
        r = cassandra_session.execute(f"SELECT {cls._COLS} FROM projects WHERE project_id = %s", [pid]).one()
        return cls._from_row(r) if r else None

    @classmethod
    def _from_row(cls, r):
        return cls(
            r.project_id, r.name, getattr(r, 'description', None), r.owner,
            getattr(r, 'owner_alliance', None), getattr(r, 'status', None),
            getattr(r, 'sphere_id', None), getattr(r, 'sphere_name', None),
            getattr(r, 'participants', None), getattr(r, 'participant_names', None),
            getattr(r, 'values', None),
            getattr(r, 'participant_roles', None),
            getattr(r, 'image', None),
            join_policy=getattr(r, 'join_policy', None),
            has_image=getattr(r, 'has_image', None),
            decision_policy=getattr(r, 'decision_policy', None),
            phase=getattr(r, 'phase', None),
        )

    @classmethod
    def set_image(cls, project_id, image_bytes):
        cassandra_session.execute(
            "UPDATE projects SET image = %s, has_image = true WHERE project_id = %s",
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
