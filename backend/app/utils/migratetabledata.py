# File: ./backend/app/utils/migratetabledata.py
# Description: This script migrates user data from the old `users` table to the new `user_credentials` table by reusing the backend's session management setup.

import logging
import sys
from os.path import dirname, abspath

# Add the `backend/app` directory to the Python path
sys.path.insert(0, abspath(dirname(__file__) + '/../'))

from backend.app.routes.cassandra import CassandraSessionInterface  # Import after adjusting sys.path

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class TableMigrator:
    def __init__(self, cluster_nodes, keyspace):
        # Reuse the existing session interface for connecting to Cassandra
        self.cassandra_session_interface = CassandraSessionInterface(cluster_nodes=cluster_nodes, keyspace=keyspace, session_lifetime=None)
        self.cassandra_session = self.cassandra_session_interface.cassandra_session

    def migrate_users_to_user_credentials(self):
        try:
            # Select data from the old users table
            select_query = "SELECT user_id, email, password FROM users"
            rows = self.cassandra_session.execute(select_query)
            
            # Insert data into the new user_credentials table
            insert_query = """
                INSERT INTO user_credentials (user_id, email, password)
                VALUES (%s, %s, %s)
            """
            for row in rows:
                self.cassandra_session.execute(insert_query, (row.user_id, row.email, row.password))
                logger.info(f"Migrated user_id: {row.user_id} with email: {row.email}")

            logger.info("Migration completed successfully.")
        except Exception as e:
            logger.error(f"Error during migration: {e}")

if __name__ == '__main__':
    # Set up the migrator with your Cassandra cluster and keyspace
    cluster_nodes = ['143.42.34.42']  # Replace with your actual Cassandra nodes
    keyspace = 'logosphere'

    migrator = TableMigrator(cluster_nodes=cluster_nodes, keyspace=keyspace)
    migrator.migrate_users_to_user_credentials()
