# Exchanges found by id, and a member's spheres, from their lookup tables (docs/2026-11-23-cassandra-audit.md,
# items 2 and 3): the same answers as reading whole tables, kept by joining and leaving, put back by repair.
import uuid

import pytest

from app.db import session
from app.models.meaning_trail import MeaningTrail
from app.models.spheres import Sphere
from test_api_sharing import exchange_between, post_opening, two  # noqa: F401


def by_reading_every_sphere(user_id):
    return {r.sphere_id for r in session.execute('SELECT sphere_id, participants FROM spheres')
            if r.participants and user_id in r.participants}


def test_a_members_spheres_are_what_reading_every_sphere_says(two, api):
    for uid in (two['ada'].id, two['ben'].id, two['cy'].id, uuid.UUID(api.uid('marie')), uuid.UUID(api.uid('admin'))):
        assert Sphere.member_sphere_ids(uid) == by_reading_every_sphere(uid), uid


def test_joining_and_leaving_count_at_once(two):
    ada, second = two['ada'], two['second']          # Ada joined Cy's sphere in the fixture
    assert second in Sphere.member_sphere_ids(ada.id)
    assert ada.post(f'/api/spheres/{second}/leave')[0] == 200
    assert second not in Sphere.member_sphere_ids(ada.id)
    assert ada.post(f'/api/spheres/{second}/join')[0] in (200, 201)
    assert second in Sphere.member_sphere_ids(ada.id)


def test_a_lost_membership_row_shuts_out_until_repair(db, people):
    ada, sphere = people['ada'], people['sphere']
    db.execute('DELETE FROM memberships_by_member WHERE user_id = %s', [ada.id])
    assert sphere not in Sphere.member_sphere_ids(ada.id)            # never the other way round
    Sphere.repair_memberships()
    assert sphere in Sphere.member_sphere_ids(ada.id)


@pytest.fixture
def exchange(db, people):
    ada, ben = people['ada'], people['ben']
    xid = exchange_between(ada, ben, post_opening(ada, people['sphere'], title='Lookup test ladder'))
    yield xid
    db.execute('DELETE FROM meaning_trail WHERE user_id = %s AND exchange_id = %s', [ada.id, uuid.UUID(xid)])
    db.execute('DELETE FROM exchanges_by_id WHERE exchange_id = %s', [uuid.UUID(xid)])


def test_an_exchange_is_found_by_its_id(db, people, exchange):
    ada, ben = people['ada'], people['ben']
    row = MeaningTrail.row_of(exchange)
    assert row is not None and row.user_id == ada.id
    assert MeaningTrail.exists(exchange) and not MeaningTrail.is_finished(exchange)
    assert MeaningTrail.row_of(uuid.uuid4()) is None and MeaningTrail.row_of('not-an-id') is None
    assert ben.get(f'/api/exchange/{exchange}')[0] == 200
    assert people['cy'].get(f'/api/exchange/{exchange}')[0] == 404          # still only for who may see it


def test_a_lost_exchange_row_is_put_back(db, exchange):
    db.execute('DELETE FROM exchanges_by_id WHERE exchange_id = %s', [uuid.UUID(exchange)])
    assert MeaningTrail.row_of(exchange) is None
    MeaningTrail.repair_lookup()
    assert MeaningTrail.row_of(exchange) is not None
