# Acknowledgements on every Meaning Trail: anyone may add one, except in
# spheres they aren't in; others appreciate them; the trail's owner highlights
# up to two in a run. (The rule for runs alone: test_timeline.py.)
import uuid

import pytest

from conftest import REPAIR_CAFE, RIVERSIDE, TOOL_LIBRARY


@pytest.fixture
def clean_trails(db):
    """Acknowledgements a test adds (and their likes) are removed afterwards."""
    before = {(r.trail_id, r.created_at, r.ack_id)
              for r in db.execute('SELECT trail_id, created_at, ack_id FROM trail_acknowledgements')}
    yield
    for r in db.execute('SELECT trail_id, created_at, ack_id FROM trail_acknowledgements'):
        key = (r.trail_id, r.created_at, r.ack_id)
        if key not in before:
            db.execute('DELETE FROM trail_acknowledgements WHERE trail_id = %s AND created_at = %s AND ack_id = %s', list(key))
            db.execute("DELETE FROM likes WHERE exchange_id = %s AND comment_type = 'ack'", [r.ack_id])


@pytest.fixture
def exchange(api, db, clean_trails):
    """David's Riverside offer, taken up by Marie."""
    status, made = api.post('/api/openings', who='david', json={
        'type': 'offer', 'title': 'Trail test opening', 'sphere_id': RIVERSIDE})
    assert status == 201, made
    sid, marie = made['service_id'], api.uid('marie')
    assert api.post(f'/api/openings/{sid}/accept', who='marie', json={})[0] == 200
    status, body = api.post(f'/api/openings/{sid}/confirm', who='david', json={'accepter_id': marie})
    assert status == 200, body
    yield body['exchange_id']
    x = uuid.UUID(body['exchange_id'])
    db.execute('DELETE FROM meaning_trail WHERE user_id = %s AND exchange_id = %s', [uuid.UUID(api.uid('david')), x])
    db.execute('DELETE FROM services WHERE service_id = %s', [uuid.UUID(sid)])
    db.execute('DELETE FROM opening_acceptances WHERE service_id = %s', [uuid.UUID(sid)])
    for kind in ('exchange', 'other'):
        db.execute('DELETE FROM likes WHERE exchange_id = %s AND comment_type = %s', [x, kind])


def acknowledge(api, trail, who, text='Thank you for being you', **more):
    return api.post(f'/api/trails/{trail}/acknowledgements', who=who, json={'text': text, **more})


def made(api, trail, who, **more):
    status, body = acknowledge(api, trail, who, **more)
    assert status == 201, body
    return body['acknowledgement']['ack_id']


def items(api, trail, who):
    status, body = api.get(f'/api/trails/{trail}', who=who)
    assert status == 200, body
    return {i['ack_id']: i for e in body['entries'] if e['type'] == 'acknowledgements' for i in e['items']}


def test_anyone_acknowledges_on_a_persons_trail(api, clean_trails):
    marie = api.uid('marie')
    ack = made(api, marie, 'elon', text='  Tidiest toolshed around  ')
    seen = items(api, marie, 'david')[ack]
    assert seen['text'] == 'Tidiest toolshed around' and seen['author_id'] == api.uid('elon')
    _, inbox = api.get('/api/notifications', who='marie')
    assert any(n['type'] == 'acknowledgement' and n['actor_id'] == api.uid('elon') for n in inbox['notifications'])


@pytest.mark.parametrize('trail', [RIVERSIDE, REPAIR_CAFE, TOOL_LIBRARY])
def test_not_in_spheres_you_are_not_in(api, clean_trails, trail):
    assert acknowledge(api, trail, 'elon')[0] in (403, 404)
    assert api.get(f'/api/trails/{trail}', who='elon')[0] == 404
    ack = made(api, trail, 'david')                 # in Riverside, if not in the Tool Library
    assert ack in items(api, trail, 'marie')


def test_the_admin_override_reads_and_moderates_but_does_not_write(api, clean_trails):
    ack = made(api, RIVERSIDE, 'david')
    assert ack in items(api, RIVERSIDE, 'admin')
    assert acknowledge(api, RIVERSIDE, 'admin')[0] == 403
    assert api.post(f'/api/trails/{RIVERSIDE}/acknowledgements/{ack}/highlight', who='admin', json={})[0] == 403
    assert api.delete(f'/api/trails/{RIVERSIDE}/acknowledgements/{ack}', who='admin')[0] == 200


def test_text_only_and_not_too_much_of_it(api, clean_trails):
    marie = api.uid('marie')
    assert acknowledge(api, marie, 'david', text='   ')[0] == 400
    assert acknowledge(api, marie, 'david', text='x' * 1001)[0] == 400
    assert acknowledge(api, marie, 'david', text={'not': 'text'})[0] == 400
    assert acknowledge(api, str(uuid.uuid4()), 'david')[0] == 404


def test_value_cards_attach_as_they_are_stored(api, clean_trails):
    marie = api.uid('marie')
    _, cards = api.get(f'/api/value_cards/{marie}', who='david')
    ack = made(api, marie, 'david', card_ids=[cards[0]['card_id'], str(uuid.uuid4()), 'junk'])
    assert [c['title'] for c in items(api, marie, 'david')[ack]['cards']] == [cards[0]['title']]


def test_others_appreciate_it_once(api, clean_trails):
    marie = api.uid('marie')
    ack = made(api, marie, 'david')
    like = f'/api/trails/{marie}/acknowledgements/{ack}/like'
    assert api.post(like, who='david', json={'liked': True})[0] == 403
    for _ in range(2):
        status, body = api.post(like, who='marie', json={'liked': True})
        assert status == 200 and body['count'] == 1 and body['by'][0]['name'] == 'Marie Kondo'
    assert api.post(like, who='marie', json={'liked': False})[1]['count'] == 0


def test_the_owner_highlights_two_in_a_run_not_three(api, clean_trails):
    marie = api.uid('marie')
    acks = [made(api, marie, 'david', text=f'Thanks {n}') for n in range(3)]
    path = lambda a: f'/api/trails/{marie}/acknowledgements/{a}/highlight'
    assert api.post(path(acks[0]), who='david', json={'highlighted': True})[0] == 403
    for a in acks[:2]:
        assert api.post(path(a), who='marie', json={'highlighted': True})[0] == 200
    assert api.post(path(acks[2]), who='marie', json={'highlighted': True})[0] == 409
    seen = items(api, marie, 'joe')
    assert [seen[a]['highlighted'] for a in acks] == [True, True, False]
    assert [seen[a]['shown'] for a in acks] == [True, True, False]
    assert api.post(path(acks[0]), who='marie', json={'highlighted': False})[0] == 200
    assert api.post(path(acks[2]), who='marie', json={'highlighted': True})[0] == 200


def test_author_and_owner_can_remove_nobody_else(api, clean_trails):
    marie = api.uid('marie')
    first, second = made(api, marie, 'david'), made(api, marie, 'david')
    path = lambda a: f'/api/trails/{marie}/acknowledgements/{a}'
    assert api.delete(path(first), who='elon')[0] == 403
    assert api.delete(path(first), who='david')[0] == 200
    assert api.delete(path(second), who='marie')[0] == 200
    assert not {first, second} & set(items(api, marie, 'marie'))


def test_an_exchange_takes_any_number(api, exchange):
    first, second = made(api, exchange, 'joe'), made(api, exchange, 'david')
    assert acknowledge(api, exchange, 'elon')[0] == 404
    status, d = api.get(f'/api/exchange/{exchange}', who='marie')
    assert status == 200 and d['can_acknowledge'] is True
    assert [a['ack_id'] for a in d['exchange']['acknowledgements']] == [second, first]
    assert all(a['can_highlight'] for a in d['exchange']['acknowledgements'])         # Marie is a side of it
    assert api.post(f'/api/trails/{exchange}/acknowledgements/{first}/highlight', who='marie', json={})[0] == 200


def test_older_apps_still_see_and_use_the_single_slot(api, exchange):
    path = f'/api/exchange/{exchange}'
    assert api.post(f'{path}/comment', who='joe', json={'type': 'other', 'text': 'Lovely'})[0] == 200
    assert api.post(f'{path}/comment', who='david', json={'type': 'other', 'text': 'Another'})[0] == 200
    _, d = api.get(path, who='marie')
    assert d['exchange']['other_comment'] == 'Lovely' and len(d['exchange']['acknowledgements']) == 2
    status, liked = api.post(f'{path}/like', who='marie', json={'comment_type': 'other'})
    assert status == 200 and liked['count'] == 1 and liked['comment_type'] == 'other'
    _, d = api.get(path, who='marie')
    assert d['exchange']['likes']['other']['liked'] is True


def test_exchanges_sit_in_their_spheres_trail_and_split_runs(api, exchange):
    _, riverside = api.get(f'/api/trails/{RIVERSIDE}', who='marie')
    assert exchange in [e['id'] for e in riverside['entries'] if e['type'] == 'exchange']
    ack = made(api, RIVERSIDE, 'david')             # newer than the exchange
    _, riverside = api.get(f'/api/trails/{RIVERSIDE}', who='marie')
    order = [e['items'][0]['ack_id'] if e['type'] == 'acknowledgements' else e['id'] for e in riverside['entries']]
    assert order.index(ack) < order.index(exchange)


def test_a_persons_trail_still_hides_other_spheres_exchanges(api, exchange):
    _, outsider = api.get(f"/api/trails/{api.uid('marie')}", who='elon')
    assert exchange not in [e['id'] for e in outsider['entries']]
