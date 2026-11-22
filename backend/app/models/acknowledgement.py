# Acknowledgements: short public words, optionally naming value cards, left on
# any Meaning Trail - a person's, a sphere's, an alliance's, a project's, or a
# single exchange's. trail_id is the id of whichever it is. Likes live in the
# `likes` table as (ack_id, 'ack').
import json
import uuid
from datetime import datetime

from app.db import session
from app.models.meaning_trail import Likes

LIKE = 'ack'
MAX_TEXT = 1000
MAX_CARDS = 5

DDL = ("CREATE TABLE IF NOT EXISTS trail_acknowledgements ("
       "trail_id uuid, created_at timestamp, ack_id uuid, author_id uuid, author_name text, "
       "body text, cards text, highlighted_at timestamp, "
       "PRIMARY KEY ((trail_id), created_at, ack_id)) "
       "WITH CLUSTERING ORDER BY (created_at DESC, ack_id ASC)")

_COLS = 'trail_id, created_at, ack_id, author_id, author_name, body, cards, highlighted_at'
_ROW = 'trail_id = %s AND created_at = %s AND ack_id = %s'


def ensure_tables():
    session.execute(DDL)


def now():
    """Cassandra keeps milliseconds; the key must read back as it was written."""
    t = datetime.utcnow()
    return t.replace(microsecond=t.microsecond // 1000 * 1000)


class Acknowledgement:
    def __init__(self, row):
        self.trail_id, self.created_at, self.ack_id = row.trail_id, row.created_at, row.ack_id
        self.author_id, self.author_name = row.author_id, row.author_name
        self.body, self.highlighted_at = row.body or '', row.highlighted_at
        try:
            self.cards = json.loads(row.cards) if row.cards else []
        except ValueError:
            self.cards = []

    @property
    def key(self):
        return [self.trail_id, self.created_at, self.ack_id]

    @classmethod
    def create(cls, trail_id, author_id, author_name, body, cards, ack_id=None, created_at=None):
        trail, ack = uuid.UUID(str(trail_id)), ack_id or uuid.uuid4()
        at = created_at or now()
        session.execute(
            'INSERT INTO trail_acknowledgements (trail_id, created_at, ack_id, author_id, author_name, body, cards) '
            'VALUES (%s, %s, %s, %s, %s, %s, %s)',
            [trail, at, ack, uuid.UUID(str(author_id)) if author_id else None, author_name, body,
             json.dumps(cards, default=str) if cards else None])
        return cls(session.execute(f'SELECT {_COLS} FROM trail_acknowledgements WHERE {_ROW}', [trail, at, ack]).one())

    @classmethod
    def on(cls, trail_id):
        """A trail's, newest first."""
        rows = session.execute(f'SELECT {_COLS} FROM trail_acknowledgements WHERE trail_id = %s',
                               [uuid.UUID(str(trail_id))])
        return [cls(r) for r in rows]

    @classmethod
    def find(cls, trail_id, ack_id):
        wanted = str(ack_id)
        return next((a for a in cls.on(trail_id) if str(a.ack_id) == wanted), None)

    @classmethod
    def everything(cls):
        return [cls(r) for r in session.execute(f'SELECT {_COLS} FROM trail_acknowledgements')]

    def highlight(self, on):
        self.highlighted_at = now() if on else None
        # IF EXISTS: an UPDATE is an upsert and would bring a removed one back as a husk.
        session.execute(f'UPDATE trail_acknowledgements SET highlighted_at = %s WHERE {_ROW} IF EXISTS',
                        [self.highlighted_at] + self.key)

    def remove(self):
        session.execute(f'DELETE FROM trail_acknowledgements WHERE {_ROW}', self.key)
        session.execute('DELETE FROM likes WHERE exchange_id = %s AND comment_type = %s', [self.ack_id, LIKE])

    def set_like(self, user_id, liked):
        ack, who = self.ack_id, uuid.UUID(str(user_id))
        if liked:
            Likes.create(exchange_id=ack, comment_type=LIKE, user_id=who)
        else:
            Likes.objects(exchange_id=ack, comment_type=LIKE, user_id=who).delete()
        return self.likes(user_id)

    def liked_by(self, user_id):
        return Likes.is_liked_by(self.ack_id, LIKE, user_id)

    def likes(self, viewer_id):
        by = Likes.likers(self.ack_id, LIKE)
        viewer = str(viewer_id or '')
        return {'count': len(by), 'liked': any(p['id'] == viewer for p in by), 'by': by,
                'own': bool(viewer) and str(self.author_id or '') == viewer}

    def to_dict(self, viewer_id, names=None, highlighted=None, owner=False, moderator=False):
        """As one viewer sees it. `owner`: it's their trail; `moderator`: a platform admin."""
        from app.utils.demo import is_agent
        mine = bool(viewer_id) and str(self.author_id or '') == str(viewer_id)
        return {
            'ack_id': str(self.ack_id),
            'trail_id': str(self.trail_id),
            'author_id': str(self.author_id) if self.author_id else None,
            'author_name': (names or {}).get(self.author_id) or self.author_name or 'A member',
            'author_is_agent': is_agent(self.author_id),
            'text': self.body,
            'cards': self.cards,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'highlighted': bool(self.highlighted_at) if highlighted is None else highlighted,
            'likes': self.likes(viewer_id),
            'can_highlight': owner,
            'can_remove': mine or owner or moderator,
        }
