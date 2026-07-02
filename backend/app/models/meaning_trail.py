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

from cassandra.cluster import Cluster
from cassandra.cqlengine import columns
from cassandra.cqlengine.models import Model
from cassandra.cqlengine import connection
from cassandra.cqlengine.management import sync_table
import uuid
import json
import os
from uuid import UUID
from datetime import datetime

#cluster = Cluster(['143.42.34.42'])  # provide your Cassandra host here
#cassandra_session = cluster.connect()
# Host(s) configurable via CASSANDRA_HOST (comma-separated), defaults to localhost.
CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
connection.setup(CASSANDRA_HOSTS, 'logosphere')

# Dedicated raw session (keyspace-bound) for cross-table reads like resolving
# user display names — mirrors the other models, avoids get_session() keyspace quirks.
_raw_session = Cluster(CASSANDRA_HOSTS).connect('logosphere')


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
    def create_for_opening(cls, initiator_id, other_user_id, other_user_name, description, project_name=None):
        """Create a fully-populated Exchange row when an Opening is accepted.
        initiator_id is the opening's provider; other_user_id is the accepter."""
        try:
            exchange_id = uuid.uuid4()
            cls.create(
                user_id=UUID(str(initiator_id)),
                exchange_id=exchange_id,
                other_user_id=UUID(str(other_user_id)),
                other_user_name=other_user_name,
                exchange_description=description,
                exchange_status='Initiated',
                project_name=project_name,
                project_start_timestamp=datetime.utcnow(),
            )
            return exchange_id
        except Exception as e:
            print(f"Error creating exchange from opening: {e}")
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
        }


    @staticmethod
    def _name_map():
        """{user_id: display name} for resolving the counterpart in an exchange."""
        try:
            out = {}
            for u in _raw_session.execute("SELECT user_id, name, surname FROM users"):
                full = f"{u.name or ''} {getattr(u, 'surname', '') or ''}".strip()
                out[u.user_id] = full or 'A member'
            return out
        except Exception as e:
            print(f"Error building name map: {e}")
            return {}

    @classmethod
    def _enrich(cls, row, target_id, viewer_id, names):
        """Row → dict with like summary and both-sides perspective fields."""
        d = row.to_dict()
        d['likes'] = Likes.summary_for_exchange(row.exchange_id, viewer_id)
        d['initiator_id'] = str(row.user_id) if row.user_id else None
        d['initiator_name'] = names.get(row.user_id, 'A member')
        # Perspective is relative to whose trail this is (target_id).
        d['viewer_is_initiator'] = str(row.user_id) == str(target_id)
        return d

    @classmethod
    def get_meaning_trail(cls, user_id, viewer_id=None):
        """Fetch a user's exchanges — both the ones they initiated and the ones
        where they are the other participant, so an exchange shows up in both
        parties' trails. `viewer_id` drives the "liked by me" flags."""
        try:
            target = UUID(str(user_id))
            names = cls._name_map()
            seen, meaning_trail = set(), []
            # Rows where the user is the initiator (efficient — partition key).
            owned = list(cls.objects(user_id=target))
            # Rows where the user is the other participant (secondary index).
            other = list(cls.objects(other_user_id=target).allow_filtering())
            for row in owned + other:
                if row.exchange_id in seen:
                    continue
                seen.add(row.exchange_id)
                meaning_trail.append(cls._enrich(row, user_id, viewer_id, names))
            return meaning_trail
        except Exception as e:
            print(f"Error occurred while fetching trust trail: {str(e)}")
            return None

    @classmethod
    def get_by_project_id(cls, project_id):
        """All exchanges tagged with this project, from any initiator — used to
        build a project's own (aggregate, multi-person) Meaning Trail. Unlike
        get_meaning_trail, perspective is always relative to each row's own
        initiator (not a single trail owner), so the frontend decides per row
        whether the actual viewer happens to be that initiator."""
        try:
            pid = UUID(str(project_id))
            rows = list(cls.objects.filter(project_id=pid).allow_filtering())
            names = cls._name_map()
            return [cls._enrich(row, row.user_id, None, names) for row in rows]
        except Exception as e:
            print(f"Error fetching exchanges by project: {e}")
            return []

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
            d = cls._enrich(row, viewer_id, viewer_id, names)
            is_initiator = str(row.user_id) == str(viewer_id)
            is_other = row.other_user_id is not None and str(row.other_user_id) == str(viewer_id)
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
            exchange.update(exchange_status=status)
        except Exception as e:
            print(f"Error occurred while setting the exchange status: {e}")

    @classmethod
    def get_by_id(cls, exchange_id, current_user_id):
        """Return (exchange_dict, is_initiator) or (None, None) if not a participant."""
        import traceback
        try:
            tx_uuid = UUID(str(exchange_id))
            user_uuid = UUID(str(current_user_id))

            # Efficient path: current user is the initiator (full PK lookup)
            rows = list(cls.objects(user_id=user_uuid, exchange_id=tx_uuid))
            if rows:
                d = rows[0].to_dict()
                d['likes'] = Likes.summary_for_exchange(tx_uuid, user_uuid)
                return d, True

            # Fallback: current user is the other participant.
            # exchange_id is a clustering key so we need allow_filtering to query without partition key.
            all_rows = list(cls.objects.filter(exchange_id=tx_uuid).allow_filtering())
            for row in all_rows:
                if row.other_user_id == user_uuid:
                    d = row.to_dict()
                    d['likes'] = Likes.summary_for_exchange(tx_uuid, user_uuid)
                    return d, False

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
    def get_completion_signal(cls, exchange_id):
        """Best-available timestamp for "this exchange looks completed" — used
        to aggregate a perpetual opening's 'Completed (multiple)' date.
        meaning_trail has no dedicated "became Finished" column, so this
        approximates using the latest comment timestamp once the exchange has
        reached a finished/receipted status. Returns None if not completed."""
        try:
            rows = list(cls.objects.filter(
                exchange_id=UUID(str(exchange_id))).limit(1).allow_filtering())
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
    def set_status_for(cls, initiator_user_id, exchange_id, status):
        """Update status using the full PK (initiator_user_id + exchange_id)."""
        try:
            rows = list(cls.objects(
                user_id=UUID(str(initiator_user_id)),
                exchange_id=UUID(str(exchange_id))
            ))
            if rows:
                rows[0].update(exchange_status=status)
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
                        author_id=None, author_name=None, cards=None):
        """comment_type: 'gratitude' | 'user' | 'other'"""
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
