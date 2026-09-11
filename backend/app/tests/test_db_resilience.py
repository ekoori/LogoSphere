# The shared connection must survive its cluster dying: production once sat
# with "Pool is shutdown" on every query until a restart. Simulate exactly
# that by shutting the live cluster down underneath the proxies.


def test_session_rebuilds_after_the_cluster_dies(app, db):
    from app import db as dbmod
    before = dbmod._backend.generation
    dbmod._backend.built_at = 0.0          # defeat the rebuild cooldown for the test
    dbmod._backend.cluster.shutdown()      # the pool is now dead, like the outage

    rows = list(db.execute('SELECT sphere_id FROM spheres LIMIT 1'))   # proxy rebuilds + retries
    assert rows
    assert dbmod._backend.generation == before + 1

    # cqlengine models were re-pointed at the new session as well
    from app.models.meaning_trail import MeaningTrail
    from cassandra.cqlengine import connection as cqlengine_connection
    assert cqlengine_connection.get_session() is dbmod._backend.orm
    assert isinstance(list(MeaningTrail.objects.all().limit(1)), list)

    # and the Flask session interface (plain queries, no stale prepared statements)
    r = app.test_client().post('/api/login', json={'email': 'joe.rogan@example.com', 'password': 'Joe'})
    assert r.status_code == 200


def test_bad_queries_are_not_mistaken_for_dead_connections(app, db):
    from app import db as dbmod
    from cassandra import InvalidRequest
    import pytest
    before = dbmod._backend.generation
    with pytest.raises(InvalidRequest):
        db.execute('SELECT nope FROM definitely_not_a_table')
    assert dbmod._backend.generation == before     # no rebuild for a plain error
