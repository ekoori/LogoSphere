# Who may see and do what across sphere boundaries (app/utils/access.py).
# Each test is a hole that was open: the Privacy page promises that a sphere's
# openings, exchanges, receipts and people are for its members.
import io
import uuid

import pytest

from conftest import PNG_1PX, RIVERSIDE

CARD = {'title': 'Access test value', 'care_about': 'Keeping to the rules', 'frankl_mode': 'creative'}


@pytest.fixture
def private_sphere(api, db):
    """A private, non-demo sphere founded by the throwaway admin."""
    status, s = api.post('/api/spheres', who='admin', json={'name': 'Access test sphere (delete me)', 'description': 'x'})
    assert status == 201, s
    sid = s['sphere_id']
    yield sid
    db.execute('DELETE FROM spheres WHERE sphere_id = %s', [uuid.UUID(sid)])
    db.execute('DELETE FROM value_cards WHERE user_id = %s', [uuid.UUID(sid)])


@pytest.fixture
def riverside_opening(api, db):
    status, body = api.post('/api/openings', who='david', json={
        'type': 'offer', 'title': 'Access test opening', 'sphere_id': RIVERSIDE, 'sphere_name': 'Riverside Commons'})
    assert status == 201, body
    sid = body['service_id']
    yield sid
    db.execute('DELETE FROM services WHERE service_id = %s', [uuid.UUID(sid)])
    db.execute('DELETE FROM opening_acceptances WHERE service_id = %s', [uuid.UUID(sid)])
    db.execute('DELETE FROM opening_likes WHERE service_id = %s', [uuid.UUID(sid)])


@pytest.fixture
def riverside_exchange(api, db, riverside_opening):
    """David's Riverside opening, accepted by Marie and confirmed."""
    marie = api.uid('marie')
    assert api.post(f'/api/openings/{riverside_opening}/accept', who='marie', json={})[0] == 200
    status, body = api.post(f'/api/openings/{riverside_opening}/confirm', who='david', json={'accepter_id': marie})
    assert status == 200, body
    xid = body['exchange_id']
    yield xid
    x = uuid.UUID(xid)
    db.execute('DELETE FROM meaning_trail WHERE user_id = %s AND exchange_id = %s', [uuid.UUID(api.uid('david')), x])
    db.execute('DELETE FROM receipt_photos WHERE exchange_id = %s', [x])


def signed_out(app, path):
    """A visitor. (The shared client keeps the cookie of the last sign-in.)"""
    r = app.test_client().get(path)
    return r.status_code, r.get_json(silent=True)


# -- Trails --------------------------------------------------------------------
def test_a_trail_hides_exchanges_from_spheres_you_are_not_in(api, riverside_exchange):
    for owner in ('david', 'marie'):
        body = {'userId': api.uid(owner)}
        _, outsider = api.post('/api/meaning_trail', who='elon', json=body)      # Elon isn't in Riverside
        assert riverside_exchange not in [r['exchange_id'] for r in outsider], owner
        _, member = api.post('/api/meaning_trail', who='joe', json=body)
        assert riverside_exchange in [r['exchange_id'] for r in member], owner
    _, own = api.get('/api/meaning_trail', who='marie')
    assert riverside_exchange in [r['exchange_id'] for r in own]


# -- Openings ------------------------------------------------------------------
def test_you_post_only_into_your_spheres(api, db):
    status, body = api.post('/api/openings', who='elon', json={
        'type': 'offer', 'title': 'Intruder', 'sphere_id': RIVERSIDE, 'sphere_name': 'Riverside Commons'})
    if status == 201:
        db.execute('DELETE FROM services WHERE service_id = %s', [uuid.UUID(body['service_id'])])
    assert status == 403, body
    status, body = api.post('/api/openings', who='marie', json={
        'type': 'offer', 'title': 'Nowhere', 'sphere_id': str(uuid.uuid4())})
    if status == 201:
        db.execute('DELETE FROM services WHERE service_id = %s', [uuid.UUID(body['service_id'])])
    assert status == 404, body


def test_the_server_names_the_sphere_and_sets_the_status(api, db):
    status, body = api.post('/api/openings', who='marie', json={
        'type': 'need', 'title': 'Spoof', 'sphere_id': RIVERSIDE, 'sphere_name': 'Somewhere else', 'status': 'Completed'})
    assert status == 201, body
    db.execute('DELETE FROM services WHERE service_id = %s', [uuid.UUID(body['service_id'])])
    assert body['spheres'] == ['Riverside Commons'] and body['status'] == 'Posted'
    status, body = api.post('/api/openings', who='marie', json={'type': 'sale', 'title': 'Not a thing here'})
    if status == 201:
        db.execute('DELETE FROM services WHERE service_id = %s', [uuid.UUID(body['service_id'])])
    assert status == 400


def test_outsiders_neither_accept_nor_appreciate(api, riverside_opening):
    assert api.post(f'/api/openings/{riverside_opening}/accept', who='elon', json={})[0] == 403
    assert api.post(f'/api/openings/{riverside_opening}/like', who='elon', json={'liked': True})[0] == 403


# -- Value cards and member lists ----------------------------------------------
def test_value_cards_need_a_session(app, api):
    marie = api.uid('marie')
    assert signed_out(app, f'/api/value_cards/{marie}')[0] == 401
    assert api.get(f'/api/value_cards/{marie}', who='elon')[0] == 200       # members see each other's


def test_a_charter_is_public_only_with_its_sphere(app, api, private_sphere):
    assert api.post(f'/api/entity_value_cards/{private_sphere}', who='admin', json=CARD)[0] == 201
    assert signed_out(app, f'/api/value_cards/{private_sphere}')[0] == 401
    assert api.post(f'/api/spheres/{private_sphere}/governance', who='admin', json={'is_public': True})[0] == 200
    status, cards = signed_out(app, f'/api/value_cards/{private_sphere}')
    assert status == 200 and [c['title'] for c in cards] == [CARD['title']]


def test_a_private_spheres_people_are_for_its_members(api, private_sphere):
    admin = api.uid('admin')
    _, outside = api.get(f'/api/spheres/{private_sphere}', who='elon')
    assert outside['members'] == [] and outside['participants'] == [] and outside['member_count'] == 1
    assert admin not in str(outside)
    _, rows = api.get('/api/spheres', who='elon')
    row = next(r for r in rows if r['sphere_id'] == private_sphere)
    assert row['members'] == [] and row['participant_names'] == [] and row['member_count'] == 1
    assert admin not in str(row)
    _, inside = api.get(f'/api/spheres/{private_sphere}', who='admin')
    assert [m['id'] for m in inside['members']] == [admin]


def test_signed_out_visitors_get_counts_not_names(app, api, private_sphere):
    assert api.post(f'/api/spheres/{private_sphere}/governance', who='admin', json={'is_public': True})[0] == 200
    status, d = signed_out(app, f'/api/public/spheres/{private_sphere}')
    assert status == 200 and d['members'] == [] and d['member_count'] == 1
    assert api.uid('admin') not in str(d)


# -- Evidence ------------------------------------------------------------------
def test_a_receipt_cannot_put_words_on_someones_card(api, riverside_exchange):
    marie = api.uid('marie')
    _, cards = api.get(f'/api/value_cards/{marie}', who='marie')
    real = cards[0]
    status, body = api.post(f'/api/exchange/{riverside_exchange}/comment', who='marie', json={
        'type': 'gratitude', 'text': 'Thank you', 'card_ids': [real['card_id']],
        'cards': [{**real, 'title': 'Forged'}, {'card_id': str(uuid.uuid4()), 'title': 'Invented'}]})
    assert status == 200, body
    _, d = api.get(f'/api/exchange/{riverside_exchange}', who='marie')
    assert [c['title'] for c in d['exchange']['gratitude_comment_cards']] == [real['title']]


def test_receipt_photos_settle_once_the_exchange_is_finished(api, riverside_exchange):
    xid = riverside_exchange
    send = lambda: api.post(f'/api/exchange/{xid}/receipt_photos', who='marie', content_type='multipart/form-data',
                            data={'photos': [(io.BytesIO(PNG_1PX), 'p.png')]})
    assert api.post(f'/api/exchange/{xid}/comment', who='david', json={'type': 'user', 'text': 'Glad to'})[0] == 200
    assert api.post(f'/api/exchange/{xid}/comment', who='marie', json={'type': 'gratitude', 'text': 'Thanks'})[0] == 200
    assert send()[0] == 200         # the photos that follow the receipt
    assert send()[0] == 409         # but evidence isn't replaced afterwards
