# Model: ValueCard — a "Thick Model of Value" card for a user's Meaning Graph.
# Each card captures one endorsed value: what the user cares about, why,
# what it looks like in practice, what drift signals look like, and more.
# Stored in Cassandra with (user_id, card_id) as the composite primary key.

from cassandra.cluster import Cluster
import uuid
import logging
import os
from datetime import datetime

CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(CASSANDRA_HOSTS)
cassandra_session = cluster.connect('logosphere')

FRANKL_MODES = ('creative', 'experiential', 'attitudinal')
COLOR_KEYS = ('honey', 'leaf', 'terracotta', 'sage', 'moss')


class ValueCard:
    def __init__(self, card_id, user_id, title, care_about, because,
                 looks_like, drift_looks_like, in_conflict, never_do,
                 frankl_mode, color_key, created_at=None):
        self.card_id = card_id
        self.user_id = user_id
        self.title = title
        self.care_about = care_about
        self.because = because
        self.looks_like = looks_like or []
        self.drift_looks_like = drift_looks_like
        self.in_conflict = in_conflict
        self.never_do = never_do
        self.frankl_mode = frankl_mode
        self.color_key = color_key
        self.created_at = created_at or datetime.utcnow()

    def to_dict(self):
        return {
            'card_id': str(self.card_id),
            'user_id': str(self.user_id),
            'title': self.title,
            'care_about': self.care_about,
            'because': self.because,
            'looks_like': list(self.looks_like) if self.looks_like else [],
            'drift_looks_like': self.drift_looks_like,
            'in_conflict': self.in_conflict,
            'never_do': self.never_do,
            'frankl_mode': self.frankl_mode,
            'color_key': self.color_key,
            'created_at': self.created_at.isoformat() if self.created_at else None,
        }

    @classmethod
    def create(cls, data, user_id):
        card_id = uuid.uuid4()
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)

        title = data.get('title', '')
        care_about = data.get('care_about', '')
        because = data.get('because', '')
        looks_like = data.get('looks_like', [])
        drift_looks_like = data.get('drift_looks_like', '')
        in_conflict = data.get('in_conflict', '')
        never_do = data.get('never_do', '')
        frankl_mode = data.get('frankl_mode', 'creative')
        color_key = data.get('color_key', 'honey')
        now = datetime.utcnow()

        cassandra_session.execute(
            """INSERT INTO value_cards
               (user_id, card_id, title, care_about, because, looks_like,
                drift_looks_like, in_conflict, never_do, frankl_mode, color_key, created_at)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, card_id, title, care_about, because, looks_like,
             drift_looks_like, in_conflict, never_do, frankl_mode, color_key, now)
        )
        return cls(card_id, user_id, title, care_about, because, looks_like,
                   drift_looks_like, in_conflict, never_do, frankl_mode, color_key, now)

    @classmethod
    def get_for_user(cls, user_id):
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                return []
        rows = cassandra_session.execute(
            "SELECT * FROM value_cards WHERE user_id = %s", [user_id]
        )
        cards = []
        for r in rows:
            cards.append(cls(
                card_id=r.card_id,
                user_id=r.user_id,
                title=getattr(r, 'title', ''),
                care_about=getattr(r, 'care_about', ''),
                because=getattr(r, 'because', ''),
                looks_like=getattr(r, 'looks_like', []),
                drift_looks_like=getattr(r, 'drift_looks_like', ''),
                in_conflict=getattr(r, 'in_conflict', ''),
                never_do=getattr(r, 'never_do', ''),
                frankl_mode=getattr(r, 'frankl_mode', 'creative'),
                color_key=getattr(r, 'color_key', 'honey'),
                created_at=getattr(r, 'created_at', None),
            ))
        return cards

    @classmethod
    def delete(cls, user_id, card_id):
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        if isinstance(card_id, str):
            card_id = uuid.UUID(card_id)
        cassandra_session.execute(
            "DELETE FROM value_cards WHERE user_id = %s AND card_id = %s",
            [user_id, card_id]
        )
