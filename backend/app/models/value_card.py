# Model: ValueCard — a "Thick Model of Value" card for a user's Meaning Graph.
# Each card captures one endorsed value: what the user cares about, why,
# what it looks like in practice, what drift signals look like, and more.
# Stored in Cassandra with (user_id, card_id) as the composite primary key.

import uuid
import logging
import os
from datetime import datetime

from app.db import session as cassandra_session

FRANKL_MODES = ('creative', 'experiential', 'attitudinal')
COLOR_KEYS = ('honey', 'leaf', 'terracotta', 'sage', 'moss')


class ValueCard:
    def __init__(self, card_id, user_id, title, care_about, because,
                 looks_like, drift_looks_like, in_conflict, never_do,
                 frankl_mode, color_key, created_at=None,
                 is_current=True, replaces_card_id=None):
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
        # is_current is None for rows written before this column existed —
        # treated as current (they've never been superseded by an edit).
        self.is_current = is_current is not False
        self.replaces_card_id = replaces_card_id

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
            'is_current': self.is_current,
            'replaces_card_id': str(self.replaces_card_id) if self.replaces_card_id else None,
        }

    @classmethod
    def _row_to_card(cls, r):
        return cls(
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
            is_current=getattr(r, 'is_current', True),
            replaces_card_id=getattr(r, 'replaces_card_id', None),
        )

    @classmethod
    def create(cls, data, user_id, replaces_card_id=None):
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
                drift_looks_like, in_conflict, never_do, frankl_mode, color_key,
                created_at, is_current, replaces_card_id)
               VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
            (user_id, card_id, title, care_about, because, looks_like,
             drift_looks_like, in_conflict, never_do, frankl_mode, color_key, now,
             True, replaces_card_id)
        )
        return cls(card_id, user_id, title, care_about, because, looks_like,
                   drift_looks_like, in_conflict, never_do, frankl_mode, color_key, now,
                   is_current=True, replaces_card_id=replaces_card_id)

    @classmethod
    def get_one(cls, user_id, card_id):
        """Single-partition, single-row lookup — cheap, unlike a bare card_id scan."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        if isinstance(card_id, str):
            card_id = uuid.UUID(card_id)
        rows = cassandra_session.execute(
            "SELECT * FROM value_cards WHERE user_id = %s AND card_id = %s",
            [user_id, card_id]
        )
        row = rows.one()
        return cls._row_to_card(row) if row else None

    @classmethod
    def get_for_user(cls, user_id, include_superseded=False):
        if isinstance(user_id, str):
            try:
                user_id = uuid.UUID(user_id)
            except ValueError:
                return []
        rows = cassandra_session.execute(
            "SELECT * FROM value_cards WHERE user_id = %s", [user_id]
        )
        cards = [cls._row_to_card(r) for r in rows]
        if not include_superseded:
            cards = [c for c in cards if c.is_current]
        return cards

    @classmethod
    def get_for_users(cls, user_ids):
        """{user_id: [current cards]} for many owners in one IN query (used by
        the list endpoints so every card on a page shares one round-trip)."""
        ids = []
        for u in user_ids or []:
            try:
                ids.append(u if isinstance(u, uuid.UUID) else uuid.UUID(str(u)))
            except (ValueError, TypeError):
                pass
        out = {u: [] for u in ids}
        if not ids:
            return out
        placeholders = ', '.join(['%s'] * len(ids))
        rows = cassandra_session.execute(
            f"SELECT * FROM value_cards WHERE user_id IN ({placeholders})", ids)
        for r in rows:
            c = cls._row_to_card(r)
            if c.is_current:
                out.setdefault(c.user_id, []).append(c)
        return out

    @classmethod
    def update(cls, user_id, card_id, data):
        """Edit a card without ever mutating its stored history: writes the
        edit as a brand-new row (new card_id, replaces_card_id=old id) and
        flips the old row's is_current to False in place. The old row's
        content is never touched — anything that already captured its values
        (e.g. a meaning-trail comment snapshot) keeps showing the wording as
        it was at the time. Returns the new current card, or None if no card
        with that id exists for this owner."""
        old = cls.get_one(user_id, card_id)
        if not old:
            return None

        merged = {
            'title': data.get('title', old.title),
            'care_about': data.get('care_about', old.care_about),
            'because': data.get('because', old.because),
            'looks_like': data.get('looks_like', old.looks_like),
            'drift_looks_like': data.get('drift_looks_like', old.drift_looks_like),
            'in_conflict': data.get('in_conflict', old.in_conflict),
            'never_do': data.get('never_do', old.never_do),
            'frankl_mode': data.get('frankl_mode', old.frankl_mode),
            'color_key': data.get('color_key', old.color_key),
        }
        new_card = cls.create(merged, old.user_id, replaces_card_id=old.card_id)

        cassandra_session.execute(
            "UPDATE value_cards SET is_current = %s WHERE user_id = %s AND card_id = %s",
            [False, old.user_id, old.card_id]
        )
        return new_card

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
