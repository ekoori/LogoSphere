# The shared connection must survive its cluster dying: production once sat
# with "Pool is shutdown" on every raw query until a restart. Simulate that by
# shutting the raw cluster down underneath the proxies.
import pytest


def test_session_rebuilds_after_the_cluster_dies(app, db):
    from app import db as dbmod
    from cassandra.cqlengine import connection as cqlengine_connection
    before = dbmod._backend.generation
    old_orm = dbmod._backend.orm
    dbmod._backend.attempted_at = 0.0      # defeat the rebuild cooldown for the test
    dbmod._backend.raw_cluster.shutdown()  # the pool is now dead, like the outage

    rows = list(db.execute('SELECT sphere_id FROM spheres LIMIT 1'))   # proxy rebuilds + retries
    assert rows
    assert dbmod._backend.generation == before + 1

    # both clusters were replaced and cqlengine re-pointed at the new ORM session
    assert dbmod._backend.orm is not old_orm
    assert cqlengine_connection.get_session() is dbmod._backend.orm
    from app.models.meaning_trail import MeaningTrail
    assert isinstance(list(MeaningTrail.objects.all().limit(1)), list)

    # and the Flask session interface (plain queries, no stale prepared statements)
    r = app.test_client().post('/api/login', json={'email': 'joe.rogan@example.com', 'password': 'Joe'})
    assert r.status_code == 200


def test_raw_and_orm_sessions_do_not_share_a_cluster(db):
    # Two sessions on one Cluster is exactly the configuration in which the
    # driver never recovers a dead pool (see the note at the top of app/db.py).
    from app import db as dbmod
    assert dbmod._backend.raw.cluster is not dbmod._backend.orm.cluster
    assert len(dbmod._backend.raw.cluster.sessions) == 1
    assert len(dbmod._backend.orm.cluster.sessions) == 1


def test_bad_queries_are_not_mistaken_for_dead_connections(db):
    from app import db as dbmod
    from cassandra import InvalidRequest
    before = dbmod._backend.generation
    with pytest.raises(InvalidRequest):
        db.execute('SELECT nope FROM definitely_not_a_table')
    assert dbmod._backend.generation == before     # no rebuild for a plain error
