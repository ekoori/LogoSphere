# File: ./backend/app/models/openings.py
# Description: Openings service model — offers and requests in the gift economy.
# Class: Service — create() and get_all() backed by the logosphere.services table.

from cassandra.cluster import Cluster
import uuid
import logging
import os
from datetime import datetime

# Host(s) configurable via CASSANDRA_HOST (comma-separated), defaults to localhost.
CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(CASSANDRA_HOSTS)
cassandra_session = cluster.connect('logosphere')


class Service:
    def __init__(self, service_id, type, title, description, provider_id, provider_name,
                 sphere_id, sphere_name, status, values, likes=0, project_name=None, image_key=None,
                 cadence='single', accepted_by=None, accepted_by_name=None):
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

    def to_dict(self):
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

        logging.info(f'Creating service with service_id: {service_id}')
        query = """
        INSERT INTO services (service_id, type, title, description, provider_id, provider_name,
                              sphere_id, sphere_name, status, created_at, values, likes, project_name,
                              image_key, cadence)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cassandra_session.execute(query, (
            service_id, type_, title, description, provider_id, provider_name,
            sphere_id, sphere_name, status, datetime.utcnow(), values, 0, project_name, image_key, cadence
        ))
        return cls(service_id, type_, title, description, provider_id, provider_name,
                   sphere_id, sphere_name, status, values, 0, project_name, image_key, cadence)

    @classmethod
    def get_all(cls):
        rows = cassandra_session.execute("SELECT * FROM services")
        services = []
        for r in rows:
            services.append(cls(
                r.service_id, r.type, r.title, r.description, r.provider_id,
                r.provider_name, r.sphere_id, getattr(r, 'sphere_name', None),
                r.status, r.values, getattr(r, 'likes', 0),
                getattr(r, 'project_name', None), getattr(r, 'image_key', None),
                getattr(r, 'cadence', None), getattr(r, 'accepted_by', None),
                getattr(r, 'accepted_by_name', None),
            ))
        return services

    @classmethod
    def get_by_id(cls, service_id):
        row = cassandra_session.execute(
            "SELECT * FROM services WHERE service_id = %s", [service_id]
        ).one()
        if not row:
            return None
        return cls(
            row.service_id, row.type, row.title, row.description, row.provider_id,
            row.provider_name, row.sphere_id, getattr(row, 'sphere_name', None),
            row.status, row.values, getattr(row, 'likes', 0),
            getattr(row, 'project_name', None), getattr(row, 'image_key', None),
            getattr(row, 'cadence', None), getattr(row, 'accepted_by', None),
            getattr(row, 'accepted_by_name', None),
        )

    @classmethod
    def mark_accepted(cls, service_id, accepter_id, accepter_name):
        """Lock a 'single' cadence opening to the accepter. No-op for 'perpetual'."""
        cassandra_session.execute(
            "UPDATE services SET status = %s, accepted_by = %s, accepted_by_name = %s "
            "WHERE service_id = %s",
            ['Accepted', accepter_id, accepter_name, service_id]
        )
