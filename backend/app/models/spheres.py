import uuid
import logging
import os
from datetime import datetime
import base64

from app.db import session as cassandra_session

from app.utils.names import resolve_user_names as _resolve_user_names, dedupe as _dedupe


class Sphere:
    def __init__(self, sphere_id, name, description, meaning_graph, location, image, admin1, participants, alliances, projects, values, member_roles=None, is_sandbox=False, is_public=False, join_policy=None, has_image=None,
                 decision_policy=None):
        self.sphere_id = sphere_id
        self.name = name
        self.description = description
        self.meaning_graph = meaning_graph
        self.location = location
        self.image = image
        self.admin1 = admin1
        self.participants = participants
        self.alliances = alliances
        self.projects = projects
        self.values = values
        self.member_roles = member_roles or {}
        # Governance flags (Phase 5): a sandbox sphere auto-enrolls every new
        # user; a public sphere is viewable by logged-out visitors.
        self.is_sandbox = bool(is_sandbox)
        self.is_public = bool(is_public)
        self.join_policy = join_policy or 'open'
        # How proposals pass in this sphere's liquid-democracy votes.
        self.decision_policy = decision_policy or 'majority'
        # has_image is a stored flag so list endpoints can skip the blob column
        # entirely (Cassandra can't test blob presence without reading it).
        self._has_image = has_image

    def members_list(self):
        """[{id, name, role}] for the sphere — participants are stored as bare
        UUIDs, so names are resolved from the users table. admin1 is 'admin'."""
        pids = _dedupe(self.participants or [])
        names = _resolve_user_names(pids)
        roles = self.member_roles or {}
        out = []
        for pid in pids:
            role = roles.get(pid) or ('admin' if self.admin1 and pid == self.admin1 else 'member')
            out.append({'id': str(pid), 'name': names.get(pid, 'Member'), 'role': role})
        return out

    def to_dict(self, include_members=False, include_image=True):
        d = {
            'sphere_id': str(self.sphere_id),
            'name': self.name,
            'description': self.description,
            'meaning_graph': self.meaning_graph,
            'location': self.location,
            'has_image': bool(self.image) if self._has_image is None else bool(self._has_image),
            'image': (base64.b64encode(self.image).decode('utf-8') if self.image else None) if include_image else None,
            'admin1': str(self.admin1),
            'participants': self.participants,
            'alliances': self.alliances,
            'projects': self.projects,
            'values': self.values,
            'is_sandbox': self.is_sandbox,
            'is_public': self.is_public,
            'join_policy': self.join_policy,
            'decision_policy': self.decision_policy,
        }
        if include_members:
            d['members'] = self.members_list()
        return d

    @classmethod
    def create(cls, data, admin1):
        sphere_id = uuid.uuid4()
        name = data['name']
        description = data['description']
        meaning_graph = data['meaning_graph']
        location = data['location']
        image = data['image']
        participants = [admin1]
        alliances = data.get('alliances', [])
        projects = data.get('projects', [])
        values = data.get('values', [])
        logging.info(f'Creating sphere with sphere_id: {sphere_id}')

        query = """
        INSERT INTO spheres (sphere_id, name, description, meaning_graph, location, image, admin1, participants, alliances, projects, values, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cassandra_session.execute(query, (sphere_id, name, description, meaning_graph, location, image, admin1, participants, alliances, projects, values, datetime.utcnow()))
        if image:
            cassandra_session.execute("UPDATE spheres SET has_image = true WHERE sphere_id = %s", [sphere_id])

        return cls(sphere_id, name, description, meaning_graph, location, image, admin1, participants, alliances, projects, values)

    @classmethod
    def set_image(cls, sphere_id, image_bytes):
        cassandra_session.execute(
            "UPDATE spheres SET image = %s, has_image = true WHERE sphere_id = %s",
            [image_bytes, sphere_id]
        )

    @classmethod
    def get_image(cls, sphere_id):
        """Just the image bytes for one sphere (served via a dedicated GET so
        the spheres list needn't carry every banner blob)."""
        row = cassandra_session.execute(
            "SELECT image FROM spheres WHERE sphere_id = %s", [sphere_id]
        ).one()
        return row.image if row and row.image else None

    @classmethod
    def set_role(cls, sphere_id, target_uuid, role):
        """Set a member's role in the sphere (e.g. promote to 'admin')."""
        cassandra_session.execute(
            "UPDATE spheres SET member_roles = member_roles + %s WHERE sphere_id = %s",
            [{target_uuid: role}, sphere_id]
        )

    @classmethod
    def admin_ids(cls, sphere_id):
        """Set of user ids allowed to administer the sphere (admin1 + role=admin)."""
        row = cassandra_session.execute(
            "SELECT admin1, member_roles FROM spheres WHERE sphere_id = %s", [sphere_id]
        ).one()
        if not row:
            return set()
        admins = {row.admin1} if row.admin1 else set()
        for uid, r in (getattr(row, 'member_roles', None) or {}).items():
            if r == 'admin':
                admins.add(uid)
        return admins

    @classmethod
    def join(cls, sphere_id, user_uuid):
        """Add user as a participant. Returns already_member=True if already in."""
        result = cassandra_session.execute(
            "SELECT participants FROM spheres WHERE sphere_id = %s", [sphere_id]
        ).one()
        if result and result.participants and user_uuid in result.participants:
            return True
        cassandra_session.execute(
            "UPDATE spheres SET participants = participants + %s WHERE sphere_id = %s",
            [[user_uuid], sphere_id]
        )
        return False

    @classmethod
    def set_governance(cls, sphere_id, is_sandbox=None, is_public=None):
        """Update a sphere's governance flags. Only the flags passed (non-None)
        are written, so callers can update sandbox/public independently."""
        sets, params = [], []
        if is_sandbox is not None:
            sets.append("is_sandbox = %s")
            params.append(bool(is_sandbox))
        if is_public is not None:
            sets.append("is_public = %s")
            params.append(bool(is_public))
        if not sets:
            return
        params.append(sphere_id)
        cassandra_session.execute(
            f"UPDATE spheres SET {', '.join(sets)} WHERE sphere_id = %s", params)

    @classmethod
    def sandbox_ids(cls):
        """List of (sphere_id) for spheres flagged as sandboxes — every new user
        is auto-enrolled into these on registration."""
        rows = cassandra_session.execute("SELECT sphere_id, is_sandbox FROM spheres")
        return [r.sphere_id for r in rows if getattr(r, 'is_sandbox', False)]

    @classmethod
    def get_by_id(cls, sphere_id):
        """Full sphere by id, including governance flags. Returns None if absent."""
        try:
            sid = sphere_id if isinstance(sphere_id, uuid.UUID) else uuid.UUID(str(sphere_id))
        except (ValueError, TypeError):
            return None
        row = cassandra_session.execute(
            f"SELECT {cls._COLS} FROM spheres WHERE sphere_id = %s", [sid]).one()
        return cls._from_row(row) if row else None

    # Every column except the banner blob - lists and detail never need it.
    _COLS = ("sphere_id, name, description, meaning_graph, location, admin1, participants, "
             "alliances, projects, values, member_roles, is_sandbox, is_public, join_policy, has_image, decision_policy")

    @classmethod
    def _from_row(cls, row):
        return cls(
            sphere_id=row.sphere_id, name=row.name, description=row.description,
            meaning_graph=row.meaning_graph, location=row.location, image=None,
            admin1=row.admin1, participants=row.participants, alliances=row.alliances,
            projects=row.projects, values=row.values,
            member_roles=getattr(row, 'member_roles', None),
            is_sandbox=getattr(row, 'is_sandbox', False),
            is_public=getattr(row, 'is_public', False),
            join_policy=getattr(row, 'join_policy', None),
            has_image=getattr(row, 'has_image', None),
            decision_policy=getattr(row, 'decision_policy', None))

    @classmethod
    def get_all(cls):
        """All spheres without their banner blobs (see has_image)."""
        seen, out = set(), []
        for row in cassandra_session.execute(f"SELECT {cls._COLS} FROM spheres"):
            if row.sphere_id in seen:
                continue
            seen.add(row.sphere_id)
            out.append(cls._from_row(row))
        return out

    @classmethod
    def member_sphere_ids(cls, user_id):
        """Set of sphere_ids the given user participates in. Used to gate
        sphere-scoped openings/alliances/projects to members only."""
        if not user_id:
            return set()
        try:
            uid = user_id if isinstance(user_id, uuid.UUID) else uuid.UUID(str(user_id))
        except (ValueError, TypeError):
            return set()
        rows = cassandra_session.execute("SELECT sphere_id, participants FROM spheres")
        return {r.sphere_id for r in rows if r.participants and uid in r.participants}
