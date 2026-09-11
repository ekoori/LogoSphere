# File: ./backend/app/models/meaning_trail.py
# Description: Model file for handling trust trails (exchange history and trust ratings received by a user)
# Class: MeaningTrail, Likes
# Properties: 
#    [-] user: Refers to the user who the meaning_trail is associated with.
#    [-] exchange_history: List of last 100 exchanges done by the user.
# Methods: 
#    [-] add_exchange(cls, user_id, other_user_id, project_id): Adds a graded entry against a exchange in a user's trust trail.
#    [-] get_meaning_trail(cls, user_id): fetches a complete MeaningTrail of a particular user with all associated like counts and stores it into rtansaction_history.
#    [-] add_gratitude_comment(cls, exchange_id, gratitude_comment): Adds a gratitude_comment to a exchange
#    [-] add_user_comment(cls, user_comment): Adds a user_comment to a gratitude comment.
#    [-] add_other_comment(cls, other_user_id, other_comment): Adds an other_comment
#    [-] set_status(cls, exchange_id, status): Change status of a exchange

# Features:
#    [-] Users can view their history of exchanges and the corresponding trust ratings received.
#    [-] User can grade other user's exchanges (trust scores, feedbacks etc.) in form of entries in their MeaningTrail.
#    [-] Users can receive trust/gratitude entries from other users in the form of textual comments.

from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from cassandra.cqlengine import connection
from cassandra.cqlengine.management import sync_table
import uuid
import json
import os
import time
from uuid import UUID
from datetime import datetime

# One shared driver session for the whole app (see app/db.py); cqlengine is
# registered against it there too.
from app.db import session as _raw_session

# Short-lived cache of the {user_id: display name} map. Every meaning-trail read
# needs it to resolve counterparts, and it changes only when a user registers or
# renames — so a brief TTL avoids a full `users` scan on every request while
# staying fresh enough (a newly registered user shows within TTL seconds).
_NAME_MAP_TTL = 30.0
_name_map_cache = {'data': None, 'ts': 0.0}
# Parallel {entity_id: 'sphere'|'alliance'|'project'} map so the exchange view
# can tell whether a participant is a person or a group (and link accordingly).
_kind_map_cache = {'data': None, 'ts': 0.0}


# Comment types that can be liked on an exchange. 'exchange' is the card itself;
# the others correspond to the three comment slots on a MeaningTrail row.
LIKE_TYPES = ('exchange', 'gratitude', 'user', 'other')


class Likes(Model):
    """Per-user like rows, scoped to an exchange + comment_type.

    A row's existence means that user liked that target. The like count is
    COUNT(*) over the (exchange_id, comment_type) partition — Cassandra cannot
    store a live counter alongside the meaning_trail columns, so this companion
    table is the idiomatic way to model likes for that page.
    """
    __keyspace__ = 'logosphere'
    __table_name__ = 'likes'

    exchange_id = columns.UUID(partition_key=True)
    comment_type = columns.Text(partition_key=True)
    user_id = columns.UUID(primary_key=True)

    @classmethod
    def count(cls, exchange_id, comment_type):
        try:
            return cls.objects(exchange_id=UUID(str(exchange_id)),
                               comment_type=comment_type).count()
        except Exception as e:
            print(f"Error counting likes: {e}")
            return 0

    @classmethod
    def is_liked_by(cls, exchange_id, comment_type, user_id):
        """True if this user has liked (exchange_id, comment_type). Full-PK lookup."""
        try:
            return cls.objects(exchange_id=UUID(str(exchange_id)),
                               comment_type=comment_type,
                               user_id=UUID(str(user_id))).count() > 0
        except Exception as e:
            print(f"Error checking like: {e}")
            return False

    @classmethod
    def toggle(cls, exchange_id, comment_type, user_id):
        """Add the like if absent, remove it if present.
        Returns (liked: bool, count: int)."""
        ex = UUID(str(exchange_id))
        uid = UUID(str(user_id))
        if cls.is_liked_by(ex, comment_type, uid):
            cls.objects(exchange_id=ex, comment_type=comment_type, user_id=uid).delete()
            liked = False
        else:
            cls.create(exchange_id=ex, comment_type=comment_type, user_id=uid)
            liked = True
        return liked, cls.count(ex, comment_type)

    @classmethod
    def summary_for_exchange(cls, exchange_id, user_id=None):
        """Return {comment_type: {'count': n, 'liked': bool}} for all like types."""
        out = {}
        for ct in LIKE_TYPES:
            liked = cls.is_liked_by(exchange_id, ct, user_id) if user_id else False
            out[ct] = {'count': cls.count(exchange_id, ct), 'liked': liked}
        return out




class MeaningTrail(Model):
    __keyspace__ = 'logosphere'
    __table_name__ = 'meaning_trail'

    user_id = columns.UUID(primary_key=True)
    exchange_id = columns.UUID(primary_key=True, clustering_order='DESC')
    other_user_id = columns.UUID()
    other_user_name = columns.Text()
    exchange_description = columns.Text()
    exchange_status = columns.Text()
    project_id = columns.UUID()
    project_name = columns.Text()
    project_start_timestamp = columns.DateTime()
    gratitude_comment = columns.Text()
    gratitude_comment_id = columns.UUID()
    gratitude_comment_timestamp = columns.DateTime()
    gratitude_comment_cards = columns.Text()
    user_comment = columns.Text()
    user_comment_id = columns.UUID()
    user_comment_timestamp = columns.DateTime()
    user_comment_cards = columns.Text()
    other_comment = columns.Text()
    other_comment_id = columns.UUID()
    other_comment_author_id = columns.UUID()
    other_comment_author_name = columns.Text()
    other_comment_timestamp = columns.DateTime()
    other_comment_cards = columns.Text()
    # One extra, lower-key note each side may leave once both have receipted.
    initiator_comment = columns.Text()
    initiator_comment_timestamp = columns.DateTime()
    recipient_comment = columns.Text()
    recipient_comment_timestamp = columns.DateTime()
    # When the initiator is an entity (sphere/alliance/project), the human who
    # acted on its behalf — "Joe on behalf of <Entity>".
    initiator_acting_user_id = columns.UUID()
    initiator_acting_user_name = columns.Text()
    # Symmetric pair for the recipient side: when an opening was accepted on
    # behalf of an alliance/project, the human who accepted for it.
    recipient_acting_user_id = columns.UUID()
    recipient_acting_user_name = columns.Text()
    # Editable details (inherited from the opening, changeable until finished).
    exchange_long_description = columns.Text()
    exchange_image = columns.Blob()
    # Structured context on the recipient's receipt (Time / Effort / Care / ...).
    gratitude_comment_context = columns.Text()
    # The opening this exchange was created from (for a "created from" link).
    source_service_id = columns.UUID()
    # Per-stage transition timestamps (Initiated = project_start_timestamp).
    in_progress_at = columns.DateTime()
    finished_at = columns.DateTime()
    receipted_at = columns.DateTime()

    @classmethod
    def add_exchange(cls, user_id, other_user_id, project_id):
        try:
            cls.create(
                user_id=user_id,
                other_user_id=other_user_id,
                exchange_id=uuid.uuid4(),
                project_id=project_id
            )
        except Exception as e:
            print(f"Error occurred while adding a exchange: {e}")

    @classmethod
    def create_for_opening(cls, initiator_id, other_user_id, other_user_name, description,
                           project_name=None, acting_user_id=None, acting_user_name=None,
                           long_description=None, image=None,
                           recipient_acting_user_id=None, recipient_acting_user_name=None,
                           source_service_id=None):
        """Create a fully-populated Exchange row when an Opening is accepted.
        initiator_id is the opening's provider; other_user_id is the accepter.
        acting_user_* names the human when the provider is an entity;
        recipient_acting_user_* names the human when the accepter is an entity.
        source_service_id links back to the opening. The exchange inherits the
        opening's long description and banner image."""
        try:
            exchange_id = uuid.uuid4()
            cls.create(
                user_id=UUID(str(initiator_id)),
                exchange_id=exchange_id,
                other_user_id=UUID(str(other_user_id)),
                other_user_name=other_user_name,
                exchange_description=description,
                exchange_long_description=long_description,
                exchange_image=image,
                exchange_status='Initiated',
                project_name=project_name,
                project_start_timestamp=datetime.utcnow(),
                initiator_acting_user_id=UUID(str(acting_user_id)) if acting_user_id else None,
                initiator_acting_user_name=acting_user_name,
                recipient_acting_user_id=UUID(str(recipient_acting_user_id)) if recipient_acting_user_id else None,
                recipient_acting_user_name=recipient_acting_user_name,
                source_service_id=UUID(str(source_service_id)) if source_service_id else None,
            )
            return exchange_id
        except Exception as e:
            import logging as _logging
            _logging.getLogger(__name__).exception(f"Error creating exchange from opening: {e}")
            return None

    def to_dict(self):
        def _uuid(v):
            return str(v) if v is not None else None

        def _dt(v):
            return v.isoformat() if v is not None else None

        def _cards(v):
            if not v:
                return []
            try:
                return json.loads(v)
            except Exception:
                return []

        return {
            'user_id': _uuid(self.user_id),
            'exchange_id': _uuid(self.exchange_id),
            'other_user_id': _uuid(self.other_user_id),
            'other_user_name': self.other_user_name,
            'exchange_description': self.exchange_description,
            'exchange_status': self.exchange_status,
            'project_id': _uuid(self.project_id),
            'project_name': self.project_name,
            'project_start_timestamp': _dt(self.project_start_timestamp),
            'gratitude_comment': self.gratitude_comment,
            'gratitude_comment_id': _uuid(self.gratitude_comment_id),
            'gratitude_comment_timestamp': _dt(self.gratitude_comment_timestamp),
            'gratitude_comment_cards': _cards(self.gratitude_comment_cards),
            'user_comment': self.user_comment,
            'user_comment_id': _uuid(self.user_comment_id),
            'user_comment_timestamp': _dt(self.user_comment_timestamp),
            'user_comment_cards': _cards(self.user_comment_cards),
            'other_comment': self.other_comment,
            'other_comment_id': _uuid(self.other_comment_id),
            'other_comment_author_id': _uuid(self.other_comment_author_id),
            'other_comment_author_name': self.other_comment_author_name,
            'other_comment_timestamp': _dt(self.other_comment_timestamp),
            'other_comment_cards': _cards(self.other_comment_cards),
            'initiator_comment': self.initiator_comment,
            'initiator_comment_timestamp': _dt(self.initiator_comment_timestamp),
            'recipient_comment': self.recipient_comment,
            'recipient_comment_timestamp': _dt(self.recipient_comment_timestamp),
            'initiator_acting_user_id': _uuid(self.initiator_acting_user_id),
            'initiator_acting_user_name': self.initiator_acting_user_name,
            'recipient_acting_user_id': _uuid(self.recipient_acting_user_id),
            'recipient_acting_user_name': self.recipient_acting_user_name,
            'source_service_id': _uuid(self.source_service_id),
            'in_progress_at': _dt(self.in_progress_at),
            'finished_at': _dt(self.finished_at),
            'receipted_at': _dt(self.receipted_at),
            'exchange_long_description': self.exchange_long_description,
            'gratitude_comment_context': self.gratitude_comment_context,
            # Image bytes are served separately via /api/exchange/<id>/image to
            # keep the (potentially large) blob out of trail-list payloads.
            'has_image': bool(self.exchange_image),
        }


    @staticmethod
    def _name_map():
        """{user_id: display name} for resolving the counterpart in an exchange.
        Cached for _NAME_MAP_TTL seconds to avoid a full `users` scan per read."""
        now = time.time()
        if _name_map_cache['data'] is not None and (now - _name_map_cache['ts']) < _NAME_MAP_TTL:
            return _name_map_cache['data']
        try:
            out = {}
            for u in _raw_session.execute("SELECT user_id, name, surname FROM users"):
                full = f"{u.name or ''} {getattr(u, 'surname', '') or ''}".strip()
                out[u.user_id] = full or 'A member'
            # Entities can be an exchange's initiator too (an opening posted on
            # behalf of a sphere/alliance/project), so resolve their ids to names.
            for s in _raw_session.execute("SELECT sphere_id, name FROM spheres"):
                if s.name:
                    out[s.sphere_id] = s.name
            for a in _raw_session.execute("SELECT alliance_id, name FROM alliances"):
                if a.name:
                    out[a.alliance_id] = a.name
            for p in _raw_session.execute("SELECT project_id, name FROM projects"):
                if p.name:
                    out[p.project_id] = p.name
            _name_map_cache['data'] = out
            _name_map_cache['ts'] = now
            return out
        except Exception as e:
            print(f"Error building name map: {e}")
            return _name_map_cache['data'] or {}

    @staticmethod
    def _kind_map():
        """{entity_id: 'sphere'|'alliance'|'project'} — anything not present is a
        person. Lets the exchange view link a participant to the right page and
        show whether the counterpart is a group. Cached like _name_map."""
        now = time.time()
        if _kind_map_cache['data'] is not None and (now - _kind_map_cache['ts']) < _NAME_MAP_TTL:
            return _kind_map_cache['data']
        try:
            out = {}
            for s in _raw_session.execute("SELECT sphere_id FROM spheres"):
                out[s.sphere_id] = 'sphere'
            for a in _raw_session.execute("SELECT alliance_id FROM alliances"):
                out[a.alliance_id] = 'alliance'
            for p in _raw_session.execute("SELECT project_id FROM projects"):
                out[p.project_id] = 'project'
            _kind_map_cache['data'] = out
            _kind_map_cache['ts'] = now
            return out
        except Exception as e:
            print(f"Error building kind map: {e}")
            return _kind_map_cache['data'] or {}

    @staticmethod
    def _add_kinds(d, kmap):
        """Tag each side of the exchange with the counterpart's kind
        (user/sphere/alliance/project) so the client links to the right page."""
        d['initiator_kind'] = kmap.get(UUID(d['user_id']), 'user') if d.get('user_id') else 'user'
        d['other_kind'] = kmap.get(UUID(d['other_user_id']), 'user') if d.get('other_user_id') else 'user'
        return d

    @classmethod
    def _enrich(cls, row, target_id, viewer_id, names, kinds=None):
        """Row → dict with like summary and both-sides perspective fields."""
        d = row.to_dict()
        d['likes'] = Likes.summary_for_exchange(row.exchange_id, viewer_id)
        d['initiator_id'] = str(row.user_id) if row.user_id else None
        d['initiator_name'] = names.get(row.user_id, 'A member')
        # Perspective is relative to whose trail this is (target_id).
        d['viewer_is_initiator'] = str(row.user_id) == str(target_id)
        if kinds is not None:
            cls._add_kinds(d, kinds)
        return d

    @classmethod
    def get_meaning_trail(cls, user_id, viewer_id=None):
        """Fetch a user's exchanges — both the ones they initiated and the ones
        where they are the other participant, so an exchange shows up in both
        parties' trails. `viewer_id` drives the "liked by me" flags."""
        try:
            target = UUID(str(user_id))
            names, kinds = cls._name_map(), cls._kind_map()
            seen, meaning_trail = set(), []
            # Rows where the user is the initiator (efficient — partition key).
            owned = list(cls.objects(user_id=target))
            # Rows where the user is the other participant (secondary index).
            other = list(cls.objects(other_user_id=target).allow_filtering())
            for row in owned + other:
                if row.exchange_id in seen:
                    continue
                seen.add(row.exchange_id)
                meaning_trail.append(cls._enrich(row, user_id, viewer_id, names, kinds))
            return meaning_trail
        except Exception as e:
            print(f"Error occurred while fetching trust trail: {str(e)}")
            return None

    @classmethod
    def get_by_project_id(cls, project_id, viewer_id=None):
        """All exchanges tagged with this project, from any initiator — used to
        build a project's own (aggregate, multi-person) Meaning Trail. Unlike
        get_meaning_trail, perspective is always relative to each row's own
        initiator (not a single trail owner), so the frontend decides per row
        whether the actual viewer happens to be that initiator.

        viewer_id drives the "liked by me" flags — it must be the *actual*
        viewer, not the row's initiator; otherwise a user who already liked an
        exchange sees it as un-liked here and clicking toggles their like off
        (making the count appear to drop)."""
        try:
            pid = UUID(str(project_id))
            rows = list(cls.objects.filter(project_id=pid).allow_filtering())
            names, kinds = cls._name_map(), cls._kind_map()
            return [cls._enrich(row, row.user_id, viewer_id, names, kinds) for row in rows]
        except Exception as e:
            print(f"Error fetching exchanges by project: {e}")
            return []

    @staticmethod
    def _viewer_on_side(side_id, acting_user_id, viewer_id):
        """Whether `viewer_id` counts as a given side of an exchange. True if
        they are that side directly, the human who acted for it when the side
        is an entity, or a current manager of that entity — so acting on behalf
        of an alliance/project (posting or accepting) grants the human the
        participant powers (receipts, notes) for that side."""
        if side_id is None:
            return False
        if str(side_id) == str(viewer_id):
            return True
        if acting_user_id and str(acting_user_id) == str(viewer_id):
            return True
        from app.utils.permissions import can_manage_entity
        return can_manage_entity(side_id, viewer_id)

    @classmethod
    def get_for_view(cls, exchange_id, viewer_id):
        """Return (exchange_dict, is_initiator, is_other) for ANY authenticated
        viewer — participants and onlookers alike (onlookers may acknowledge).
        Returns (None, False, False) if the exchange doesn't exist."""
        try:
            tx = UUID(str(exchange_id))
            rows = list(cls.objects.filter(exchange_id=tx).limit(1).allow_filtering())
            if not rows:
                return None, False, False
            row = rows[0]
            names = cls._name_map()
            d = cls._enrich(row, viewer_id, viewer_id, names, cls._kind_map())
            is_initiator = cls._viewer_on_side(row.user_id, row.initiator_acting_user_id, viewer_id)
            is_other = cls._viewer_on_side(row.other_user_id, row.recipient_acting_user_id, viewer_id)
            return d, is_initiator, is_other
        except Exception as e:
            print(f"Error getting exchange for view: {e}")
            return None, False, False

    @classmethod
    def add_gratitude_comment(cls, exchange_id, gratitude_comment):
        try:
            exchange = cls.objects(exchange_id=exchange_id).get()
            exchange.update(gratitude_comment=gratitude_comment)
        except Exception as e:
            print(f"Error occurred while adding a gratitude comment: {e}")

    @classmethod
    def add_user_comment(cls, exchange_id, user_comment):
        try:
            exchange = cls.objects(exchange_id=exchange_id).get()
            exchange.update(user_comment=user_comment)
        except Exception as e:
            print(f"Error occurred while adding a user comment: {e}")

    @classmethod
    def add_other_comment(cls, exchange_id, other_user_id, other_comment):
        try:
            exchange = cls.objects(exchange_id=exchange_id).get()
            exchange.update(other_comment_author_id=other_user_id, other_comment=other_comment)
        except Exception as e:
            print(f"Error occurred while adding an other comment: {e}")

    @classmethod
    def set_status(cls, exchange_id, status):
        try:
            exchange = cls.objects(exchange_id=exchange_id).get()
            fields = {'exchange_status': status}
            # Stamp when each tracked stage was reached, so the progress bar can
            # show the transition date. Only set the first time each is reached.
            col = {'In Progress': 'in_progress_at', 'Finished': 'finished_at',
                   'Receipted': 'receipted_at'}.get(status)
            if col and getattr(exchange, col, None) is None:
                fields[col] = datetime.utcnow()
            exchange.update(**fields)
        except Exception as e:
            print(f"Error occurred while setting the exchange status: {e}")

    @classmethod
    def get_by_id(cls, exchange_id, current_user_id):
        """Return (exchange_dict, is_initiator) or (None, None) if not a participant."""
        import traceback
        try:
            tx_uuid = UUID(str(exchange_id))
            user_uuid = UUID(str(current_user_id))

            names, kinds = cls._name_map(), cls._kind_map()
            # Efficient path: current user is the initiator (full PK lookup)
            rows = list(cls.objects(user_id=user_uuid, exchange_id=tx_uuid))
            if rows:
                return cls._enrich(rows[0], user_uuid, user_uuid, names, kinds), True

            # Fallback: current user is (or acts for / manages) either side.
            # exchange_id is a clustering key so we need allow_filtering to query without partition key.
            all_rows = list(cls.objects.filter(exchange_id=tx_uuid).allow_filtering())
            for row in all_rows:
                if cls._viewer_on_side(row.user_id, row.initiator_acting_user_id, user_uuid):
                    return cls._enrich(row, user_uuid, user_uuid, names, kinds), True
                if cls._viewer_on_side(row.other_user_id, row.recipient_acting_user_id, user_uuid):
                    return cls._enrich(row, user_uuid, user_uuid, names, kinds), False

            return None, None
        except Exception as e:
            print(f"Error getting exchange by id: {e}")
            print(traceback.format_exc())
            return None, None

    @classmethod
    def exists(cls, exchange_id):
        """True if any row carries this exchange_id. exchange_id is a clustering
        key, so this needs allow_filtering — acceptable for low-frequency actions."""
        try:
            rows = list(cls.objects.filter(
                exchange_id=UUID(str(exchange_id))).limit(1).allow_filtering())
            return len(rows) > 0
        except Exception as e:
            print(f"Error checking exchange existence: {e}")
            return False

    @classmethod
    def get_completion_signal(cls, exchange_id, initiator_id):
        """Best-available timestamp for "this exchange looks completed" — used
        to aggregate a perpetual opening's 'Completed (multiple)' date.
        meaning_trail has no dedicated "became Finished" column, so this
        approximates using the latest comment timestamp once the exchange has
        reached a finished/receipted status. Returns None if not completed.

        `initiator_id` is the exchange's initiator (the opening's provider), which
        together with `exchange_id` is the full primary key — a single-partition
        point read, so this avoids the previous allow_filtering multi-partition
        scan (this runs per confirmed acceptance inside the openings list)."""
        try:
            rows = list(cls.objects(
                user_id=UUID(str(initiator_id)), exchange_id=UUID(str(exchange_id))))
            if not rows:
                return None
            row = rows[0]
            if row.exchange_status not in ('Finished', 'Receipted', 'Additional Comments Added'):
                return None
            candidates = [row.gratitude_comment_timestamp, row.user_comment_timestamp,
                          row.project_start_timestamp]
            candidates = [c for c in candidates if c]
            return max(candidates) if candidates else None
        except Exception as e:
            print(f"Error getting completion signal: {e}")
            return None

    @classmethod
    def is_finished(cls, exchange_id):
        """Finished = both sides have receipted (recipient's gratitude + the
        initiator's note). After this the exchange is immutable."""
        try:
            rows = list(cls.objects.filter(
                exchange_id=UUID(str(exchange_id))).limit(1).allow_filtering())
            if not rows:
                return False
            r = rows[0]
            return bool(r.gratitude_comment and r.user_comment)
        except Exception as e:
            print(f"Error checking finished: {e}")
            return False

    @classmethod
    def edit_details(cls, initiator_id, exchange_id, title=None, long_description=None, image=None):
        """Edit the exchange's title / description / image on the initiator's row
        (the single stored row). Callers enforce the not-finished rule."""
        try:
            rows = list(cls.objects(
                user_id=UUID(str(initiator_id)), exchange_id=UUID(str(exchange_id))))
            if not rows:
                return False
            fields = {}
            if title is not None:
                fields['exchange_description'] = title
            if long_description is not None:
                fields['exchange_long_description'] = long_description
            if image is not None:
                fields['exchange_image'] = image
            if fields:
                rows[0].update(**fields)
            return True
        except Exception as e:
            print(f"Error editing exchange: {e}")
            return False

    @classmethod
    def get_image(cls, exchange_id):
        """Raw banner-image bytes for an exchange (served via an endpoint)."""
        try:
            rows = list(cls.objects.filter(
                exchange_id=UUID(str(exchange_id))).limit(1).allow_filtering())
            if rows and rows[0].exchange_image:
                return rows[0].exchange_image
            return None
        except Exception as e:
            print(f"Error getting exchange image: {e}")
            return None

    @classmethod
    def set_receipt_photos(cls, exchange_id, images):
        """Store up to 3 receipt photos (replacing any existing) in the
        receipt_photos companion table, keyed by (exchange_id, idx)."""
        ex = UUID(str(exchange_id))
        try:
            _raw_session.execute("DELETE FROM receipt_photos WHERE exchange_id = %s", [ex])
            for i, img in enumerate((images or [])[:3]):
                _raw_session.execute(
                    "INSERT INTO receipt_photos (exchange_id, idx, image) VALUES (%s, %s, %s)",
                    [ex, i, img])
            return True
        except Exception as e:
            print(f"Error storing receipt photos: {e}")
            return False

    @classmethod
    def receipt_photo_count(cls, exchange_id):
        try:
            rows = _raw_session.execute(
                "SELECT idx FROM receipt_photos WHERE exchange_id = %s", [UUID(str(exchange_id))])
            return len(list(rows))
        except Exception as e:
            print(f"Error counting receipt photos: {e}")
            return 0

    @classmethod
    def get_receipt_photo(cls, exchange_id, idx):
        try:
            row = _raw_session.execute(
                "SELECT image FROM receipt_photos WHERE exchange_id = %s AND idx = %s",
                [UUID(str(exchange_id)), int(idx)]).one()
            return row.image if row else None
        except Exception as e:
            print(f"Error getting receipt photo: {e}")
            return None

    @classmethod
    def set_status_for(cls, initiator_user_id, exchange_id, status):
        """Update status using the full PK (initiator_user_id + exchange_id),
        stamping the per-stage transition timestamp the first time each tracked
        stage is reached (so the progress bar can show when it happened)."""
        try:
            rows = list(cls.objects(
                user_id=UUID(str(initiator_user_id)),
                exchange_id=UUID(str(exchange_id))
            ))
            if rows:
                row = rows[0]
                fields = {'exchange_status': status}
                col = {'In Progress': 'in_progress_at', 'Finished': 'finished_at',
                       'Receipted': 'receipted_at'}.get(status)
                if col and getattr(row, col, None) is None:
                    fields[col] = datetime.utcnow()
                row.update(**fields)
                return True
            return False
        except Exception as e:
            print(f"Error setting status: {e}")
            return False

    @classmethod
    def add_followup_for(cls, initiator_user_id, exchange_id, side, text):
        """Store the one lower-key follow-up note a participant may leave after
        both sides have receipted. `side` is 'initiator' or 'recipient'.
        Returns 'ok' | 'exists' | 'not_ready' | False."""
        try:
            rows = list(cls.objects(
                user_id=UUID(str(initiator_user_id)),
                exchange_id=UUID(str(exchange_id))
            ))
            if not rows:
                return False
            row = rows[0]
            # Both receipts must be in first.
            if not (row.gratitude_comment and row.user_comment):
                return 'not_ready'
            now = datetime.utcnow()
            if side == 'initiator':
                if row.initiator_comment:
                    return 'exists'
                row.update(initiator_comment=text, initiator_comment_timestamp=now)
            elif side == 'recipient':
                if row.recipient_comment:
                    return 'exists'
                row.update(recipient_comment=text, recipient_comment_timestamp=now)
            else:
                return False
            return 'ok'
        except Exception as e:
            print(f"Error adding follow-up comment: {e}")
            return False

    @classmethod
    def add_comment_for(cls, initiator_user_id, exchange_id, comment_type, text,
                        author_id=None, author_name=None, cards=None, context=None):
        """comment_type: 'gratitude' | 'user' | 'other'. `context` (the
        Time/Effort/Care/... note) is only stored on a gratitude receipt."""
        try:
            rows = list(cls.objects(
                user_id=UUID(str(initiator_user_id)),
                exchange_id=UUID(str(exchange_id))
            ))
            if not rows:
                return False
            now = datetime.utcnow()
            row = rows[0]
            cards_json = json.dumps(cards) if cards else None
            if comment_type == 'gratitude':
                row.update(
                    gratitude_comment=text,
                    gratitude_comment_id=uuid.uuid4(),
                    gratitude_comment_timestamp=now,
                    gratitude_comment_cards=cards_json,
                    gratitude_comment_context=(context or None),
                )
            elif comment_type == 'user':
                row.update(
                    user_comment=text,
                    user_comment_id=uuid.uuid4(),
                    user_comment_timestamp=now,
                    user_comment_cards=cards_json,
                )
            elif comment_type == 'other':
                row.update(
                    other_comment=text,
                    other_comment_id=uuid.uuid4(),
                    other_comment_author_id=UUID(str(author_id)) if author_id else None,
                    other_comment_author_name=author_name or '',
                    other_comment_timestamp=now,
                    other_comment_cards=cards_json,
                )
            return True
        except Exception as e:
            print(f"Error adding comment: {e}")
            return False
