# Who may see what across sphere boundaries: the one place that decides it.
#
# The promise (Privacy page): a sphere's openings, exchanges, receipts and
# people are for its members. The exceptions, all deliberate: the two sides of
# an exchange always see it, platform admins see everything, a public sphere
# shows its activity (signed-out visitors get counts, not people), and demo
# spheres list their members (they are AI personas).
#
# Make one Sight per request: it reads the viewer's spheres once.
import uuid

from app.db import session
from app.models.spheres import Sphere
from app.utils import demo
from app.utils.permissions import can_manage_entity, is_platform_admin


def as_uuid(value):
    if value is None or isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def exchange_sphere(row):
    """The sphere an exchange happened in, or None. Read afresh when the
    short-lived maps don't know the opening yet: a brand-new one must not
    count as "no sphere", which anyone may see."""
    found = demo.exchange_sphere_id(row)
    if found is not None:
        return found
    get = row.get if isinstance(row, dict) else (lambda k: getattr(row, k, None))
    for value, table, column in ((get('source_service_id'), 'services', 'service_id'),
                                 (get('project_id'), 'projects', 'project_id')):
        key = as_uuid(value)
        if key is None:
            continue
        hit = session.execute(f'SELECT sphere_id FROM {table} WHERE {column} = %s', [key]).one()
        if hit and hit.sphere_id:
            return hit.sphere_id
    return None


class Sight:
    """What one viewer may see. A viewer of None is a signed-out visitor."""

    def __init__(self, viewer_id):
        self.id = as_uuid(viewer_id)
        self.admin = bool(self.id) and is_platform_admin(self.id)
        self.spheres = Sphere.member_sphere_ids(self.id) if self.id else set()
        self._sides = {}

    def member_of(self, sphere_id):
        return as_uuid(sphere_id) in self.spheres

    def sphere(self, sphere_id):
        """May see what happens inside this sphere (no sphere: any member may)."""
        if self.id is None:
            return False
        return not sphere_id or self.admin or self.member_of(sphere_id)

    def on_side(self, side_id, acting_id=None):
        """This person is that side of an exchange: the person, whoever acted
        for the group, or one of the group's own managers."""
        side = as_uuid(side_id)
        if self.id is None or side is None:
            return False
        if self.id == side or self.id == as_uuid(acting_id):
            return True
        if side not in self._sides:
            self._sides[side] = can_manage_entity(side, self.id, include_platform_admin=False)
        return self._sides[side]

    def party(self, row):
        get = row.get if isinstance(row, dict) else (lambda k: getattr(row, k, None))
        return (self.on_side(get('user_id'), get('initiator_acting_user_id'))
                or self.on_side(get('other_user_id'), get('recipient_acting_user_id')))

    def exchange(self, row):
        if self.id is None:
            return False
        return self.sphere(exchange_sphere(row)) or self.party(row)

    def people_of(self, sphere):
        """May see who is in this sphere."""
        if self.id is None:
            return False
        return self.admin or self.member_of(sphere.sphere_id) or bool(sphere.is_public) or bool(sphere.is_demo)

    def value_cards(self, owner_id):
        """May read this owner's cards: 'ok', 'signin' or 'hidden'."""
        owner = as_uuid(owner_id)
        if owner is None:
            return 'hidden' if self.id else 'signin'
        sphere = session.execute('SELECT sphere_id, is_public FROM spheres WHERE sphere_id = %s', [owner]).one()
        if sphere:                                  # spheres are discoverable: so is what they stand for
            return 'ok' if self.id or sphere.is_public else 'signin'
        for table, column, members in (('alliances', 'alliance_id', 'members'),
                                       ('projects', 'project_id', 'participants')):
            row = session.execute(f'SELECT sphere_id, {members} FROM {table} WHERE {column} = %s', [owner]).one()
            if not row:
                continue
            if self.id is None:
                parent = row.sphere_id and session.execute(
                    'SELECT is_public FROM spheres WHERE sphere_id = %s', [row.sphere_id]).one()
                return 'ok' if parent and parent.is_public else 'signin'
            if self.sphere(row.sphere_id) or self.id in (getattr(row, members) or []):
                return 'ok'
            return 'hidden'
        return 'ok' if self.id else 'signin'        # a person's: for signed-in members


def without_people(sphere_dict):
    """A sphere as someone outside it sees it: how many, not who."""
    d = dict(sphere_dict)
    for key in ('members', 'participants', 'participant_names', 'alliances', 'projects', 'alliance_list', 'project_list'):
        if key in d:
            d[key] = []
    d['admin1'] = None
    return d


def group_without_people(group_dict):
    """An alliance or project as a signed-out visitor sees it."""
    d = dict(group_dict)
    d['member_count'] = len(d.get('members') or [])
    for key in ('members', 'participants'):
        d[key] = []
    for key in ('admin1', 'owner', 'owner_id', 'owner_name'):
        if key in d:
            d[key] = None
    return d


def resolve_cards(card_ids, owners, limit=8):
    """The stored cards behind ids a client named, looked up among those
    owners' graphs. What a client says a card reads is never stored."""
    from app.models.value_card import ValueCard
    hints = []
    for owner in owners:
        key = as_uuid(owner)
        if key and key not in hints:
            hints.append(key)
    out, seen = [], set()
    for raw in card_ids if isinstance(card_ids, (list, tuple)) else []:
        key = as_uuid(raw)
        if key is None or key in seen:
            continue
        seen.add(key)
        card = ValueCard.find_by_id(key, owner_hints=hints)
        if card:
            out.append(card)
        if len(out) >= limit or len(seen) >= limit * 2:
            break
    return out
