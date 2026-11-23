# The openings list a page at a time, from the openings feed (app/utils/openings_feed.py): the same openings as the
# whole list, newest first, each once, filtered on the server. The people are conftest's: Ada and Ben share Ada's
# sphere; Cy is outside it, with a sphere of Cy's own that Ada joins (test_api_sharing's `two`).
import uuid

import pytest

from app.utils import openings_feed
from test_api_sharing import exchange_between, post_opening, two  # noqa: F401


def every_page(person, size=5, **filters):
    seen, before = [], None
    for _ in range(200):
        query = {'limit': size, **filters, **({'before': before} if before else {})}
        status, body = person.get('/api/openings?' + '&'.join(f'{k}={v}' for k, v in query.items()))
        assert status == 200, body
        seen += body['openings']
        before = body['next']
        if not before:
            return seen
    raise AssertionError('the pages never ended')


def ids(openings):
    return [o['id'] for o in openings]


def test_the_pages_hold_the_whole_list(people):
    for who in (people['ada'], people['cy']):
        post_opening(who, people['sphere'] if who is people['ada'] else None, title='Feed test kettle')
        whole = ids(who.get('/api/openings')[1])
        paged = every_page(who)
        assert sorted(ids(paged)) == sorted(whole)
        assert len(set(ids(paged))) == len(paged)                           # each once
        made = [o.get('created_at') or '' for o in paged]
        assert made == sorted(made, reverse=True)                            # newest first


def test_shared_shows_in_the_other_sphere_once(two):
    ada, cy, second = two['ada'], two['cy'], two['second']
    oid = post_opening(ada, two['sphere'], title='Feed test shared ladder')
    assert oid not in ids(every_page(cy))
    assert ada.post(f'/api/openings/{oid}/spheres', {'sphere_ids': [str(second)]})[0] == 200
    assert ids(every_page(cy)).count(oid) == 1
    assert ids(every_page(ada)).count(oid) == 1                              # in two of Ada's spheres, still once
    assert ada.post(f'/api/openings/{oid}/spheres', {'sphere_ids': []})[0] == 200
    assert oid not in ids(every_page(cy))


def test_withdrawn_or_taken_up_leaves_the_list(db, people):
    ada, ben = people['ada'], people['ben']
    single = post_opening(ada, people['sphere'], title='Feed test single')
    gone = post_opening(ada, people['sphere'], title='Feed test withdrawn')
    assert {single, gone} <= set(ids(every_page(ben)))
    xid = exchange_between(ada, ben, single)
    assert ada.post(f'/api/openings/{gone}/cancel')[0] == 200
    listed = ids(every_page(ben))
    assert single not in listed and gone not in listed
    assert ids(every_page(ben)) == [i for i in ids(ben.get('/api/openings')[1]) if i in set(listed)]
    db.execute('DELETE FROM meaning_trail WHERE user_id = %s AND exchange_id = %s', [ada.id, uuid.UUID(xid)])


def test_filters_on_the_server(people):
    ada, ben, sphere = people['ada'], people['ben'], people['sphere']
    offer = post_opening(ada, sphere, title='Feed test offer of quinces')
    need = post_opening(ada, sphere, title='Feed test need of a wheelbarrow', type='need')
    loan = post_opening(ada, sphere, title='Feed test loan of a drill', borrow=True)
    assert need in ids(every_page(ben, type='need')) and offer not in ids(every_page(ben, type='need'))
    assert ids(every_page(ben, loans=1)) == [loan] or loan in ids(every_page(ben, loans=1))
    assert offer not in ids(every_page(ben, loans=1))
    assert ids(every_page(ben, q='quinces')) == [offer]
    assert set(ids(every_page(ben, sphere=sphere))) >= {offer, need, loan}
    assert every_page(people['cy'], sphere=sphere) == []                     # not a sphere of Cy's
    assert ben.get('/api/openings?limit=5&before=not-a-cursor')[0] == 400
    assert ben.get('/api/openings?limit=five')[0] == 400


def test_repair_puts_back_what_was_lost(db, people):
    ada, ben = people['ada'], people['ben']
    oid = post_opening(ada, people['sphere'], title='Feed test lost and found')
    for r in db.execute('SELECT place, created_at FROM opening_feed_rows WHERE service_id = %s', [uuid.UUID(oid)]):
        db.execute('DELETE FROM openings_feed WHERE place = %s AND created_at = %s AND service_id = %s',
                   [r.place, r.created_at, uuid.UUID(oid)])
    db.execute('DELETE FROM opening_feed_rows WHERE service_id = %s', [uuid.UUID(oid)])
    assert oid not in ids(every_page(ben))
    openings_feed.repair()
    assert oid in ids(every_page(ben))


@pytest.fixture(autouse=True)
def feed_kept_tidy():
    yield
    openings_feed.repair()          # rows of openings the people fixture removes go with them
