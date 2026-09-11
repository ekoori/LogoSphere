# File: ./backend/app/db.py
# Description: The shared Cassandra connection for the whole app - and the
# thing that keeps it alive.
#
# Two Clusters, one Session each:
#   `session`     raw CQL for the hand-written models (named-tuple rows)
#   `orm_session` cqlengine (which requires dict rows)
# They are deliberately NOT two sessions on one Cluster. The driver ignores a
# "host down" signal while *any* session on the cluster still has an open pool
# to that host (Cluster.on_down, `_discount_down_events`). So when one session's
# only connection was defuncted by a heartbeat timeout, its pool shut itself
# down but the host was never marked down, no reconnector was started and the
# pool was never renewed: every query on that session failed with
# "ConnectionException('Pool is shutdown')" until the worker was restarted.
# That is what took production logins down on 2026-09-11 (the login route
# reports any exception as "Invalid email or password").
#
# Both clusters are configured in the driver's legacy (per-session) mode: the
# ORM session needs dict rows, and in execution-profile mode cqlengine would
# flip the cluster-wide default row factory instead.
#
# Belt and braces: `session` / `orm_session` are proxies. When a query fails
# because the connection is dead they rebuild both clusters (once, under a
# lock, with a short cooldown), re-point cqlengine at the new ORM session and
# retry the query once - so even a failure of the driver's own reconnection
# costs one failed query rather than an outage.
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
# Pin the protocol so a (re)connect doesn't go through the v66 -> v65 -> v5
# downgrade negotiation, each step of which defuncts a connection.
PROTOCOL_VERSION = int(os.environ.get('CASSANDRA_PROTOCOL_VERSION', '5'))

# Errors that mean "the connection is gone", as opposed to a bad query.
_DEAD = (NoHostAvailable, ConnectionException, ConnectionShutdown)
# Don't (re)attempt a rebuild more often than this - a burst of failing
# requests should share one rebuild, not trigger dozens.
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
    """Holds the live clusters + sessions; `generation` changes on every
    rebuild so concurrent failures can tell whether someone already rebuilt."""

    def __init__(self):
        self.raw_cluster = None
        self.orm_cluster = None
        self.raw = None
        self.orm = None
        self.generation = 0
        self.attempted_at = 0.0

    def build(self):
        self.attempted_at = time.time()
        raw_cluster = _new_cluster()
        orm_cluster = _new_cluster()
        try:
            raw = raw_cluster.connect(KEYSPACE)
            raw.default_timeout = REQUEST_TIMEOUT
            orm = orm_cluster.connect(KEYSPACE)
            orm.default_timeout = REQUEST_TIMEOUT
            orm.row_factory = dict_factory
        except Exception:
            # Leave the previous (possibly dead) connection in place; the next
            # failing query will try again once the cooldown has passed
            # (counted from the end of this attempt, which may have taken the
            # full connect timeout).
            for c in (raw_cluster, orm_cluster):
                c.shutdown()
            self.attempted_at = time.time()
            raise

        old = (self.raw_cluster, self.orm_cluster)
        self.raw_cluster, self.orm_cluster, self.raw, self.orm = raw_cluster, orm_cluster, raw, orm
        self.generation += 1

        # (Re)point the cqlengine ORM at the new session. Unregistering the
        # previous default connection also shuts its (old) cluster down.
        try:
            cqlengine_connection.unregister_connection('default')
        except Exception:
            logger.exception('Could not unregister the previous cqlengine connection')
        cqlengine_connection.set_session(orm)

        for c in old:
            if c is not None:
                try:
                    c.shutdown()   # idempotent; no-op if unregister already did it
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
    """Rebuild the connection after a dead-connection error. Returns True when
    the caller should retry its query on a fresh connection (either this call
    rebuilt it, or a concurrent request already had). Returns False - without
    waiting - when a rebuild is in progress on another request or one was
    attempted a moment ago: while Cassandra itself is unresponsive, every
    request must fail fast rather than queue up behind 10-second connects."""
    if not _lock.acquire(blocking=False):
        return False
    try:
        if _backend.generation != failed_generation:
            return True
        if time.time() - _backend.attempted_at < _REBUILD_COOLDOWN:
            return False
        logger.warning('Cassandra connection unusable (%s) - rebuilding', reason)
        _backend.build()
        return True
    finally:
        _lock.release()


class ResilientSession:
    """Proxy over a driver Session. `execute` retries once on a fresh
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
            if not rebuild(e, generation):
                raise
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
# The ORM's session (dict rows) - mostly for introspection; cqlengine models
# use the registered default connection, which is the same session.
orm_session = ResilientSession('orm')

# Connect eagerly so a misconfigured host fails at startup, not on first use.
_ensure()
