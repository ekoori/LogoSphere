# File: ./backend/app/db.py
# Description: The single shared Cassandra connection for the whole app.
#
# Every model used to open its own Cluster()/Session at import time (11 of them),
# each with its own connection pool, control connection and heartbeat. They all
# pointed at the same keyspace, so this module now owns the one Cluster and hands
# out the sessions; models import `session` from here.
#
# Two sessions, one cluster: the hand-written CQL models expect named-tuple rows,
# while cqlengine (MeaningTrail / Likes / Notification) needs dict rows and sets
# that on the session it is given. The cluster is deliberately configured in the
# driver's *legacy* (per-session) mode: with execution profiles, cqlengine would
# flip the row factory on the cluster-wide default profile and break every raw
# query in the process.
import logging
import os

from cassandra.cluster import Cluster
from cassandra.cqlengine import connection as cqlengine_connection
from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy

logger = logging.getLogger(__name__)

CASSANDRA_HOSTS = [h.strip() for h in os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',') if h.strip()]
KEYSPACE = os.environ.get('CASSANDRA_KEYSPACE', 'logosphere')
# Per-request timeout: above the driver's 10s default so a slow read/write
# (e.g. a large banner blob under memory pressure) waits rather than 500-ing.
REQUEST_TIMEOUT = float(os.environ.get('CASSANDRA_TIMEOUT', '30'))

cluster = Cluster(
    CASSANDRA_HOSTS,
    load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy()),
)

# Raw session for the hand-written CQL models (named-tuple rows).
session = cluster.connect(KEYSPACE)
session.default_timeout = REQUEST_TIMEOUT

# The ORM's own session on the same cluster (cqlengine switches its row_factory
# to dict_factory; that stays confined to this session in legacy mode).
orm_session = cluster.connect(KEYSPACE)
orm_session.default_timeout = REQUEST_TIMEOUT
cqlengine_connection.set_session(orm_session)
cqlengine_connection.default_keyspace = KEYSPACE

logger.info('Cassandra sessions ready: hosts=%s keyspace=%s', CASSANDRA_HOSTS, KEYSPACE)
