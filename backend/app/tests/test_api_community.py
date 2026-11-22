# Events, announcements and invitation links. The people are conftest's: Ada
# and Ben share only a sphere of theirs (Ada's); Cy shares nothing with either.
import io
import uuid
from datetime import datetime, timedelta

import pytest

from conftest import PNG_1PX, PERSON_PASSWORD
from app.utils import invites, mailer

SOON = (datetime.utcnow() + timedelta(days=9)).replace(hour=19, minute=0).strftime('%Y-%m-%dT%H:%M')


def put_on(person, sphere=None, **more):
    body = {'title': 'Test mending night', 'starts': SOON, 'tz': 'UTC', 'length_min': 120, **more}
    if sphere:
        body['host_id'] = str(sphere)
    return person.post('/api/events', body)


# -- Events ------------------------------------------------------------------
def test_a_groups_event_is_seen_inside_its_sphere(people):
    ada, ben, cy, sphere = people['ada'], people['ben'], people['cy'], people['sphere']
    status, made = put_on(ben, sphere)                      # any member may
    assert status == 201, made
    assert made['host']['id'] == str(sphere) and made['times'][0]['day'] == SOON[:10]

    assert [e['id'] for e in ada.get(f'/api/events?group={sphere}')[1]['events']] == [made['id']]
    assert ada.told('event_new')[0]['link'] == f"/event?id={made['id']}"
    assert cy.get(f"/api/events/{made['id']}")[0] == 404
    assert made['id'] not in str(cy.get('/api/events')[1])
    assert cy.post(f"/api/events/{made['id']}/reply", {'day': SOON[:10], 'answer': 'going'})[0] == 404
    assert put_on(cy, sphere)[0] == 403


def test_with_no_group_its_for_everyone(people):
    status, made = put_on(people['ada'])
    assert status == 201, made
    assert people['cy'].get(f"/api/events/{made['id']}")[0] == 200


def test_whos_coming_and_who_hears_of_changes(people):
    ada, ben, sphere = people['ada'], people['ben'], people['sphere']
    made = put_on(ada, sphere, repeats='weekly')[1]
    day = made['times'][1]['day']
    status, seen = ben.post(f"/api/events/{made['id']}/reply", {'day': day, 'answer': 'going'})
    assert status == 200, seen
    second = seen['times'][1]
    assert (second['going'], second['my_answer']) == (1, 'going') and second['people'][0]['id'] == str(ben.id)
    assert seen['times'][0]['going'] == 0                   # attendance is for one date

    assert ben.client.patch(f"/api/events/{made['id']}", headers=ben.headers, json={'title': 'Mine'}).status_code == 403
    r = ada.client.patch(f"/api/events/{made['id']}", headers=ada.headers, json={'starts': SOON[:11] + '18:30'})
    assert r.status_code == 200, r.get_json()
    assert len(ben.told('event_changed')) == 1

    status, after = ada.post(f"/api/events/{made['id']}/cancel", {'day': day})
    assert status == 200 and after['times'][1]['skipped'] is True
    assert ada.post(f"/api/events/{made['id']}/cancel", {'day': day})[0] == 200     # saying it twice
    assert len(ben.told('event_changed')) == 2
    assert ben.post(f"/api/events/{made['id']}/reply", {'day': day, 'answer': 'maybe'})[0] == 409
    assert ben.post(f"/api/events/{made['id']}/reply", {'day': day, 'answer': None})[0] == 200


def test_cancelled_leaves_the_list_and_keeps_its_page(people):
    ada, ben, sphere = people['ada'], people['ben'], people['sphere']
    made = put_on(ada, sphere)[1]
    assert ben.post(f"/api/events/{made['id']}/cancel", {})[0] == 403
    assert ada.post(f"/api/events/{made['id']}/cancel", {})[1]['cancelled'] is True
    assert ada.get(f'/api/events?group={sphere}')[1]['events'] == []
    assert ben.get(f"/api/events/{made['id']}")[1]['cancelled'] is True


def test_refuses_what_is_no_event(people):
    ada = people['ada']
    for wrong in ({'title': ''}, {'starts': 'Tuesday'}, {'starts': '2020-01-01T10:00'}, {'tz': 'Mars/Base'},
                  {'length_min': 5}, {'length_min': '60'}, {'repeats': 'daily'}, {'repeats': 'weekly', 'until': '2020-01-01'},
                  {'starts': '9999-12-31T23:59'}, {'title': 'x' * 200}, {'tz': 'Factory'},
                  {'starts': '0001-01-01T00:00', 'tz': 'Asia/Tokyo', 'repeats': 'weekly'}):
        assert put_on(ada, **wrong)[0] == 400, wrong
    made = put_on(ada)[1]
    for body in ({'day': '2020-01-01', 'answer': 'going'}, {'day': SOON[:10], 'answer': 'sure'}, {'day': SOON[:10]}):
        assert ada.post(f"/api/events/{made['id']}/reply", body)[0] == 400, body


def test_who_left_the_sphere_is_outside_its_events(people):
    ada, ben, sphere = people['ada'], people['ben'], people['sphere']
    bens, adas = put_on(ben, sphere)[1], put_on(ada, sphere)[1]
    assert ben.post(f"/api/events/{adas['id']}/reply", {'day': SOON[:10], 'answer': 'going'})[0] == 200
    assert ben.post(f'/api/spheres/{sphere}/leave')[0] == 200

    assert ben.get(f"/api/events/{bens['id']}")[0] == 404       # Ben's own making is no pass
    r = ben.client.patch(f"/api/events/{bens['id']}", headers=ben.headers, json={'title': 'Still mine'})
    assert r.status_code == 404
    assert ada.post(f"/api/events/{adas['id']}/cancel", {})[0] == 200
    assert ben.told('event_changed') == []


def test_a_group_hears_of_three_events_a_day_from_one_member(people):
    ada, ben, sphere = people['ada'], people['ben'], people['sphere']
    for n in range(5):
        assert put_on(ben, sphere, title=f'Test night {n}')[0] == 201
    assert len(ada.told('event_new')) == 3
    assert len(ada.get(f'/api/events?group={sphere}')[1]['events']) == 5


def test_an_events_place_and_spot(people):
    ada, ben = people['ada'], people['ben']
    made = put_on(ada, people['sphere'])[1]
    path = f"/api/places/events/{made['id']}"
    place = {'place': {'lat': -40.123456, 'lon': -20.654321, 'precision': 'exact', 'label': 'Test hall'}}
    assert ben.post(path, place)[0] == 403
    assert ada.post(path, place)[0] == 200
    seen = ben.get(f"/api/events/{made['id']}")[1]
    assert seen['location'] == 'Test hall' and seen['point'] == {'lat': -40.123456, 'lon': -20.654321}


def test_an_events_picture_is_only_for_who_sees_it(people, monkeypatch):
    from app.utils import ai_pictures, image_store
    monkeypatch.setattr(image_store, 'store', lambda data, kind='banner': (None, data))     # not into the bucket
    monkeypatch.setattr(ai_pictures, 'note_upload', lambda data, key: None)
    ada, cy = people['ada'], people['cy']
    made = put_on(ada, people['sphere'])[1]
    path = f"/api/events/{made['id']}/image"
    r = ada.client.post(path, headers=ada.headers, data={'image': (io.BytesIO(PNG_1PX), 'hall.png')},
                        content_type='multipart/form-data')
    assert r.status_code == 200, r.get_json()
    r = ada.client.get(path, headers=ada.headers)
    assert r.status_code == 200 and 'private' in r.headers['Cache-Control']
    assert cy.client.get(path, headers=cy.headers).status_code == 404
    assert cy.client.application.test_client().get(path).status_code == 401


def test_the_distance_from_me(people):
    ada, ben = people['ada'], people['ben']
    made = put_on(ada)[1]
    for who, path, lat in ((ada, f"/api/places/events/{made['id']}", -40.1), (ben, f'/api/places/users/{ben.id}', -40.3)):
        status, body = who.post(path, {'place': {'lat': lat, 'lon': -20.6, 'precision': '1km', 'label': 'Test spot'}})
        assert status == 200, body
    assert ben.get(f"/api/events/{made['id']}")[1]['distance'] is not None
    listed = next(e for e in ben.get('/api/events')[1]['events'] if e['id'] == made['id'])
    assert listed['distance'] is not None and listed['upcoming']['day'] == SOON[:10]


# -- Announcements -----------------------------------------------------------
def test_managers_announce_and_members_read(api, people):
    ada, ben, cy, sphere = people['ada'], people['ben'], people['cy'], people['sphere']
    path = f'/api/announcements/{sphere}'
    assert ben.post(path, {'text': 'Not mine to announce'})[0] == 403
    status, made = ada.post(path, {'text': 'The hall key is at number 12'})
    assert status == 201, made
    seen = ben.get(path)[1]
    assert seen['announcements'][0]['text'] == 'The hall key is at number 12' and seen['can_announce'] is False
    told, = ben.told('announcement')
    assert 'key' not in told['message']                     # not its words
    assert cy.get(path)[0] == 404

    assert ben.post('/api/reports', {'kind': 'announcement', 'id': made['id'], 'group_id': str(sphere)})[0] == 201
    mine = next(r for r in api.get('/api/admin/reports', who='admin')[1]['reports'] if r['item_id'] == made['id'])
    assert mine['excerpt'] == 'The hall key is at number 12' and mine['removable'] is True
    assert api.post(f"/api/admin/reports/{mine['id']}", who='admin', json={'status': 'handled', 'remove': True})[0] == 200
    assert ben.get(path)[1]['announcements'] == []


def test_a_member_cant_remove_the_managers(people):
    ada, ben, sphere = people['ada'], people['ben'], people['sphere']
    made = ada.post(f'/api/announcements/{sphere}', {'text': 'Bins go out on Monday'})[1]
    path = f"/api/announcements/{sphere}/{made['id']}"
    assert ben.client.delete(path, headers=ben.headers).status_code == 403
    assert ada.client.delete(path, headers=ada.headers).status_code == 200


# -- Invitations ------------------------------------------------------------
def test_a_link_brings_someone_into_the_group(app, people):
    ben, cy, sphere = people['ben'], people['cy'], people['sphere']
    status, made = ben.post('/api/invites', {'group_id': str(sphere)})      # open: any member may
    assert status == 201, made
    code = made['path'].split('#')[1]
    looked = app.test_client().post('/api/invites/look', json={'code': code})       # whoever holds it
    assert looked.status_code == 200 and looked.get_json()['group']['id'] == str(sphere)
    assert code not in str(ben.get('/api/invites')[1])

    for _ in range(2):
        assert cy.post('/api/invites/accept', {'code': code})[0] == 200
    assert cy.get(f'/api/announcements/{sphere}')[0] == 200     # in
    assert len(ben.told('invite_accepted')) == 1


def test_where_joining_needs_approval_only_managers_invite(people):
    ada, ben, sphere = people['ada'], people['ben'], people['sphere']
    early = ben.post('/api/invites', {'group_id': str(sphere)})[1]['path'].split('#')[1]
    r = ada.client.patch(f'/api/spheres/{sphere}', headers=ada.headers, json={'join_policy': 'approval'})
    assert r.status_code == 200, r.get_json()
    assert ben.post('/api/invites', {'group_id': str(sphere)})[0] == 403
    assert people['cy'].post('/api/invites/accept', {'code': early})[0] == 404     # and the older one stops
    assert ada.post('/api/invites', {'group_id': str(sphere)})[0] == 201


def test_a_managers_link_is_the_approval(db, people):
    ada, cy, sphere = people['ada'], people['cy'], people['sphere']
    r = ada.client.patch(f'/api/spheres/{sphere}', headers=ada.headers, json={'join_policy': 'approval'})
    assert r.status_code == 200, r.get_json()
    assert cy.post(f'/api/spheres/{sphere}/join')[0] == 202      # waiting
    code = ada.post('/api/invites', {'group_id': str(sphere)})[1]['path'].split('#')[1]
    assert cy.post('/api/invites/accept', {'code': code})[0] == 200
    row = db.execute('SELECT participants, member_roles FROM spheres WHERE sphere_id = %s', [sphere]).one()
    assert cy.id in row.participants and (row.member_roles or {}).get(cy.id) != 'pending'


def test_an_outsider_cant_invite_in(people):
    assert people['cy'].post('/api/invites', {'group_id': str(people['sphere'])})[0] == 403


def test_revoked_used_up_or_blocked_is_the_same_answer(people, monkeypatch):
    ada, ben, cy = people['ada'], people['ben'], people['cy']
    made = ada.post('/api/invites', {})[1]
    code = made['path'].split('#')[1]
    assert ada.post(f'/api/blocks/{cy.id}', {'blocked': True})[0] == 200
    status, blocked = cy.post('/api/invites/accept', {'code': code})
    assert status == 404
    assert ben.post('/api/invites/accept', {'code': code})[0] == 200
    assert ada.get('/api/invites')[1][0]['joined'] == 0 and ada.told('invite_accepted') == []   # Ben was here already
    monkeypatch.setattr(invites, 'MOST_USES', 0)
    assert cy.post('/api/invites/look', {'code': code})[1] == blocked
    assert ben.post(f"/api/invites/{made['id']}/revoke")[0] == 404      # not Ben's
    assert ada.post(f"/api/invites/{made['id']}/revoke")[0] == 200
    assert ada.get('/api/invites')[1] == []


def test_signing_up_to_logosphere_with_one(app, people, new_member):
    ada = people['ada']
    code = ada.post('/api/invites', {})[1]['path'].split('#')[1]
    r = app.test_client().post('/api/register', json={
        'name': 'Test Invited', 'email': new_member, 'password': PERSON_PASSWORD, 'invite': code})
    assert r.status_code == 200, r.get_json()
    assert len(ada.told('invite_accepted')) == 1 and ada.get('/api/invites')[1][0]['joined'] == 1


def test_signing_up_with_one(app, db, people, new_member):
    ada, sphere = people['ada'], people['sphere']
    code = ada.post('/api/invites', {'group_id': str(sphere)})[1]['path'].split('#')[1]
    r = app.test_client().post('/api/register', json={
        'name': 'Test Invited', 'email': new_member, 'password': PERSON_PASSWORD, 'invite': code})
    assert r.status_code == 200, r.get_json()
    uid = uuid.UUID(str(r.get_json()['user_id']))
    assert uid in db.execute('SELECT participants FROM spheres WHERE sphere_id = %s', [sphere]).one().participants
    assert r.get_json()['invited_to']['id'] == str(sphere)
    assert len(ada.told('invite_accepted')) == 1


def test_signing_up_with_one_by_email(app, db, people, new_member, monkeypatch):
    import re
    ada, sphere = people['ada'], people['sphere']
    code = ada.post('/api/invites', {'group_id': str(sphere)})[1]['path'].split('#')[1]
    sent = []
    monkeypatch.setattr(mailer, 'enabled', lambda: True)
    monkeypatch.setattr(mailer, 'deliverable', lambda address: True)
    monkeypatch.setattr(mailer, 'queue', lambda job, *args: job(*args))
    monkeypatch.setattr(mailer, 'send', lambda to, letter, tag, headers=None: sent.append((to, letter)) or True)
    client = app.test_client()
    assert client.post('/api/register', json={'name': 'Test Invited', 'email': new_member, 'invite': code}).status_code == 200
    token = re.search(r'#token=([\w-]+)', next(m for to, m in sent if to == new_member).text).group(1)
    r = client.post('/api/register/confirm', json={'token': token, 'password': PERSON_PASSWORD})
    assert r.status_code == 200, r.get_json()
    uid = uuid.UUID(str(r.get_json()['user_id']))
    assert uid in db.execute('SELECT participants FROM spheres WHERE sphere_id = %s', [sphere]).one().participants
    assert r.get_json()['invited_to']['id'] == str(sphere)


# -- A deleted group -----------------------------------------------------------
def test_a_deleted_group_takes_its_own_along(api, db, people):
    ada, ben, sphere = people['ada'], people['ben'], people['sphere']
    made = put_on(ada, sphere)[1]
    assert ben.post(f"/api/events/{made['id']}/reply", {'day': SOON[:10], 'answer': 'going'})[0] == 200
    assert ada.post(f'/api/announcements/{sphere}', {'text': 'The last word'})[0] == 201
    assert ada.post('/api/invites', {'group_id': str(sphere)})[0] == 201

    assert api.delete(f'/api/admin/spheres/{sphere}', who='admin')[0] == 200
    assert [n['link'] for n in ben.told('event_changed')] == ['/events']
    event = uuid.UUID(made['id'])
    for table in ('events', 'event_replies'):
        assert not list(db.execute(f'SELECT event_id FROM {table} WHERE event_id = %s', [event]))
    assert not list(db.execute('SELECT group_id FROM announcements WHERE group_id = %s', [sphere]))
    assert ada.get('/api/invites')[1] == []


# -- Accounts -----------------------------------------------------------------
def test_export_and_leaving(people):
    ada, ben = people['ada'], people['ben']
    made = put_on(ben)[1]
    assert ben.post(f"/api/events/{made['id']}/reply", {'day': SOON[:10], 'answer': 'going'})[0] == 200
    assert ben.post('/api/invites', {})[0] == 201
    data = ben.client.get('/api/account/export', headers=ben.headers).get_json(force=True)
    assert data['events']['made'][0]['id'] == made['id'] and data['events']['replies'][0]['answer'] == 'going'
    assert len(data['invitations']) == 1 and data['announcements'] == []

    assert ben.post('/api/account/delete', {'password': PERSON_PASSWORD})[0] == 200
    left = ada.get(f"/api/events/{made['id']}")[1]
    assert left['cancelled'] is True and left['times'][0]['going'] == 0 and left['location'] is None
