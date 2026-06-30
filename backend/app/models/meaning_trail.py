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
import os
from uuid import UUID
from datetime import datetime

#cluster = Cluster(['143.42.34.42'])  # provide your Cassandra host here
#cassandra_session = cluster.connect()
# Host(s) configurable via CASSANDRA_HOST (comma-separated), defaults to localhost.
CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
connection.setup(CASSANDRA_HOSTS, 'logosphere')


class Likes(Model):
    __keyspace__ = 'logosphere'
    __table_name__ = 'likes'

    comment_id = columns.UUID(primary_key=True)
    comment_type= columns.Text()
    user_id = columns.UUID(primary_key=True)

    like = columns.Boolean()

    @classmethod
    def get_likes(cls, comment_id, comment_type):
        try:
            return cls.objects(comment_id=comment_id, comment_type=comment_type).count()
        except Exception as e:
            print(f"Error occurred while fetching likes: {e}")




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
    user_comment = columns.Text()
    user_comment_id = columns.UUID()
    user_comment_timestamp = columns.DateTime()
    other_comment = columns.Text()
    other_comment_id = columns.UUID()
    other_comment_author_id = columns.UUID()
    other_comment_author_name = columns.Text()
    other_comment_timestamp = columns.DateTime()

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
        return {
            'user_id': str(self.user_id),
            'exchange_id': str(self.exchange_id),
            'other_user_id': str(self.other_user_id),
            'other_user_name': self.other_user_name,
            'exchange_description': self.exchange_description,
            'exchange_status': self.exchange_status,
            'project_id': str(self.project_id),
            'project_name': self.project_name,
            'project_start_timestamp': self.project_start_timestamp,
            'gratitude_comment': self.gratitude_comment,
            'gratitude_comment_id': self.gratitude_comment_id,
            'gratitude_comment_timestamp': self.gratitude_comment_timestamp,
            'user_comment': self.user_comment,
            'user_comment_id': self.user_comment_id,
            'user_comment_timestamp': self.user_comment_timestamp,
            'other_comment': self.other_comment,
            'othercomment_id': self.other_comment_id,
            'other_comment_author_id': str(self.other_comment_author_id),
            'other_comment_author_name': self.other_comment_author_name,
            'other_comment_timestamp': self.other_comment_timestamp
        }


    @classmethod
    def get_meaning_trail(cls, user_id):
        try:
            user_id_uuid = UUID(user_id)
            meaning_trail_queryset = cls.objects(user_id=user_id)
            meaning_trail = []
            # print(user_id, meaning_trail_queryset)
            for exchange in meaning_trail_queryset:
                exchange_dict = exchange.to_dict()  # Convert the exchange object to a dictionary
                exchange_dict['exchange_history'] = {}
                gratitude_comment_likes = Likes.get_likes(exchange.gratitude_comment_id, "gratitude") if exchange.gratitude_comment_id is not None else []
                user_comment_likes = Likes.get_likes(exchange.user_comment_id, "user") if exchange.user_comment_id is not None else []
                other_comment_likes = Likes.get_likes(exchange.other_comment_id, "other") if exchange.other_comment_id is not None else []
                exchange_dict['exchange_history']['gratitude_comment_likes'] = gratitude_comment_likes
                exchange_dict['exchange_history']['user_comment_likes'] = user_comment_likes
                exchange_dict['exchange_history']['other_comment_likes'] = other_comment_likes
                meaning_trail.append(exchange_dict)
            return meaning_trail
        except Exception as e:
            print(f"Error occurred while fetching trust trail: {str(e)}")
            return None            

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
        try:
            tx_uuid = UUID(str(exchange_id))
            user_uuid = UUID(str(current_user_id))

            # Efficient path: current user is the initiator (full PK lookup)
            rows = list(cls.objects(user_id=user_uuid, exchange_id=tx_uuid))
            if rows:
                return rows[0].to_dict(), True

            # Fallback: raw CQL to check if viewer is the other_user_id
            session = connection.get_session()
            results = session.execute(
                "SELECT user_id, other_user_id FROM meaning_trail WHERE exchange_id = %s ALLOW FILTERING",
                [tx_uuid]
            )
            for raw in results:
                if raw.other_user_id == user_uuid:
                    # Re-fetch as cqlengine object so we can call to_dict()
                    initiator_rows = list(cls.objects(user_id=raw.user_id, exchange_id=tx_uuid))
                    if initiator_rows:
                        return initiator_rows[0].to_dict(), False
            return None, None
        except Exception as e:
            print(f"Error getting exchange by id: {e}")
            return None, None

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
    def add_comment_for(cls, initiator_user_id, exchange_id, comment_type, text,
                        author_id=None, author_name=None):
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
            if comment_type == 'gratitude':
                row.update(
                    gratitude_comment=text,
                    gratitude_comment_id=uuid.uuid4(),
                    gratitude_comment_timestamp=now,
                )
            elif comment_type == 'user':
                row.update(
                    user_comment=text,
                    user_comment_id=uuid.uuid4(),
                    user_comment_timestamp=now,
                )
            elif comment_type == 'other':
                row.update(
                    other_comment=text,
                    other_comment_id=uuid.uuid4(),
                    other_comment_author_id=UUID(str(author_id)) if author_id else None,
                    other_comment_author_name=author_name or '',
                    other_comment_timestamp=now,
                )
            return True
        except Exception as e:
            print(f"Error adding comment: {e}")
            return False
