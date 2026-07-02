# File: ./backend/app/models/openings.py
# Description: Openings service model — offers and requests in the gift economy.
# Class: Service — create() and get_all() backed by the logosphere.services table.

from cassandra.cluster import Cluster
import uuid
import logging
import os
import base64
from datetime import datetime

# Host(s) configurable via CASSANDRA_HOST (comma-separated), defaults to localhost.
CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(CASSANDRA_HOSTS)
cassandra_session = cluster.connect('logosphere')


class Service:
    def __init__(self, service_id, type, title, description, provider_id, provider_name,
                 sphere_id, sphere_name, status, values, likes=0, project_name=None, image_key=None,
                 cadence='single', accepted_by=None, accepted_by_name=None, created_at=None,
                 accepted_at=None, in_progress_at=None, completed_at=None, image=None,
                 acting_user_id=None, acting_user_name=None):
        self.service_id = service_id
        self.type = type
        self.title = title
        self.description = description
        self.provider_id = provider_id
        self.provider_name = provider_name
        self.sphere_id = sphere_id
        self.sphere_name = sphere_name
        self.status = status
        self.values = values
        self.likes = likes or 0
        self.project_name = project_name
        self.image_key = image_key
        self.cadence = cadence or 'single'
        self.accepted_by = accepted_by
        self.accepted_by_name = accepted_by_name
        self.created_at = created_at
        self.accepted_at = accepted_at
        self.in_progress_at = in_progress_at
        self.completed_at = completed_at
        self.image = image
        # When an entity (sphere/alliance/project) is the provider, these name
        # the human who actually posted it — "Joe on behalf of <Entity>".
        self.acting_user_id = acting_user_id
        self.acting_user_name = acting_user_name

    def to_dict(self):
        def _iso(v):
            return v.isoformat() if v else None
        return {
            'service_id': str(self.service_id),
            'id': str(self.service_id),
            'type': self.type,
            'title': self.title,
            'description': self.description,
            'provider': self.provider_name,
            'provider_id': str(self.provider_id) if self.provider_id else None,
            'sphere_id': str(self.sphere_id) if self.sphere_id else None,
            'spheres': [self.sphere_name] if self.sphere_name else [],
            'status': self.status,
            'values': self.values or [],
            'likes': self.likes or 0,
            'project_name': self.project_name,
            'image_key': self.image_key,
            'cadence': self.cadence or 'single',
            'accepted_by': str(self.accepted_by) if self.accepted_by else None,
            'accepted_by_name': self.accepted_by_name,
            'created_at': _iso(self.created_at),
            'accepted_at': _iso(self.accepted_at),
            'in_progress_at': _iso(self.in_progress_at),
            'completed_at': _iso(self.completed_at),
            'image': base64.b64encode(self.image).decode('utf-8') if self.image else None,
            'acting_user_id': str(self.acting_user_id) if self.acting_user_id else None,
            'acting_user': self.acting_user_name,
        }

    @classmethod
    def create(cls, data, provider_id):
        service_id = uuid.uuid4()
        type_ = data.get('type', 'offer')
        title = data['title']
        description = data.get('description', '')
        provider_name = data.get('provider_name', '')
        sphere_id = data.get('sphere_id')
        if isinstance(sphere_id, str) and sphere_id:
            sphere_id = uuid.UUID(sphere_id)
        else:
            sphere_id = None
        sphere_name = data.get('sphere_name')
        status = data.get('status', 'Posted')
        values = data.get('values', [])
        project_name = data.get('project_name')
        image_key = data.get('image_key')
        cadence = data.get('cadence') if data.get('cadence') in ('single', 'perpetual') else 'single'
        acting_user_id = data.get('acting_user_id')
        if isinstance(acting_user_id, str) and acting_user_id:
            acting_user_id = uuid.UUID(acting_user_id)
        elif not isinstance(acting_user_id, uuid.UUID):
            acting_user_id = None
        acting_user_name = data.get('acting_user_name')

        # Look up provider name from users table if not supplied by the client.
        if not provider_name:
            try:
                row = cassandra_session.execute(
                    "SELECT name, surname FROM users WHERE user_id = %s", [provider_id]
                ).one()
                if row:
                    provider_name = f"{row.name or ''} {row.surname or ''}".strip()
            except Exception as e:
                logging.warning(f'Could not look up provider name: {e}')

        created_at = datetime.utcnow()
        logging.info(f'Creating service with service_id: {service_id}')
        query = """
        INSERT INTO services (service_id, type, title, description, provider_id, provider_name,
                              sphere_id, sphere_name, status, created_at, values, likes, project_name,
                              image_key, cadence, acting_user_id, acting_user_name)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cassandra_session.execute(query, (
            service_id, type_, title, description, provider_id, provider_name,
            sphere_id, sphere_name, status, created_at, values, 0, project_name, image_key, cadence,
            acting_user_id, acting_user_name
        ))
        return cls(service_id, type_, title, description, provider_id, provider_name,
                   sphere_id, sphere_name, status, values, 0, project_name, image_key, cadence,
                   created_at=created_at, acting_user_id=acting_user_id, acting_user_name=acting_user_name)

    @classmethod
    def _from_row(cls, r):
        return cls(
            r.service_id, r.type, r.title, r.description, r.provider_id,
            r.provider_name, r.sphere_id, getattr(r, 'sphere_name', None),
            r.status, r.values, getattr(r, 'likes', 0),
            getattr(r, 'project_name', None), getattr(r, 'image_key', None),
            getattr(r, 'cadence', None), getattr(r, 'accepted_by', None),
            getattr(r, 'accepted_by_name', None), getattr(r, 'created_at', None),
            getattr(r, 'accepted_at', None), getattr(r, 'in_progress_at', None),
            getattr(r, 'completed_at', None), getattr(r, 'image', None),
            getattr(r, 'acting_user_id', None), getattr(r, 'acting_user_name', None),
        )

    @classmethod
    def get_all(cls):
        rows = cassandra_session.execute("SELECT * FROM services")
        return [cls._from_row(r) for r in rows]

    @classmethod
    def get_by_id(cls, service_id):
        row = cassandra_session.execute(
            "SELECT * FROM services WHERE service_id = %s", [service_id]
        ).one()
        return cls._from_row(row) if row else None

    @classmethod
    def set_image(cls, service_id, image_bytes):
        cassandra_session.execute(
            "UPDATE services SET image = %s WHERE service_id = %s",
            [image_bytes, service_id]
        )

    @classmethod
    def mark_accepted(cls, service_id, accepter_id, accepter_name):
        """Lock a 'single' cadence opening to the accepter (display + prevents
        other accepts). No-op for 'perpetual'. Records when the Accepted phase
        of the progress bar was reached."""
        cassandra_session.execute(
            "UPDATE services SET status = %s, accepted_by = %s, accepted_by_name = %s, "
            "accepted_at = %s WHERE service_id = %s",
            ['Accepted', accepter_id, accepter_name, datetime.utcnow(), service_id]
        )

    @classmethod
    def set_status(cls, service_id, status):
        """Set status and, for the phases the progress bar tracks a date for,
        stamp when that phase was reached."""
        phase_column = {'In Progress': 'in_progress_at', 'Completed': 'completed_at'}.get(status)
        if phase_column:
            cassandra_session.execute(
                f"UPDATE services SET status = %s, {phase_column} = %s WHERE service_id = %s",
                [status, datetime.utcnow(), service_id]
            )
        else:
            cassandra_session.execute(
                "UPDATE services SET status = %s WHERE service_id = %s", [status, service_id]
            )

    # ── Acceptances (two-step: accept → provider confirms → exchange) ──────────
    @classmethod
    def record_acceptance(cls, service_id, accepter_id, accepter_name):
        """Register a pending acceptance. Idempotent per (service, accepter)."""
        cassandra_session.execute(
            "INSERT INTO opening_acceptances "
            "(service_id, accepter_id, accepter_name, status, created_at) "
            "VALUES (%s, %s, %s, 'pending', %s)",
            [service_id, accepter_id, accepter_name, datetime.utcnow()]
        )

    @classmethod
    def get_acceptance(cls, service_id, accepter_id):
        row = cassandra_session.execute(
            "SELECT accepter_id, accepter_name, status, exchange_id, created_at "
            "FROM opening_acceptances WHERE service_id = %s AND accepter_id = %s",
            [service_id, accepter_id]
        ).one()
        if not row:
            return None
        return {
            'accepter_id': str(row.accepter_id),
            'accepter_name': row.accepter_name,
            'status': row.status,
            'exchange_id': str(row.exchange_id) if row.exchange_id else None,
            'created_at': row.created_at,
        }

    @classmethod
    def acceptances(cls, service_id, status=None):
        rows = cassandra_session.execute(
            "SELECT accepter_id, accepter_name, status, exchange_id, created_at "
            "FROM opening_acceptances WHERE service_id = %s", [service_id]
        )
        out = []
        for r in rows:
            if status and r.status != status:
                continue
            out.append({
                'accepter_id': str(r.accepter_id),
                'accepter_name': r.accepter_name,
                'status': r.status,
                'exchange_id': str(r.exchange_id) if r.exchange_id else None,
                'created_at': r.created_at,
            })
        return out

    @classmethod
    def activity_summary(cls, service_id, provider_id):
        """For a 'perpetual' opening, aggregate the many acceptances it has
        gathered into one activation date per progress-bar phase:
        - accepted:    latest acceptance of any status (someone said yes)
        - in_progress: latest CONFIRMED acceptance (an exchange is underway)
        - completed:   latest confirmed acceptance whose spawned exchange has
                       reached a finished/receipted state (approximated by that
                       exchange's own timestamps, since meaning_trail doesn't
                       track a dedicated "became Finished" moment)
        `provider_id` is the opening's provider = the initiator of every exchange
        it spawned, letting the completion lookup be a full-PK point read.
        Returns None fields where that phase has never been reached."""
        accs = cls.acceptances(service_id)
        confirmed = [a for a in accs if a['status'] == 'confirmed' and a['exchange_id']]

        accepted_last = max((a['created_at'] for a in accs if a['created_at']), default=None)
        in_progress_last = max((a['created_at'] for a in confirmed if a['created_at']), default=None)

        completed_last = None
        if confirmed:
            from app.models.meaning_trail import MeaningTrail
            for a in confirmed:
                info = MeaningTrail.get_completion_signal(a['exchange_id'], provider_id)
                if info and (completed_last is None or info > completed_last):
                    completed_last = info

        return {
            'accepted_count': len(accs),
            'accepted_last_at': accepted_last.isoformat() if accepted_last else None,
            'in_progress_count': len(confirmed),
            'in_progress_last_at': in_progress_last.isoformat() if in_progress_last else None,
            'completed_last_at': completed_last.isoformat() if completed_last else None,
        }

    @classmethod
    def mark_confirmed(cls, service_id, accepter_id, exchange_id):
        cassandra_session.execute(
            "UPDATE opening_acceptances SET status = 'confirmed', exchange_id = %s "
            "WHERE service_id = %s AND accepter_id = %s",
            [exchange_id, service_id, accepter_id]
        )

    @classmethod
    def remove_acceptance(cls, service_id, accepter_id):
        cassandra_session.execute(
            "DELETE FROM opening_acceptances WHERE service_id = %s AND accepter_id = %s",
            [service_id, accepter_id]
        )

    @classmethod
    def reopen(cls, service_id):
        """Clear the single-opening lock so others may accept it again."""
        cassandra_session.execute(
            "UPDATE services SET status = 'Posted', accepted_by = null, accepted_by_name = null "
            "WHERE service_id = %s", [service_id]
        )

    # ── Likes ────────────────────────────────────────────────────────────────
    # Per-user rows in opening_likes; count = COUNT(*) per service_id partition.
    @classmethod
    def like_count(cls, service_id):
        row = cassandra_session.execute(
            "SELECT COUNT(*) AS n FROM opening_likes WHERE service_id = %s", [service_id]
        ).one()
        return int(row.n) if row else 0

    @classmethod
    def is_liked_by(cls, service_id, user_id):
        row = cassandra_session.execute(
            "SELECT user_id FROM opening_likes WHERE service_id = %s AND user_id = %s",
            [service_id, user_id]
        ).one()
        return row is not None

    @classmethod
    def toggle_like(cls, service_id, user_id):
        """Add the like if absent, remove it if present. Returns (liked, count)."""
        if cls.is_liked_by(service_id, user_id):
            cassandra_session.execute(
                "DELETE FROM opening_likes WHERE service_id = %s AND user_id = %s",
                [service_id, user_id]
            )
            liked = False
        else:
            cassandra_session.execute(
                "INSERT INTO opening_likes (service_id, user_id) VALUES (%s, %s)",
                [service_id, user_id]
            )
            liked = True
        return liked, cls.like_count(service_id)
