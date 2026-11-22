# Whose a Meaning Trail is, who reads it, who may acknowledge on it, and what
# is on it.
#
#   person    read: members            write: members           owner: that person
#   sphere    read: its members        write: its members       owner: its admins
#   alliance  read: its sphere         write: its sphere        owner: its managers
#   project   read: its sphere         write: its sphere        owner: its managers
#   exchange  read: who can see it     write: sphere + parties  owner: both sides
#
# "Anyone can acknowledge anywhere, except in spheres they aren't in": so the
# platform-admin override reads and moderates, but doesn't write or highlight.
from app.db import session
from app.models.acknowledgement import Acknowledgement
from app.models.alliance import Alliance
from app.models.meaning_trail import MeaningTrail
from app.models.project import Project
from app.models.spheres import Sphere
from app.utils import timeline
from app.utils.access import as_uuid, exchange_sphere
from app.utils.permissions import can_manage_entity, get_entity_info


class Trail:
    def __init__(self, trail_id, kind, name, subject, sphere_id=None):
        self.id, self.kind, self.name, self.subject, self.sphere_id = trail_id, kind, name, subject, sphere_id

    @classmethod
    def find(cls, raw_id):
        tid = as_uuid(raw_id)
        if tid is None:
            return None
        person = session.execute('SELECT user_id, name, surname FROM users WHERE user_id = %s', [tid]).one()
        if person:
            name = f"{person.name or ''} {person.surname or ''}".strip() or 'A member'
            return cls(tid, 'user', name, person)
        sphere = Sphere.get_by_id(tid)
        if sphere:
            return cls(tid, 'sphere', sphere.name, sphere, tid)
        for kind, model in (('alliance', Alliance), ('project', Project)):
            group = model.get_by_id(tid)
            if group:
                return cls(tid, kind, group.name, group, group.sphere_id)
        row = MeaningTrail.row_of(tid)
        if row:
            return cls(tid, 'exchange', row.exchange_description or 'An exchange', row, exchange_sphere(row))
        return None

    @property
    def link(self):
        if self.kind == 'exchange':
            return f'/exchange?id={self.id}'
        return f'/{self.kind}?id={self.id}&tab=trail'

    def _in_group(self, sight):
        members = self.subject.members if self.kind == 'alliance' else self.subject.participants
        return sight.id in (members or [])

    def readable(self, sight):
        if sight.id is None:
            return False
        if self.kind == 'user':
            return True
        if self.kind == 'exchange':
            return sight.exchange(self.subject)
        if self.kind == 'sphere':
            return sight.sphere(self.id)
        return sight.sphere(self.sphere_id) or self._in_group(sight)

    def writable(self, sight):
        if sight.id is None:
            return False
        if self.kind == 'user':
            return True
        if self.kind == 'exchange' and sight.party(self.subject):
            return True
        return not self.sphere_id or sight.member_of(self.sphere_id)

    def owned(self, sight):
        if sight.id is None:
            return False
        if self.kind == 'user':
            return sight.id == self.id
        if self.kind == 'exchange':
            return sight.party(self.subject)
        return can_manage_entity(self.id, sight.id, include_platform_admin=False)

    def people(self):
        """The humans to tell about it: groups have no inbox."""
        if self.kind == 'user':
            return {self.id}
        if self.kind == 'sphere':
            return Sphere.admin_ids(self.id)
        if self.kind == 'alliance':
            return Alliance.lead_ids(self.id)
        if self.kind == 'project':
            return Project.manager_ids(self.id)
        x, out = self.subject, set()
        for side, acting in ((x.user_id, x.initiator_acting_user_id), (x.other_user_id, x.recipient_acting_user_id)):
            if acting:
                out.add(acting)
            elif side and not get_entity_info(side):
                out.add(side)
        return out

    def card_owners(self, author_id):
        """Whose cards an acknowledgement here may name."""
        owners = [author_id]
        if self.kind == 'exchange':
            x = self.subject
            owners += [x.user_id, x.other_user_id, x.initiator_acting_user_id, x.recipient_acting_user_id]
        else:
            owners.append(self.id)
            if self.kind in ('alliance', 'project') and self.sphere_id:
                owners.append(self.sphere_id)
        return owners

    def exchange_rows(self):
        """Every exchange on this trail, whoever is asking."""
        if self.kind == 'exchange':
            return []
        if self.kind == 'user':
            return MeaningTrail.rows_of_party(self.id)
        sides, project_ids, project_names = {self.id}, set(), set()
        if self.kind == 'project':
            project_ids.add(self.id)
            project_names.add(self.name)
        elif self.kind == 'alliance':
            listed = set(self.subject.projects or [])
            for p in Project.get_all():
                if p.sphere_id == self.sphere_id and (p.owner_alliance == self.name or p.name in listed):
                    project_ids.add(p.project_id)
                    project_names.add(p.name)
        else:
            sides |= {as_uuid(a['id']) for a in Alliance.list_for_sphere(self.id)}
            for p in Project.list_for_sphere(self.id):
                project_ids.add(as_uuid(p['id']))
                sides.add(as_uuid(p['id']))
        out = []
        for row in MeaningTrail.every_row():
            if row.user_id in sides or row.other_user_id in sides or (row.project_id and row.project_id in project_ids):
                out.append(row)
            elif self.kind == 'sphere':
                if exchange_sphere(row) == self.id:
                    out.append(row)
            elif row.project_name and row.project_name in project_names and exchange_sphere(row) == self.sphere_id:
                # Exchanges from openings carry their project's name, not its id.
                out.append(row)
        return out

    def chronology(self, sight=None):
        """The trail's entries; as `sight` sees them, or whole (for the rules)."""
        rows = self.exchange_rows()
        if sight is not None:
            rows = [r for r in rows if sight.exchange(r)]
        return timeline.chronology([(r.project_start_timestamp, r) for r in rows], Acknowledgement.on(self.id))
