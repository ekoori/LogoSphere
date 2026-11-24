# Openings: accept -> confirm (LWT), receipts naming value cards, likes as
# names, edit-after-exchange versioning. Every row the test creates is
# removed again in the fixture teardown.
import uuid
import pytest

JOE = 'fe878ccf-aba7-4b16-8b5f-847f7db6e0ad'
OPENING = '2052e249-96e0-5b37-aaef-5a23ae361baf'   # Joe's perpetual "Sharing what I know"


@pytest.fixture
def exchange(api, db, keep_rows):
    """Marie accepts Joe's perpetual opening and Joe confirms -> one exchange.
    Yields its id; teardown deletes the exchange, its likes and any version the
    test branched, and puts the opening, Marie's acceptance and her like on it
    back exactly as they were."""
    marie = api.uid('marie')
    keep_rows('services', service_id=OPENING)
    keep_rows('opening_acceptances', service_id=OPENING, accepter_id=marie)
    keep_rows('opening_likes', service_id=OPENING, user_id=marie)
    status, body = api.post(f'/api/openings/{OPENING}/accept', who='marie', json={})
    assert status in (200, 201), body
    status, body = api.post(f'/api/openings/{OPENING}/confirm', who='joe', json={'accepter_id': marie})
    assert status == 200 and body['exchange_id'], body
    xid = body['exchange_id']
    created_versions = []
    yield {'id': xid, 'marie': marie, 'versions': created_versions}
    joe, x = uuid.UUID(JOE), uuid.UUID(xid)
    db.execute('DELETE FROM meaning_trail WHERE user_id = %s AND exchange_id = %s', [joe, x])
    db.execute('DELETE FROM receipt_photos WHERE exchange_id = %s', [x])
    db.execute('DELETE FROM trail_acknowledgements WHERE trail_id = %s', [x])
    for ct in ('exchange', 'gratitude', 'user', 'other'):
        db.execute('DELETE FROM likes WHERE exchange_id = %s AND comment_type = %s', [x, ct])
    for v in created_versions:
        db.execute('DELETE FROM services WHERE service_id = %s', [uuid.UUID(v)])


def test_second_confirm_is_idempotent(api, exchange):
    status, body = api.post(f'/api/openings/{OPENING}/confirm', who='joe', json={'accepter_id': exchange['marie']})
    assert status == 200 and body['message'] == 'Already confirmed'
    assert body['exchange_id'] == exchange['id']


def test_receipt_names_value_cards_and_kind_of_meaning(api, exchange):
    xid = exchange['id']
    _, cards = api.get(f'/api/value_cards/{JOE}', who='marie')
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
    status, body = api.post(f'/api/exchange/{xid}/like', who='david', json={'comment_type': 'exchange'})
    assert status == 200
    assert [p['name'] for p in body['by']] == ['David Attenbarough']
    # openings: explicit target state is idempotent
    _, b1 = api.post(f'/api/openings/{OPENING}/like', who='marie', json={'liked': True})
    _, b2 = api.post(f'/api/openings/{OPENING}/like', who='marie', json={'liked': True})
    assert b1['likes'] == b2['likes'] == 1 and b2['liked_by'][0]['name'] == 'Marie Konda'
    _, b3 = api.post(f'/api/openings/{OPENING}/like', who='marie', json={'liked': False})
    assert b3['likes'] == 0


def test_your_own_opening_is_not_yours_to_appreciate(api, keep_rows):
    keep_rows('opening_likes', service_id=OPENING, user_id=api.uid('joe'))
    status, body = api.post(f'/api/openings/{OPENING}/like', who='joe', json={'liked': True})
    assert status == 403, body
    status, _ = api.post(f'/api/openings/{OPENING}/like', who='joe', json={'liked': False})
    assert status == 200        # an old self-like can still come off


def test_your_own_exchange_is_not_yours_to_appreciate(api, exchange):
    xid = exchange['id']
    for who in ('joe', 'marie'):            # either side
        status, body = api.post(f'/api/exchange/{xid}/like', who=who, json={'comment_type': 'exchange'})
        assert status == 403, body
    # The apps learn which parts are the viewer's own, and offer no button there.
    status, body = api.get(f'/api/exchange/{xid}', who='marie')
    likes = body['exchange']['likes']
    assert likes['exchange']['own'] and likes['gratitude']['own'] and not likes['user']['own']
    status, body = api.get(f'/api/exchange/{xid}', who='david')
    assert not any(v['own'] for v in body['exchange']['likes'].values())


def test_what_is_whose_on_an_exchange():
    from app.models.meaning_trail import own_like_targets
    # I initiated as a person; R acted for the receiving group G; N acknowledged it.
    row = {'user_id': 'I', 'other_user_id': 'G', 'recipient_acting_user_id': 'R', 'other_comment_author_id': 'N'}
    assert own_like_targets(row, 'I') == {'exchange', 'user'}           # their exchange and their note
    assert own_like_targets(row, 'R') == {'exchange', 'gratitude'}      # their exchange and their receipt
    assert own_like_targets(row, 'M', is_other=True) == {'exchange', 'gratitude'}  # manages G
    assert own_like_targets(row, 'N') == {'other'}                      # their acknowledgement
    assert own_like_targets(row, 'X') == set() and own_like_targets(row, None) == set()


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


def test_platform_admin_is_not_the_other_side(api, exchange):
    """Regression: the platform-admin override in can_manage_entity made an
    admin count as every exchange's recipient - even when the recipient is a
    person - so Joe could write Marie's receipt for her."""
    xid = exchange['id']
    status, body = api.get(f'/api/exchange/{xid}', who='joe')
    assert status == 200
    assert body['is_initiator'] is True and body['is_other'] is False
    status, _ = api.post(f'/api/exchange/{xid}/comment', who='joe',
                         json={'type': 'gratitude', 'text': 'Not mine to write.'})
    assert status == 403
    # Marie still is the other side.
    _, as_marie = api.get(f'/api/exchange/{xid}', who='marie')
    assert as_marie['is_other'] is True and as_marie['is_initiator'] is False
    # A platform admin is neither side, and can't write either side's words.
    status, as_admin = api.get(f'/api/exchange/{xid}', who='admin')
    assert status == 200 and as_admin['is_initiator'] is False and as_admin['is_other'] is False
    status, _ = api.post(f'/api/exchange/{xid}/comment', who='admin',
                         json={'type': 'gratitude', 'text': 'Not mine to write either.'})
    assert status == 403


def test_edit_without_exchange_updates_in_place(api, keep_rows):
    opening = '71887191-7e4c-5731-8f03-ba543bc778d6'   # Joe's "Looking for a helping hand" (no exchange)
    keep_rows('services', service_id=opening)
    status, body = api.patch(f'/api/openings/{opening}', who='joe', json={'title': 'Looking for a helping hand (t)'})
    assert status == 200 and body['versioned'] is False and body['service']['service_id'] == opening


def test_only_the_provider_edits(api):
    status, _ = api.patch(f'/api/openings/{OPENING}', who='marie', json={'title': 'x'})
    assert status == 403


def test_list_and_detail_agree(api):
    """The list reads likes and acceptances in bulk, the detail page one
    opening at a time: both must tell the viewer the same thing."""
    _, items = api.get('/api/openings', who='joe')
    keys = ('is_provider', 'can_manage', 'likes', 'liked_by_current_user',
            'my_acceptance', 'pending_acceptances', 'activity')
    sample = items[:12] + [o for o in items if o['id'] == OPENING or o.get('my_acceptance')]
    for o in sample:
        _, one = api.get(f"/api/openings/{o['id']}", who='joe')
        for k in keys:
            assert one[k] == o[k], (o['id'], k)


def test_marketplace_lists_newest_first(api):
    status, body = api.get('/api/openings', who='marie')
    stamps = [o.get('created_at') or '' for o in body]
    assert status == 200 and len(stamps) > 1 and stamps == sorted(stamps, reverse=True)


# ── Platform admins are not parties to other people's openings ──────────────
def test_platform_admin_can_accept_someone_elses_opening(api, keep_rows):
    """Regression: an admin used to get 'You cannot accept your own opening'
    on EVERY opening, because the manage-anything override was also used to
    decide who the provider is."""
    _, items = api.get('/api/openings', who='admin')
    theirs = next(o for o in items if o['cadence'] == 'perpetual')
    assert theirs['is_provider'] is False and theirs['can_manage'] is True
    _, mine = api.get(f'/api/openings/{OPENING}', who='joe')       # a provider's own
    assert mine['is_provider'] is True and mine['can_manage'] is True
    admin = api.uid('admin')
    keep_rows('opening_acceptances', service_id=theirs['id'], accepter_id=admin)
    status, body = api.post(f"/api/openings/{theirs['id']}/accept", who='admin', json={})
    assert status == 200, body
    # ...but managing it doesn't let the admin confirm their own acceptance:
    # that is the provider's consent. They see it as theirs, not as one
    # awaiting them.
    status, body = api.post(f"/api/openings/{theirs['id']}/confirm", who='admin', json={'accepter_id': admin})
    assert status == 403, body
    _, opening = api.get(f"/api/openings/{theirs['id']}", who='admin')
    assert opening['my_acceptance']['status'] == 'pending'
    assert all(p['accepter_id'] != admin for p in opening['pending_acceptances'])


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
    # someone else can't cancel it; a platform admin can, and so can David
    status, _ = api.post(f'/api/openings/{sid}/cancel', who='elon', json={})
    assert status == 403
    status, body = api.post(f'/api/openings/{sid}/cancel', who='admin', json={})
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
        status, body = api.post(f'/api/openings/{sid}/cancel', who='admin', json={})
        assert status == 409 and 'exchange' in body['message']
    finally:
        from app.db import session as db
        for who in ('david', 'marie'):
            db.execute('DELETE FROM meaning_trail WHERE user_id = %s AND exchange_id = %s',
                       [uuid.UUID(api.uid(who)), xid])


# ── Declining, banners, exchange edits and receipt photos ────────────────────
def test_provider_declines_an_acceptance(api, davids_opening):
    sid = davids_opening
    marie = api.uid('marie')
    assert api.post(f'/api/openings/{sid}/accept', who='marie', json={})[0] == 200
    _, page = api.get(f'/api/openings/{sid}', who='david')
    assert [p['accepter_id'] for p in page['pending_acceptances']] == [marie]
    # Only the providing side (or a platform admin) declines.
    assert api.post(f'/api/openings/{sid}/reject', who='elon', json={'accepter_id': marie})[0] == 403
    assert api.post(f'/api/openings/{sid}/reject', who='david', json={})[0] == 400
    status, _ = api.post(f'/api/openings/{sid}/reject', who='david', json={'accepter_id': marie})
    assert status == 200
    _, page = api.get(f'/api/openings/{sid}', who='marie')
    assert page['my_acceptance'] is None and page['status'] == 'Posted'      # open to others again
    assert api.post(f'/api/openings/{sid}/reject', who='david', json={'accepter_id': marie})[0] == 404
    # Marie hears she was declined; David's "Marie wants to accept" is gone.
    link = f'/opening?id={sid}'
    _, inbox = api.get('/api/notifications', who='marie')
    assert any(n['type'] == 'opening_declined' and n['link'] == link for n in inbox['notifications'])
    _, inbox = api.get('/api/notifications', who='david')
    assert not any(n['type'] == 'opening_accepted' and n['link'] == link for n in inbox['notifications'])


def test_accepter_takes_their_acceptance_back(api, davids_opening):
    """Regression: only the provider could undo an acceptance, so someone who
    changed their mind was stuck - and an admin's one way out withdrew the
    whole opening for everyone."""
    sid = davids_opening
    marie = api.uid('marie')
    assert api.post(f'/api/openings/{sid}/accept', who='marie', json={})[0] == 200
    # Nobody else takes it back for her.
    assert api.post(f'/api/openings/{sid}/reject', who='elon', json={'accepter_id': marie})[0] == 403
    link = f'/opening?id={sid}'
    _, inbox = api.get('/api/notifications', who='david')
    assert any(n['type'] == 'opening_accepted' and n['link'] == link for n in inbox['notifications'])
    status, body = api.post(f'/api/openings/{sid}/reject', who='marie', json={'accepter_id': marie})
    assert status == 200 and body['message'] == 'Acceptance taken back'
    # David's "Marie wants to accept" no longer holds, so it's gone.
    _, inbox = api.get('/api/notifications', who='david')
    assert not any(n['type'] == 'opening_accepted' and n['link'] == link for n in inbox['notifications'])
    _, page = api.get(f'/api/openings/{sid}', who='marie')
    assert page['my_acceptance'] is None and page['status'] == 'Posted'      # open to others again
    # Once confirmed it is an exchange, and there is nothing left to take back.
    assert api.post(f'/api/openings/{sid}/accept', who='marie', json={})[0] == 200
    status, body = api.post(f'/api/openings/{sid}/confirm', who='david', json={'accepter_id': marie})
    assert status == 200 and body['exchange_id'], body
    xid = uuid.UUID(body['exchange_id'])
    try:
        assert api.post(f'/api/openings/{sid}/reject', who='marie', json={'accepter_id': marie})[0] == 409
    finally:
        from app.db import session as db
        for who in ('david', 'marie'):
            db.execute('DELETE FROM meaning_trail WHERE user_id = %s AND exchange_id = %s',
                       [uuid.UUID(api.uid(who)), xid])


def test_opening_banner_is_the_providers(app, api, davids_opening):
    from conftest import PNG_1PX
    import io
    sid = davids_opening
    upload = lambda who, data: api.post(f'/api/openings/{sid}/image', who=who, content_type='multipart/form-data',
                                        data={'image': (io.BytesIO(data), 'banner.png')})
    assert upload('marie', PNG_1PX)[0] == 403
    assert upload('david', b'definitely not an image')[0] == 400
    assert upload('david', PNG_1PX)[0] == 200
    r = app.test_client().get(f'/api/openings/{sid}/image')       # public, for <img src>
    assert r.status_code == 200 and r.data == PNG_1PX and r.mimetype == 'image/png'
    _, page = api.get(f'/api/openings/{sid}', who='marie')
    assert page['has_image'] is True and page.get('image') is None    # never inlined in JSON


def test_exchange_edit_and_banner(app, api, exchange):
    from conftest import PNG_1PX
    import io
    xid = exchange['id']
    assert api.post(f'/api/exchange/{xid}/edit', who='elon', json={'title': 'Not mine'})[0] == 403
    status, _ = api.post(f'/api/exchange/{xid}/edit', who='joe', json={'title': 'Edited title', 'description': 'Longer words'})
    assert status == 200
    _, x = api.get(f'/api/exchange/{xid}', who='marie')
    assert x['exchange']['exchange_description'] == 'Edited title'
    assert x['exchange']['exchange_long_description'] == 'Longer words'

    status, _ = api.post(f'/api/exchange/{xid}/edit', who='marie', content_type='multipart/form-data',
                         data={'image': (io.BytesIO(PNG_1PX), 'b.png')})
    assert status == 200
    r = api.client.get(f'/api/exchange/{xid}/image', headers={'Authorization': f"Bearer {api.login('joe')}"})
    assert r.status_code == 200 and r.data == PNG_1PX
    # Not public: the exchange image follows the exchange's visibility.
    assert app.test_client().get(f'/api/exchange/{xid}/image').status_code == 401


def test_receipt_photos_are_the_recipients(api, exchange):
    from conftest import PNG_1PX
    import io
    xid = exchange['id']
    photos = lambda n: {'photos': [(io.BytesIO(PNG_1PX), f'p{i}.png') for i in range(n)]}
    status, _ = api.post(f'/api/exchange/{xid}/receipt_photos', who='joe', content_type='multipart/form-data', data=photos(1))
    assert status == 403                                             # the initiator isn't the recipient
    status, body = api.post(f'/api/exchange/{xid}/receipt_photos', who='marie', content_type='multipart/form-data',
                            data=photos(4))
    assert status == 200 and body['count'] == 3                      # at most three
    _, x = api.get(f'/api/exchange/{xid}', who='joe')
    assert x['exchange']['receipt_photo_count'] == 3
    r = api.client.get(f'/api/exchange/{xid}/receipt_photo/0', headers={'Authorization': f"Bearer {api.login('joe')}"})
    assert r.status_code == 200 and r.data == PNG_1PX
