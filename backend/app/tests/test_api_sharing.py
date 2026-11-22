# Sharing an opening with more spheres, loans, the activity of people you
# follow, and whom you both know. The people are conftest's: Ada and Ben share
# Ada's sphere; Cy is outside it. Cy's own sphere is the second, and Ada joins it.
import uuid
from datetime import datetime, timedelta

import pytest

from app.utils import demo
from app.utils.search_vectors import invalidate_index


@pytest.fixture
def two(db, people):
    status, made = people['cy'].post('/api/spheres', {'name': 'Sharing test sphere (delete me)', 'description': 'x'})
    assert status == 201, made
    second = uuid.UUID(made['sphere_id'])
    assert people['ada'].post(f'/api/spheres/{second}/join')[0] in (200, 201)
    yield {**people, 'second': second}
    for who in (people['ada'], people['ben'], people['cy']):
        for row in db.execute('SELECT exchange_id FROM meaning_trail WHERE user_id = %s', [who.id]):
            db.execute('DELETE FROM trail_acknowledgements WHERE trail_id = %s', [row.exchange_id])
        db.execute('DELETE FROM meaning_trail WHERE user_id = %s', [who.id])
    db.execute('DELETE FROM spheres WHERE sphere_id = %s', [second])
    demo.forget()
    invalidate_index()


def post_opening(person, sphere=None, **more):
    body = {'title': 'Test long ladder', 'type': 'offer', **more}
    if sphere:
        body['sphere_id'] = str(sphere)
    status, made = person.post('/api/openings', body)
    assert status == 201, made
    return made['service_id']


def exchange_between(provider, accepter, opening):
    assert accepter.post(f'/api/openings/{opening}/accept')[0] == 200
    status, done = provider.post(f'/api/openings/{opening}/confirm', {'accepter_id': str(accepter.id)})
    assert status == 200, done
    return done['exchange_id']


def patch(person, path, body):
    r = person.client.patch(path, headers=person.headers, json=body)
    return r.status_code, r.get_json(silent=True)


def listed(person):
    return {o['service_id']: o for o in person.get('/api/openings')[1]}


# -- Sharing --------------------------------------------------------------------
def test_shared_into_another_sphere_is_seen_there(two):
    ada, ben, cy = two['ada'], two['ben'], two['cy']
    opening = post_opening(ada, two['sphere'])
    path = f'/api/openings/{opening}'
    assert opening not in listed(cy) and cy.get(path)[0] == 403
    assert cy.post(f'{path}/accept')[0] == 403

    status, shared = ada.post(f'{path}/spheres', {'sphere_ids': [str(two['second'])]})
    assert status == 200, shared
    assert [s['id'] for s in shared['shared_with']] == [str(two['second'])]
    assert opening in listed(cy) and cy.get(path)[0] == 200
    assert [s['id'] for s in listed(cy)[opening]['shared_with']] == [str(two['second'])]
    # Ben isn't in the second sphere, so doesn't learn that Ada is.
    assert listed(ben)[opening]['shared_with'] == []


def test_it_can_be_shared_when_its_posted(two):
    opening = post_opening(two['ada'], two['sphere'], also_sphere_ids=[str(two['second'])])
    assert opening in listed(two['cy'])


def test_shared_with_shows_the_opening_never_its_spheres_people(two):
    ada, ben, cy = two['ada'], two['ben'], two['cy']
    opening = post_opening(ada, two['sphere'], cadence='perpetual', also_sphere_ids=[str(two['second'])])
    path = f'/api/openings/{opening}'
    assert ben.post(f'{path}/like', {'liked': True})[0] == 200
    exchange_between(ada, ben, opening)

    seen = cy.get(path)[1]
    assert seen['likes'] == 1 and seen['liked_by'] == []
    assert seen['exchanges'] == [] and seen['history'] == []
    assert str(ben.id) not in str(seen) and 'Test Ben' not in str(seen)
    assert str(ben.id) not in str(listed(cy)[opening])
    status, liked = cy.post(f'{path}/like', {'liked': True})
    assert status == 200 and [p['id'] for p in liked['liked_by']] == [str(cy.id)]
    # Those inside still see people rather than numbers.
    inside = ada.get(path)[1]
    assert {p['id'] for p in inside['liked_by']} == {str(ben.id), str(cy.id)}
    assert len(inside['exchanges']) == 1


def test_someone_it_was_shared_with_can_take_it_up(two):
    ada, ben, cy = two['ada'], two['ben'], two['cy']
    opening = post_opening(ada, two['sphere'], also_sphere_ids=[str(two['second'])])
    exchange = exchange_between(ada, cy, opening)
    assert cy.get(f'/api/exchange/{exchange}')[0] == 200        # a side of it
    assert ben.get(f'/api/exchange/{exchange}')[0] == 200       # it happened in the opening's sphere
    assert ada.post(f'/api/openings/{opening}/spheres', {'sphere_ids': []})[0] == 200
    assert cy.get(f'/api/openings/{opening}')[0] == 200         # still the one who took it up


def test_who_may_share_and_into_what(db, two):
    ada, ben, cy, second = two['ada'], two['ben'], two['cy'], two['second']
    opening = post_opening(ada, two['sphere'])
    path = f'/api/openings/{opening}/spheres'
    assert ben.post(path, {'sphere_ids': [str(second)]})[0] == 403      # not Ben's opening
    for wrong in ({}, {'sphere_ids': 'all'}, {'sphere_ids': ['nope']}):
        assert ada.post(path, wrong)[0] == 400, wrong
    assert ada.post(path, {'sphere_ids': [str(uuid.uuid4())]})[0] == 403    # not one Ada is in
    everyones = post_opening(cy)
    assert cy.post(f'/api/openings/{everyones}/spheres', {'sphere_ids': [str(second)]})[0] == 400

    db.execute('UPDATE spheres SET is_demo = true WHERE sphere_id = %s', [second])
    demo.forget()
    status, refused = ada.post(path, {'sphere_ids': [str(second)]})
    assert status == 400 and 'demo' in refused['message'].lower()


def test_leaving_takes_the_shared_openings_out(two):
    ada, cy = two['ada'], two['cy']
    opening = post_opening(ada, two['sphere'], also_sphere_ids=[str(two['second'])])
    assert opening in listed(cy)
    assert ada.post(f"/api/spheres/{two['second']}/leave")[0] == 200
    assert opening not in listed(cy)


def test_a_new_version_is_shared_alike(two):
    ada, ben, cy = two['ada'], two['ben'], two['cy']
    opening = post_opening(ada, two['sphere'], cadence='perpetual', borrow=True, also_sphere_ids=[str(two['second'])])
    exchange_between(ada, ben, opening)
    status, edited = patch(ada, f'/api/openings/{opening}', {'title': 'Test longer ladder'})
    assert status == 200 and edited['versioned'] is True
    newer = edited['service']['service_id']
    assert listed(cy)[newer]['borrow'] is True


def test_search_finds_what_was_shared(two):
    title = f'Testsharedladder{uuid.uuid4().hex[:8]}'
    opening = post_opening(two['ada'], two['sphere'], title=title)
    invalidate_index()
    assert two['cy'].get(f'/api/search?q={title}')[1]['total'] == 0
    assert two['ada'].post(f'/api/openings/{opening}/spheres', {'sphere_ids': [str(two['second'])]})[0] == 200
    assert two['cy'].get(f'/api/search?q={title}')[1]['total'] == 1


def test_one_can_write_to_its_poster(two):
    ada, cy = two['ada'], two['cy']
    opening = post_opening(ada, two['sphere'], also_sphere_ids=[str(two['second'])])
    status, talk = cy.get(f'/api/messages/{ada.id}?opening={opening}')
    assert status == 200 and talk['about']['id'] == opening


# -- Loans --------------------------------------------------------------------
def test_a_loan_says_so_on_the_opening_and_its_exchange(two):
    ada, ben = two['ada'], two['ben']
    opening = post_opening(ada, two['sphere'], borrow=True)
    assert listed(ben)[opening]['borrow'] is True
    exchange = exchange_between(ada, ben, opening)
    assert ben.get(f'/api/exchange/{exchange}')[1]['exchange']['borrow'] is True


def test_a_loan_is_yes_or_no(two):
    ada = two['ada']
    assert ada.post('/api/openings', {'title': 'Test', 'borrow': 'yes'})[0] == 400
    opening = post_opening(ada)
    assert listed(ada)[opening]['borrow'] is False
    assert patch(ada, f'/api/openings/{opening}', {'borrow': 1})[0] == 400
    assert patch(ada, f'/api/openings/{opening}', {'borrow': True})[0] == 200
    assert listed(ada)[opening]['borrow'] is True


# -- Activity ------------------------------------------------------------------
def test_activity_is_only_what_you_may_see(two):
    ada, ben, cy = two['ada'], two['ben'], two['cy']
    assert cy.post(f'/api/users/{ada.id}/follow')[0] == 200
    assert ben.post(f'/api/users/{ada.id}/follow')[0] == 200
    inside = post_opening(ada, two['sphere'], title='Test only inside')
    open_to_all = post_opening(ada, title='Test for everyone', borrow=True)

    theirs = cy.get('/api/activity')[1]['activity']
    assert [i['link'] for i in theirs] == [f'/opening?id={open_to_all}']
    assert theirs[0]['says'] == 'offers to lend' and theirs[0]['who']['id'] == str(ada.id)
    assert {i['link'] for i in ben.get('/api/activity')[1]['activity']} == {
        f'/opening?id={inside}', f'/opening?id={open_to_all}'}


def test_activity_has_exchanges_thanks_and_events(two):
    ada, ben, cy, sphere = two['ada'], two['ben'], two['cy'], two['sphere']
    assert ben.post(f'/api/users/{ada.id}/follow')[0] == 200
    exchange = exchange_between(ada, ben, post_opening(ada, sphere))
    assert ada.post(f'/api/trails/{cy.id}/acknowledgements', {'text': 'For the soup'})[0] == 201
    soon = (datetime.utcnow() + timedelta(days=4)).strftime('%Y-%m-%dT18:00')
    status, event = ada.post('/api/events', {'title': 'Test soup', 'starts': soon, 'tz': 'UTC', 'host_id': str(sphere)})
    assert status == 201, event

    seen = {i['kind']: i for i in ben.get('/api/activity')[1]['activity']}
    assert seen['exchange']['link'] == f'/exchange?id={exchange}' and seen['exchange']['says'].endswith('with you')
    assert seen['acknowledgement']['title'] == 'Test Cy' and seen['acknowledgement']['text'] == 'For the soup'
    assert seen['event']['link'] == f"/event?id={event['id']}"

    # A block either way hides what involves them.
    assert cy.post(f'/api/blocks/{ben.id}', {'blocked': True})[0] == 200
    assert 'acknowledgement' not in {i['kind'] for i in ben.get('/api/activity')[1]['activity']}


def test_following_nobody_is_empty(two):
    assert two['cy'].get('/api/activity')[1] == {'activity': []}


# -- Whom you both know --------------------------------------------------------
def test_you_both_know(two):
    ada, ben, cy = two['ada'], two['ben'], two['cy']
    assert ben.get(f'/api/users/{ada.id}/known')[1] == {'people': []}
    exchange_between(ada, cy, post_opening(ada, two['second']))     # in a sphere Ben isn't in
    assert ben.post(f'/api/users/{cy.id}/follow')[0] == 200
    assert ben.get(f'/api/users/{ada.id}/known')[1] == {'people': []}      # following alone doesn't show it

    exchange_between(ada, cy, post_opening(ada, two['sphere'], also_sphere_ids=[str(two['second'])]))
    assert [p['id'] for p in ben.get(f'/api/users/{ada.id}/known')[1]['people']] == [str(cy.id)]
    # Cy learns nothing of whom Ben follows.
    assert cy.get(f'/api/users/{ben.id}/known')[1] == {'people': []}
