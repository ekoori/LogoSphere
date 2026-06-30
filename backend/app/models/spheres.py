from cassandra.cluster import Cluster
import uuid
import logging
import os
from datetime import datetime
import base64

# Set up Cassandra session
# Host(s) configurable via CASSANDRA_HOST (comma-separated), defaults to localhost.
CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(CASSANDRA_HOSTS)
cassandra_session = cluster.connect('logosphere')

class Sphere:
    def __init__(self, sphere_id, name, description, meaning_graph, location, image, admin1, participants, alliances, projects, values):
        self.sphere_id = sphere_id
        self.name = name
        self.description = description
        self.meaning_graph = meaning_graph
        self.location = location
        self.image = image
        self.admin1 = admin1
        self.participants = participants
        self.alliances = alliances
        self.projects = projects
        self.values = values

    def to_dict(self):
        return {
            'sphere_id': str(self.sphere_id),
            'name': self.name,
            'description': self.description,
            'meaning_graph': self.meaning_graph,
            'location': self.location,
            'image': base64.b64encode(self.image).decode('utf-8') if self.image else None,
            'admin1': str(self.admin1),
            'participants': self.participants,
            'alliances': self.alliances,
            'projects': self.projects,
            'values': self.values
        }

    @classmethod
    def create(cls, data, admin1):
        sphere_id = uuid.uuid4()
        name = data['name']
        description = data['description']
        meaning_graph = data['meaning_graph']
        location = data['location']
        image = data['image']
        participants = [admin1]
        alliances = data.get('alliances', [])
        projects = data.get('projects', [])
        values = data.get('values', [])
        logging.info(f'Creating sphere with sphere_id: {sphere_id}')

        query = """
        INSERT INTO spheres (sphere_id, name, description, meaning_graph, location, image, admin1, participants, alliances, projects, values, created_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        cassandra_session.execute(query, (sphere_id, name, description, meaning_graph, location, image, admin1, participants, alliances, projects, values, datetime.utcnow()))

        return cls(sphere_id, name, description, meaning_graph, location, image, admin1, participants, alliances, projects, values)
