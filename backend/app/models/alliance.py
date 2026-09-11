# File: ./backend/app/models/alliance.py
# Description: Alliance model. Alliances are federations/partnerships between
# spheres — groups of users, usually nested in a Sphere.
# Class: Alliance — create() and get_all() backed by the logosphere.alliances table.

import uuid
import logging
import os
from datetime import datetime
import base64

from app.db import session as cassandra_session
from app.utils.names import resolve_user_names, dedupe


class Alliance:
    def __init__(self, alliance_id, name, description, admin1, sphere_id, sphere_name,
                 members, member_names, projects, values, meaning_graph, image, member_roles=None):
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
        self.meaning_graph = meaning_graph
        self.image = image
        self.member_roles = member_roles or {}

    def to_dict(self, include_image=True):
        def _role(mid):
            # An explicit role wins; otherwise the alliance admin (admin1) is the admin.
            if self.member_roles and self.member_roles.get(mid):
                return self.member_roles[mid]
            if self.admin1 and mid == self.admin1:
                return 'admin'
            return 'member'

        # Names come from `users` at read time (member_names was positionally
        # aligned to members and drifted on rename).
        mids = dedupe(self.members or [])
        names = resolve_user_names(mids)
        members_with_roles = [
            {'id': str(mid), 'name': names.get(mid, 'Member'), 'role': _role(mid)}
            for mid in mids
        ]
        return {
            'alliance_id': str(self.alliance_id),
            'id': str(self.alliance_id),
            'name': self.name,
            'description': self.description,
            'admin1': str(self.admin1) if self.admin1 else None,
            'sphere_id': str(self.sphere_id) if self.sphere_id else None,
            'sphere_name': self.sphere_name,
            'participants': [m['name'] for m in members_with_roles],
            'members': members_with_roles,
            'projects': self.projects or [],
            'values': self.values or [],
            'meaning_graph': self.meaning_graph,
            'has_image': bool(self.image),
            'image': (base64.b64encode(self.image).decode('utf-8') if self.image else None) if include_image else None,
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
        meaning_graph = data.get('meaning_graph', '')
        image = data.get('image')

        logging.info(f'Creating alliance with alliance_id: {alliance_id}')
        query = """
        INSERT INTO alliances (alliance_id, name, description, admin1, sphere_id, sphere_name,
                            created_at, members, member_names, projects, values, meaning_graph, image)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cassandra_session.execute(query, (
            alliance_id, name, description, admin1, sphere_id, sphere_name,
            datetime.utcnow(), members, member_names, projects, values, meaning_graph, image
        ))
        return cls(alliance_id, name, description, admin1, sphere_id, sphere_name,
                   members, member_names, projects, values, meaning_graph, image)

    @classmethod
    def get_all(cls):
        rows = cassandra_session.execute("SELECT * FROM alliances")
        return [cls._from_row(r) for r in rows]

    @classmethod
    def get_by_id(cls, alliance_id):
        """One alliance by id (point read), or None."""
        try:
            aid = alliance_id if isinstance(alliance_id, uuid.UUID) else uuid.UUID(str(alliance_id))
        except (ValueError, TypeError):
            return None
        r = cassandra_session.execute("SELECT * FROM alliances WHERE alliance_id = %s", [aid]).one()
        return cls._from_row(r) if r else None

    @classmethod
    def _from_row(cls, r):
        return cls(
            r.alliance_id, r.name, r.description, r.admin1, r.sphere_id,
            getattr(r, 'sphere_name', None), r.members, getattr(r, 'member_names', None),
            r.projects, r.values, r.meaning_graph, r.image,
            getattr(r, 'member_roles', None),
        )

    @classmethod
    def set_image(cls, alliance_id, image_bytes):
        cassandra_session.execute(
            "UPDATE alliances SET image = %s WHERE alliance_id = %s",
            [image_bytes, alliance_id]
        )

    @classmethod
    def get_image(cls, alliance_id):
        """Just the image bytes for one alliance (served via a dedicated GET so
        the alliances list needn't carry every banner blob)."""
        row = cassandra_session.execute(
            "SELECT image FROM alliances WHERE alliance_id = %s", [alliance_id]
        ).one()
        return row.image if row and row.image else None

    @classmethod
    def set_role(cls, alliance_id, target_uuid, role):
        """Set a member's role. Roles: 'admin' (Lead), 'steward' (Board member),
        'member'. Display names differ (see frontend) but values are kept stable."""
        cassandra_session.execute(
            "UPDATE alliances SET member_roles = member_roles + %s WHERE alliance_id = %s",
            [{target_uuid: role}, alliance_id]
        )

    @classmethod
    def lead_ids(cls, alliance_id):
        """Set of user ids allowed to lead the alliance (admin1 + role=admin)."""
        row = cassandra_session.execute(
            "SELECT admin1, member_roles FROM alliances WHERE alliance_id = %s", [alliance_id]
        ).one()
        if not row:
            return set()
        leads = {row.admin1} if row.admin1 else set()
        for uid, r in (getattr(row, 'member_roles', None) or {}).items():
            if r == 'admin':
                leads.add(uid)
        return leads

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
