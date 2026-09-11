# File: ./backend/app/db.py
# Description: The single shared Cassandra connection for the whole app - and
# the thing that keeps it alive.
#
# One Cluster, two Sessions on it: `session` for the hand-written CQL models
# (named-tuple rows) and `orm_session` for cqlengine (which needs dict rows).
# The cluster is configured in the driver's legacy (per-session) mode because
# cqlengine sets the row factory on the session it is given; with execution
# profiles that would flip the cluster-wide default and break every raw query.
#
# Resilience: under gevent the driver occasionally times out an idle-connection
# heartbeat, marks the (only) host down and shuts its pool - and in production
# it then never came back ("ConnectionException('Pool is shutdown')" on every
# query until the worker was restarted, which showed up to users as "wrong
# username/password"). `session` and `orm_session` are therefore proxies: when
# a query fails because the connection is dead they rebuild the whole cluster
# connection (once, under a lock) and retry the query, so a dead pool costs one
# failed query instead of an outage.
import logging
import os
import threading
import time

from cassandra.cluster import Cluster, NoHostAvailable
from cassandra.connection import ConnectionException, ConnectionShutdown
from cassandra.cqlengine import connection as cqlengine_connection
from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy, ConstantReconnectionPolicy
from cassandra.query import dict_factory

logger = logging.getLogger(__name__)

CASSANDRA_HOSTS = [h.strip() for h in os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',') if h.strip()]
KEYSPACE = os.environ.get('CASSANDRA_KEYSPACE', 'logosphere')
# Per-request timeout: above the driver's 10s default so a slow read/write
# (e.g. a large banner blob under memory pressure) waits rather than 500-ing.
REQUEST_TIMEOUT = float(os.environ.get('CASSANDRA_TIMEOUT', '30'))
# Pin the protocol so every (re)connect doesn't go through the v66 -> v65 -> v5
# downgrade negotiation, each step of which defuncts a connection.
PROTOCOL_VERSION = int(os.environ.get('CASSANDRA_PROTOCOL_VERSION', '5'))

# Errors that mean "the connection is gone", as opposed to a bad query.
_DEAD = (NoHostAvailable, ConnectionException, ConnectionShutdown)
# Don't rebuild more often than this - a burst of failing requests should share
# one rebuild, not trigger dozens.
_REBUILD_COOLDOWN = 2.0


def _new_cluster():
    return Cluster(
        CASSANDRA_HOSTS,
        load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy()),
        # Keep trying to bring a marked-down host back every second, forever
        # (the default exponential policy backs off to ten minutes).
        reconnection_policy=ConstantReconnectionPolicy(delay=1.0, max_attempts=None),
        protocol_version=PROTOCOL_VERSION,
        idle_heartbeat_interval=30,
        idle_heartbeat_timeout=60,
        connect_timeout=10,
        control_connection_timeout=10,
    )


class _Backend:
    """Holds the live cluster + sessions; `generation` changes on every rebuild
    so concurrent failures can tell whether someone already rebuilt."""

    def __init__(self):
        self.cluster = None
        self.raw = None
        self.orm = None
        self.generation = 0
        self.built_at = 0.0

    def build(self):
        cluster = _new_cluster()
        try:
            raw = cluster.connect(KEYSPACE)
            raw.default_timeout = REQUEST_TIMEOUT
            orm = cluster.connect(KEYSPACE)
            orm.default_timeout = REQUEST_TIMEOUT
            orm.row_factory = dict_factory
        except Exception:
            # Leave the previous (possibly dead) connection in place; the next
            # failing query will try again once the cooldown has passed.
            cluster.shutdown()
            raise

        old = self.cluster
        self.cluster, self.raw, self.orm = cluster, raw, orm
        self.generation += 1
        self.built_at = time.time()

        # (Re)point the cqlengine ORM at the new session. Unregistering the
        # previous default connection also shuts its (old) cluster down.
        try:
            cqlengine_connection.unregister_connection('default')
        except Exception:
            logger.exception('Could not unregister the previous cqlengine connection')
        cqlengine_connection.set_session(orm)

        if old is not None:
            try:
                old.shutdown()   # idempotent; no-op if unregister already did it
            except Exception:
                pass
        logger.info('Cassandra connection ready (generation %d): hosts=%s keyspace=%s protocol=v%s',
                    self.generation, CASSANDRA_HOSTS, KEYSPACE, PROTOCOL_VERSION)


_backend = _Backend()
_lock = threading.RLock()


def _ensure():
    if _backend.raw is None:
        with _lock:
            if _backend.raw is None:
                _backend.build()
    return _backend


def rebuild(reason, failed_generation):
    """Rebuild the cluster connection after a dead-connection error, unless a
    concurrent request already did (or one was done a moment ago)."""
    with _lock:
        if _backend.generation != failed_generation:
            return
        if time.time() - _backend.built_at < _REBUILD_COOLDOWN:
            return
        logger.warning('Cassandra connection unusable (%s) - rebuilding', reason)
        _backend.build()


class ResilientSession:
    """Proxy over a driver Session. `execute` retries once on a fresh cluster
    connection when the current one is dead; everything else delegates."""

    def __init__(self, which):
        self._which = which

    def _target(self):
        return getattr(_ensure(), self._which)

    def execute(self, *args, **kwargs):
        backend = _ensure()
        generation = backend.generation
        try:
            return getattr(backend, self._which).execute(*args, **kwargs)
        except _DEAD as e:
            rebuild(e, generation)
            return getattr(_ensure(), self._which).execute(*args, **kwargs)

    def execute_async(self, *args, **kwargs):
        return self._target().execute_async(*args, **kwargs)

    def prepare(self, *args, **kwargs):
        # Prepared statements are bound to a cluster; callers should prefer
        # plain parameterised queries so a rebuild can't strand them.
        return self._target().prepare(*args, **kwargs)

    @property
    def default_timeout(self):
        return self._target().default_timeout

    @default_timeout.setter
    def default_timeout(self, value):
        self._target().default_timeout = value

    @property
    def cluster(self):
        return self._target().cluster

    @property
    def generation(self):
        return _ensure().generation

    def __getattr__(self, name):
        return getattr(self._target(), name)


# Raw session for the hand-written CQL models (named-tuple rows).
session = ResilientSession('raw')
# The ORM's own session (dict rows) - mostly for introspection; cqlengine
# models use the registered default connection.
orm_session = ResilientSession('orm')

# Connect eagerly so a misconfigured host fails at startup, not on first use.
_ensure()
