# Places through the API: a person's point is theirs alone; others get words and bands.
# Every spot here is invented, out in the South Atlantic where no member is.
import json
import uuid

import pytest

from conftest import RIVERSIDE

LAT, LON = -40.123456, -20.654321


@pytest.fixture
def people(api, db, keep_rows):
    for who in ('marie', 'david', 'elon'):
        keep_rows('users', user_id=api.uid(who))
    return lambda who: f'/api/places/users/{api.uid(who)}'


def settle(api, path, who, lat=LAT, lon=LON, precision='exact', findable=False, label='Test Island'):
    return api.post(path, who=who, json={
        'place': {'lat': lat, 'lon': lon, 'precision': precision, 'label': label}, 'findable': findable})


def stored_place(db, table, key, value):
    row = db.execute(f'SELECT place FROM {table} WHERE {key} = %s', [uuid.UUID(value)]).one()
    return json.loads(row.place) if row.place else None


def gives_away_the_point(body):
    said = json.dumps(body)
    return any(bit in said for bit in ('40.1234', '20.6543', '"lat"', '"lon"', '"place"'))


def test_a_pin_is_rounded_before_it_is_stored(api, db, people):
    status, body = settle(api, people('marie'), 'marie', precision='5km')
    assert status == 200, body
    kept = stored_place(db, 'users', 'user_id', api.uid('marie'))
    assert (kept['lat'], kept['lon']) != (LAT, LON)
    assert abs(kept['lat'] - LAT) < 0.03 and kept['precision'] == '5km'
    assert body['place']['lat'] == kept['lat'] and body['findable'] is False


def test_nobody_else_gets_a_persons_point(api, db, people):
    assert settle(api, people('marie'), 'marie', findable=True)[0] == 200
    assert settle(api, people('david'), 'david', lat=LAT + 0.002)[0] == 200
    marie = api.uid('marie')
    assert api.get(people('marie'), who='david')[0] == 403
    assert api.get(people('marie'), who='admin')[0] == 403          # nor an administrator
    assert settle(api, people('marie'), 'admin')[0] == 403
    for path in (f'/api/users/{marie}', '/api/nearby', '/api/openings', '/api/spheres',
                 f'/api/spheres/{RIVERSIDE}', '/api/search?q=Marie'):
        for who in ('david', 'admin'):
            status, body = api.get(path, who=who)
            assert status == 200, path
            assert not gives_away_the_point(body), (path, who)
    assert api.get(f'/api/users/{marie}', who='david')[1]['location'] == 'Test Island'


def test_you_are_found_only_if_you_chose_to_be(api, people):
    marie = api.uid('marie')
    assert settle(api, people('david'), 'david', lat=LAT + 0.004)[0] == 200

    def found():
        status, body = api.get('/api/nearby?km=5', who='david')
        assert status == 200 and body['has_place'] is True
        return [p for p in body['people'] if p['id'] == marie]

    assert settle(api, people('marie'), 'marie')[0] == 200
    assert found() == []
    assert settle(api, people('marie'), 'marie', findable=True)[0] == 200
    assert found()[0]['distance'] == {'km': 2, 'text': 'Within 2 km'}
    assert settle(api, people('marie'), 'marie', lat=LAT + 3, findable=True)[0] == 200
    assert found() == []
    assert api.get('/api/nearby?km=3', who='david')[0] == 400


def test_the_findable_switch_alone_leaves_the_place(api, db, people):
    marie = api.uid('marie')
    assert settle(api, people('marie'), 'marie', precision='5km')[0] == 200
    before = stored_place(db, 'users', 'user_id', marie)
    status, body = api.post(people('marie'), who='marie', json={'findable': True})
    assert status == 200 and body['findable'] is True
    assert stored_place(db, 'users', 'user_id', marie) == {**before, 'findable': True}
    assert api.post(people('marie'), who='marie', json={'place': None})[0] == 200
    assert api.post(people('marie'), who='marie', json={'findable': True})[0] == 400


def test_no_place_no_nearby(api, db, people):
    db.execute('UPDATE users SET place = null WHERE user_id = %s', [uuid.UUID(api.uid('elon'))])
    status, body = api.get('/api/nearby', who='elon')
    assert status == 200 and body['has_place'] is False and body['people'] == []
    country = {'lat': LAT, 'lon': LON, 'precision': 'country'}
    db.execute('UPDATE users SET place = %s WHERE user_id = %s', [json.dumps(country), uuid.UUID(api.uid('elon'))])
    assert api.get('/api/nearby', who='elon')[1]['has_place'] is False      # too rough to be near anything


def test_new_words_let_go_of_the_old_point(api, db, people):
    marie = api.uid('marie')
    assert settle(api, people('marie'), 'marie', findable=True)[0] == 200
    hdr = api._hdr('marie')
    assert api.client.post('/api/updateuser', headers=hdr, data={'location': 'Test Island'},
                           content_type='multipart/form-data').status_code == 200
    assert stored_place(db, 'users', 'user_id', marie)              # the same words: it stays
    assert api.client.post('/api/updateuser', headers=hdr, data={'location': 'Elsewhere'},
                           content_type='multipart/form-data').status_code == 200
    assert stored_place(db, 'users', 'user_id', marie) is None
    assert api.get(people('marie'), who='marie')[1] ['place'] == {'label': 'Elsewhere'}


def test_words_alone_and_none_at_all(api, db, people):
    status, body = api.post(people('marie'), who='marie', json={'place': {'label': ' The  hills '}, 'findable': True})
    assert status == 200 and body == {'id': api.uid('marie'), 'place': {'label': 'The hills'}, 'findable': False}
    assert api.post(people('marie'), who='marie', json={'place': None})[1]['place'] is None
    assert api.get(f'/api/users/{api.uid("marie")}', who='david')[1]['location'] is None


def test_refuses_what_is_no_place(api, people):
    for place in ('Melbourne', [1, 2], {'lat': 91, 'lon': 0, 'label': 'x'}, {'lat': '1', 'lon': 2, 'label': 'x'},
                  {'lat': 1, 'label': 'x'}, {'lat': 1, 'lon': 2}, {'lat': 1, 'lon': 2, 'label': 'x', 'precision': 'town'},
                  {'lat': 1, 'lon': 2, 'label': 'x', 'precision': ['1km']}, {'id': 987654321}):
        assert api.post(people('marie'), who='marie', json={'place': place})[0] == 400, place
    assert api.post(people('marie'), who='marie', json={})[0] == 400
    assert api.post('/api/places/planets/' + str(uuid.uuid4()), who='marie', json={'place': None})[0] == 404
    assert api.post('/api/places/spheres/' + str(uuid.uuid4()), who='admin', json={'place': None})[0] == 404


@pytest.fixture
def opening(api, db):
    status, body = api.post('/api/openings', who='david', json={
        'type': 'offer', 'title': 'Place test opening', 'sphere_id': RIVERSIDE})
    assert status == 201, body
    made = [body['service_id']]
    yield made[0], made
    for sid in made:
        for table in ('services', 'opening_acceptances', 'opening_likes'):
            db.execute(f'DELETE FROM {table} WHERE service_id = %s', [uuid.UUID(sid)])


def test_an_opening_shows_its_spot_only_when_exact(api, db, people, opening):
    oid, _ = opening
    path = f'/api/places/openings/{oid}'
    assert settle(api, people('marie'), 'marie', lat=LAT + 0.005)[0] == 200
    assert settle(api, path, 'marie')[0] == 403                     # not hers
    assert settle(api, path, 'david', precision='1km', label='By the jetty')[0] == 200

    status, seen = api.get(f'/api/openings/{oid}', who='marie')
    assert status == 200 and seen['location'] == 'By the jetty' and seen['point'] is None
    assert seen['distance']['km'] == 2
    assert not gives_away_the_point({k: v for k, v in seen.items() if k != 'point'})
    listed = [o for o in api.get('/api/openings', who='marie')[1] if o['service_id'] == oid][0]
    assert listed['distance']['km'] == 2 and 'point' not in listed

    assert settle(api, path, 'david', precision='exact', label='By the jetty')[0] == 200
    assert api.get(f'/api/openings/{oid}', who='marie')[1]['point'] == {'lat': LAT, 'lon': LON}
    assert 'point' not in [o for o in api.get('/api/openings', who='marie')[1] if o['service_id'] == oid][0]


def test_an_opening_without_a_place_is_as_near_as_its_sphere(api, people, opening, keep_rows):
    oid, _ = opening
    keep_rows('spheres', sphere_id=RIVERSIDE)
    assert settle(api, f'/api/places/spheres/{RIVERSIDE}', 'elon')[0] == 403
    assert settle(api, f'/api/places/spheres/{RIVERSIDE}', 'admin', precision='1km', label='Test Riverside')[0] == 200
    assert settle(api, people('marie'), 'marie')[0] == 200
    assert api.get(f'/api/openings/{oid}', who='marie')[1]['distance']['km'] == 2
    sphere = api.get(f'/api/spheres/{RIVERSIDE}', who='marie')[1]
    assert sphere['location'] == 'Test Riverside' and sphere['point'] is None and sphere['distance']['km'] == 2
    nearby = api.get('/api/nearby', who='marie')[1]
    assert RIVERSIDE in [s['id'] for s in nearby['spheres']]


def test_where_it_was_agreed_stays_with_that_version(api, db, opening):
    oid, made = opening
    path = f'/api/places/openings/{oid}'
    assert settle(api, path, 'david', label='By the jetty')[1]['id'] == oid     # nobody took it up yet
    db.execute("INSERT INTO opening_acceptances (service_id, accepter_id, accepter_name, status) "
               "VALUES (%s, %s, 'Marie', 'confirmed')", [uuid.UUID(oid), uuid.UUID(api.uid('marie'))])
    assert settle(api, path, 'david', label='By the jetty')[1]['id'] == oid     # the same place
    status, body = settle(api, path, 'david', lat=LAT + 1, label='By the pier')
    assert status == 200, body
    made.append(body['id'])
    assert body['id'] != oid and body['place']['label'] == 'By the pier'
    old = api.get(f'/api/openings/{oid}', who='david')[1]
    assert old['location'] == 'By the jetty' and old['point'] == {'lat': LAT, 'lon': LON}
    assert api.get(f"/api/openings/{body['id']}", who='david')[1]['location'] == 'By the pier'


def test_a_private_spheres_exact_spot_is_for_those_inside(api, db):
    status, made = api.post('/api/spheres', who='admin', json={'name': 'Places test sphere (delete me)', 'description': 'x'})
    assert status == 201, made
    sid = made['sphere_id']
    try:
        assert settle(api, f'/api/places/spheres/{sid}', 'admin')[0] == 200
        assert api.get(f'/api/spheres/{sid}', who='admin')[1]['point'] == {'lat': LAT, 'lon': LON}
        outside = api.get(f'/api/spheres/{sid}', who='elon')[1]
        assert outside['location'] == 'Test Island' and outside['point'] is None
    finally:
        db.execute('DELETE FROM spheres WHERE sphere_id = %s', [uuid.UUID(sid)])


def test_searching_is_for_members_and_fine_without_data(app, api, monkeypatch, tmp_path):
    monkeypatch.setenv('PLACES_DB', str(tmp_path / 'none.sqlite'))
    status, body = api.post('/api/places/search', who='marie', json={'q': 'Bigton'})
    assert status == 200 and body['available'] is False and body['results'] == [] and body['attribution']['url']
    assert api.post('/api/places/nearest', who='marie', json={'lat': LAT, 'lon': LON})[0] == 200
    c = app.test_client()
    for path in ('/api/places/search', '/api/places/nearest'):
        assert c.post(path, json={'q': 'x'}).status_code == 401
    assert c.get('/api/nearby').status_code == 401


def test_your_export_has_your_place(api, people):
    assert settle(api, people('marie'), 'marie')[0] == 200
    status, data = api.get('/api/account/export', who='marie')
    assert status == 200 and data['profile']['place']['lat'] == LAT
