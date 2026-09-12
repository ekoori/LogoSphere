# Openings: accept -> confirm (LWT), receipts naming value cards, likes as
# names, edit-after-exchange versioning. Every row the test creates is
# removed again in the fixture teardown.
import uuid
import pytest

JOE = 'fe878ccf-aba7-4b16-8b5f-847f7db6e0ad'
OPENING = '2052e249-96e0-5b37-aaef-5a23ae361baf'   # Joe's perpetual "Sharing what I know"


@pytest.fixture
def exchange(api, db):
    """Marie accepts Joe's perpetual opening and Joe confirms -> one exchange.
    Yields its id; teardown deletes the exchange, acceptance, likes and any
    version the test branched."""
    marie = api.uid('marie')
    status, body = api.post(f'/api/openings/{OPENING}/accept', who='marie', json={})
    assert status in (200, 201), body
    status, body = api.post(f'/api/openings/{OPENING}/confirm', who='joe', json={'accepter_id': marie})
    assert status == 200 and body['exchange_id'], body
    xid = body['exchange_id']
    created_versions = []
    yield {'id': xid, 'marie': marie, 'versions': created_versions}
    joe, x, op, m = uuid.UUID(JOE), uuid.UUID(xid), uuid.UUID(OPENING), uuid.UUID(marie)
    db.execute('DELETE FROM meaning_trail WHERE user_id = %s AND exchange_id = %s', [joe, x])
    db.execute('DELETE FROM opening_acceptances WHERE service_id = %s AND accepter_id = %s', [op, m])
    for ct in ('exchange', 'gratitude', 'user', 'other'):
        db.execute('DELETE FROM likes WHERE exchange_id = %s AND comment_type = %s', [x, ct])
    db.execute('DELETE FROM opening_likes WHERE service_id = %s AND user_id = %s', [op, m])
    for v in created_versions:
        db.execute('DELETE FROM services WHERE service_id = %s', [uuid.UUID(v)])
    db.execute('UPDATE services SET is_current = true, title = %s WHERE service_id = %s', ['Sharing what I know', op])


def test_second_confirm_is_idempotent(api, exchange):
    status, body = api.post(f'/api/openings/{OPENING}/confirm', who='joe', json={'accepter_id': exchange['marie']})
    assert status == 200 and body['message'] == 'Already confirmed'
    assert body['exchange_id'] == exchange['id']


def test_receipt_names_value_cards_and_kind_of_meaning(api, exchange):
    xid = exchange['id']
    _, cards = api.get(f'/api/value_cards/{JOE}')
    ids = [c['card_id'] for c in cards[:2]]
    status, body = api.post(f'/api/exchange/{xid}/comment', who='marie', json={
        'type': 'gratitude', 'text': 'Patient and generous.', 'card_ids': ids,
        'frankl_mode': 'experiential', 'cards': []})
    assert status == 200, body
    _, d = api.get(f'/api/exchange/{xid}', who='joe')
    x = d['exchange']
    assert x['gratitude_card_ids'] == ids
    assert x['gratitude_frankl_mode'] == 'experiential'
    # a second receipt from the same side is refused, not overwritten
    status, body = api.post(f'/api/exchange/{xid}/comment', who='marie', json={'type': 'gratitude', 'text': 'again'})
    assert status == 409


def test_status_state_machine(api, exchange):
    xid = exchange['id']
    status, body = api.post(f'/api/exchange/{xid}/status', who='joe', json={'status': 'Receipted'})
    assert status == 409 and body['status'] == 'Initiated'
    status, body = api.post(f'/api/exchange/{xid}/status', who='joe', json={'status': 'In Progress'})
    assert status == 200 and body['status'] == 'In Progress'
    status, _ = api.post(f'/api/exchange/{xid}/status', who='elon', json={'status': 'Finished'})
    assert status in (403, 404)   # not a participant (and not in the sphere)


def test_likes_are_people_not_numbers(api, exchange):
    xid = exchange['id']
    api.post(f'/api/exchange/{xid}/like', who='joe', json={'comment_type': 'exchange'})
    status, body = api.post(f'/api/exchange/{xid}/like', who='marie', json={'comment_type': 'exchange'})
    assert status == 200
    assert sorted(p['name'] for p in body['by']) == ['Joe Rogan', 'Marie Kondo']
    # openings: explicit target state is idempotent
    _, b1 = api.post(f'/api/openings/{OPENING}/like', who='marie', json={'liked': True})
    _, b2 = api.post(f'/api/openings/{OPENING}/like', who='marie', json={'liked': True})
    assert b1['likes'] == b2['likes'] == 1 and b2['liked_by'][0]['name'] == 'Marie Kondo'
    _, b3 = api.post(f'/api/openings/{OPENING}/like', who='marie', json={'liked': False})
    assert b3['likes'] == 0


def test_edit_after_exchange_branches_a_version(api, exchange):
    status, body = api.patch(f'/api/openings/{OPENING}', who='joe', json={'title': 'Sharing what I know (v2)'})
    assert status == 200 and body['versioned'] is True
    new_id = body['service']['service_id']
    exchange['versions'].append(new_id)
    assert new_id != OPENING and body['service']['version'] == 2
    # the old version is frozen and can no longer be edited
    _, old = api.get(f'/api/openings/{OPENING}', who='joe')
    assert old['is_current'] is False and old['title'] == 'Sharing what I know'
    assert api.patch(f'/api/openings/{OPENING}', who='joe', json={'title': 'x'})[0] == 409
    # the new version lists the old one, with its exchange, as history
    _, new = api.get(f'/api/openings/{new_id}', who='joe')
    assert new['is_current'] is True
    assert [h['service_id'] for h in new['history']] == [OPENING]
    assert new['history'][0]['exchanges'][0]['exchange_id'] == exchange['id']
    # the marketplace only shows the current version
    _, rows = api.get('/api/openings', who='joe')
    ids = {r['service_id'] for r in rows}
    assert new_id in ids and OPENING not in ids


def test_edit_without_exchange_updates_in_place(api, db):
    opening = '71887191-7e4c-5731-8f03-ba543bc778d6'   # Joe's "Looking for a helping hand" (no exchange)
    try:
        status, body = api.patch(f'/api/openings/{opening}', who='joe', json={'title': 'Looking for a helping hand (t)'})
        assert status == 200 and body['versioned'] is False and body['service']['service_id'] == opening
    finally:
        db.execute('UPDATE services SET title = %s WHERE service_id = %s', ['Looking for a helping hand', uuid.UUID(opening)])


def test_only_the_provider_edits(api):
    status, _ = api.patch(f'/api/openings/{OPENING}', who='marie', json={'title': 'x'})
    assert status == 403


# ── Platform admins are not parties to other people's openings ──────────────
def test_platform_admin_can_accept_someone_elses_opening(api, db):
    """Regression: an admin used to get 'You cannot accept your own opening'
    on EVERY opening, because the manage-anything override was also used to
    decide who the provider is."""
    _, items = api.get('/api/openings', who='joe')
    theirs = next(o for o in items if o['provider_id'] != api.uid('joe') and o['cadence'] == 'perpetual')
    assert theirs['is_provider'] is False and theirs['can_manage'] is True
    mine = next(o for o in items if o['id'] == OPENING)
    assert mine['is_provider'] is True and mine['can_manage'] is True
    status, body = api.post(f"/api/openings/{theirs['id']}/accept", who='joe', json={})
    assert status == 200, body
    db.execute('DELETE FROM opening_acceptances WHERE service_id = %s AND accepter_id = %s',
               [uuid.UUID(theirs['id']), uuid.UUID(api.uid('joe'))])


# ── Cancelling an opening ───────────────────────────────────────────────────
@pytest.fixture
def davids_opening(api, db):
    status, body = api.post('/api/openings', who='david', json={
        'type': 'need', 'title': 'Cancel me', 'description': 'temporary',
        'sphere_id': '11111111-1111-1111-1111-111111111111'})
    assert status == 201, body
    sid = body['service_id']
    yield sid
    db.execute('DELETE FROM services WHERE service_id = %s', [uuid.UUID(sid)])
    db.execute('DELETE FROM opening_acceptances WHERE service_id = %s', [uuid.UUID(sid)])


def test_provider_cancels_an_unconfirmed_opening(api, davids_opening):
    sid = davids_opening
    status, _ = api.post(f'/api/openings/{sid}/accept', who='marie', json={})
    assert status == 200
    # someone else can't cancel it; a platform admin (Joe) can, and so can David
    status, _ = api.post(f'/api/openings/{sid}/cancel', who='elon', json={})
    assert status == 403
    status, body = api.post(f'/api/openings/{sid}/cancel', who='joe', json={})
    assert status == 200 and body['status'] == 'Cancelled'
    status, body = api.post(f'/api/openings/{sid}/cancel', who='david', json={})
    assert status == 200 and body['status'] == 'Cancelled'      # idempotent
    # gone from the marketplace, pending acceptance dropped, page still reachable, no new accepts
    _, items = api.get('/api/openings', who='marie')
    assert all(o['id'] != sid for o in items)
    _, page = api.get(f'/api/openings/{sid}', who='marie')
    assert page['status'] == 'Cancelled' and page['my_acceptance'] is None
    status, body = api.post(f'/api/openings/{sid}/accept', who='marie', json={})
    assert status == 409


def test_confirmed_opening_cannot_be_cancelled(api, davids_opening):
    sid = davids_opening
    status, _ = api.post(f'/api/openings/{sid}/accept', who='marie', json={})
    assert status == 200
    status, body = api.post(f'/api/openings/{sid}/confirm', who='david', json={'accepter_id': api.uid('marie')})
    assert status == 200 and body['exchange_id']
    xid = uuid.UUID(body['exchange_id'])
    try:
        status, body = api.post(f'/api/openings/{sid}/cancel', who='joe', json={})
        assert status == 409 and 'exchange' in body['message']
    finally:
        from app.db import session as db
        for who in ('david', 'marie'):
            db.execute('DELETE FROM meaning_trail WHERE user_id = %s AND exchange_id = %s',
                       [uuid.UUID(api.uid(who)), xid])
