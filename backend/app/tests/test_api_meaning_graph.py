# The Meaning Graph over the API: who sees which cards, who judges, what
# counts as evidence. (The arithmetic's promises: test_closeness.py.)
import uuid

import pytest

from conftest import REPAIR_CAFE


@pytest.fixture
def people(app, db):
    """Three throwaway members: personas don't judge or make evidence, so the
    seeded accounts can't stand in. Everything they make goes afterwards."""
    made = []
    spheres = {r.sphere_id: set(r.participants or []) for r in db.execute('SELECT sphere_id, participants FROM spheres')}
    for n in range(3):
        email, client = f'test-graph-{uuid.uuid4().hex[:10]}@example.com', app.test_client()
        r = client.post('/api/register', json={'name': f'Graph Test {n}', 'email': email, 'password': f'{uuid.uuid4().hex}'})
        assert r.status_code == 200, r.get_json()
        uid = uuid.UUID(r.get_json()['user_id'])
        token = uuid.uuid4()
        db.execute("INSERT INTO sessions (session_id, user_email, user_id, creation_time, last_access_time, expire_at) "
                   "VALUES (%s, %s, %s, toTimestamp(now()), toTimestamp(now()), '2099-01-01T00:00:00Z')", [token, email, uid])
        made.append({'id': str(uid), 'uid': uid, 'token': token, 'client': app.test_client()})
    yield made
    ids = {p['uid'] for p in made}
    for r in list(db.execute('SELECT trail_id, created_at, ack_id, author_id FROM trail_acknowledgements')):
        if r.author_id in ids or r.trail_id in ids:
            db.execute('DELETE FROM trail_acknowledgements WHERE trail_id = %s AND created_at = %s AND ack_id = %s',
                       [r.trail_id, r.created_at, r.ack_id])
    for r in list(db.execute('SELECT pair, user_id FROM meaning_judgements')):
        if r.user_id in ids:
            db.execute('DELETE FROM meaning_judgements WHERE pair = %s AND user_id = %s', [r.pair, r.user_id])
    for r in list(db.execute('SELECT sphere_id, participants FROM spheres')):
        joined = ids & set(r.participants or []) - spheres.get(r.sphere_id, set())
        if joined:
            db.execute('UPDATE spheres SET participants = participants - %s WHERE sphere_id = %s', [list(joined), r.sphere_id])
    for p in made:
        db.execute('DELETE FROM sessions WHERE session_id = %s', [p['token']])
        for table in ('value_cards', 'notifications', 'users', 'user_credentials'):
            db.execute(f'DELETE FROM {table} WHERE user_id = %s', [p['uid']])


def call(person, method, path, json=None):
    r = person['client'].open(path, method=method, json=json, headers={'Authorization': f"Bearer {person['token']}"})
    return r.status_code, r.get_json(silent=True)


def new_card(person, title, care):
    status, card = call(person, 'POST', '/api/value_cards', {'title': title, 'care_about': care, 'frankl_mode': 'creative'})
    assert status == 201, card
    return card


def fresh_graph(person):
    from app.utils import meaning_graph
    meaning_graph.get_graph(fresh=True)
    status, graph = call(person, 'GET', '/api/meaning_graph')
    assert status == 200, graph
    return graph


def edge_of(graph, a, b):
    return next((e for e in graph['edges'] if {e['a'], e['b']} == {a, b}), None)


def test_the_graph_is_for_members_and_the_method_for_everyone(app):
    assert app.test_client().get('/api/meaning_graph').status_code == 401
    r = app.test_client().get('/api/meaning_graph/method')
    assert r.status_code == 200 and r.get_json()['formula'] and r.get_json()['families']


def test_you_see_only_cards_you_may_read(api):
    from app.utils import meaning_graph
    meaning_graph.get_graph(fresh=True)
    _, inside = api.get('/api/meaning_graph', who='marie')
    _, outside = api.get('/api/meaning_graph', who='elon')
    assert any(n['owner']['id'] == REPAIR_CAFE for n in inside['nodes'])
    assert all(n['owner']['id'] != REPAIR_CAFE for n in outside['nodes'])
    for graph in (inside, outside):
        ids = {n['id'] for n in graph['nodes']}
        assert all(e['a'] in ids and e['b'] in ids for e in graph['edges'])


def test_a_pair_is_as_close_whoever_looks(api):
    _, one = api.get('/api/meaning_graph', who='marie')
    _, two = api.get('/api/meaning_graph', who='david')
    mine = {(e['a'], e['b']): e['closeness'] for e in one['edges']}
    theirs = {(e['a'], e['b']): e['closeness'] for e in two['edges']}
    both = mine.keys() & theirs.keys()
    assert both and all(mine[p] == theirs[p] for p in both)


def test_a_reworded_card_is_the_same_node(people):
    a = people[0]
    card = new_card(a, 'Graph test quokkas', 'Quokkas and kettles')
    assert card['card_id'] in {n['id'] for n in fresh_graph(a)['nodes']}
    _, edited = call(a, 'PATCH', f"/api/value_cards/{card['card_id']}", {'title': 'Graph test quokkas, reworded'})
    node = next(n for n in fresh_graph(a)['nodes'] if n['id'] == card['card_id'])
    assert node['card']['card_id'] == edited['card_id'] and node['mine'] is True and node['can_judge'] is False


def test_any_version_of_a_card_finds_its_dot(people):
    a = people[0]
    card = new_card(a, 'Graph test wombats', 'Wombats and teapots')
    _, edited = call(a, 'PATCH', f"/api/value_cards/{card['card_id']}", {'title': 'Graph test wombats, reworded'})
    for asked in (card['card_id'], edited['card_id']):
        assert call(a, 'GET', f'/api/meaning_graph/card/{asked}') == (200, {'id': card['card_id']})
    assert call(a, 'GET', f'/api/meaning_graph/card/{uuid.uuid4()}')[0] == 404
    assert call(a, 'GET', '/api/meaning_graph/card/not-an-id')[0] == 404


def test_a_copy_remembers_where_it_came_from(people):
    a, b, _ = people
    source = new_card(a, 'Graph test lineage', 'Lanterns along the towpath')
    status, copy = call(b, 'POST', '/api/value_cards/clone', {'source': source, 'target_id': b['id']})
    assert status == 201
    edge = edge_of(fresh_graph(b), source['card_id'], copy['card_id'])
    assert edge['lineage'] is True and edge['closeness'] > 0.99


def test_judging(people, api):
    a, b, c = people
    one, two = new_card(a, 'Zinnias', 'Boiling kettles'), new_card(a, 'Lighthouses', 'Spotting otters')
    x, y = one['card_id'], two['card_id']
    path = '/api/meaning_graph/judgement'
    assert call(a, 'POST', path, {'a': x, 'b': y, 'close': True})[0] == 403           # their own cards
    assert api.post(path, who='marie', json={'a': x, 'b': y, 'close': True})[0] == 403    # a persona
    assert call(b, 'POST', path, {'a': x, 'b': x, 'close': True})[0] == 400
    assert call(b, 'POST', path, {'a': x, 'b': y, 'close': 'yes'})[0] == 400
    status, first = call(b, 'POST', path, {'a': x, 'b': y, 'close': True})
    assert status == 200 and first['edge']['my_judgement'] is True
    assert first['edge']['judges'] == 0 and first['edge']['closeness'] == 0           # one judge isn't enough
    _, second = call(c, 'POST', path, {'a': x, 'b': y, 'close': True})
    assert second['edge']['judges'] == 2 and second['edge']['closeness'] == round(2 / 6, 4)
    _, back = call(c, 'POST', path, {'a': x, 'b': y, 'close': None})
    assert back['edge']['judges'] == 0 and back['edge']['my_judgement'] is None


def test_lived_takes_two_people(people):
    a, b, c = people
    x = new_card(a, 'Quinces', 'Stirring marmalade')['card_id']
    y = new_card(a, 'Timetables', 'Catching ferries')['card_id']
    ack = lambda who: call(who, 'POST', f"/api/trails/{a['id']}/acknowledgements", {'text': 'Both', 'card_ids': [x, y]})
    assert ack(b)[0] == 201 and ack(b)[0] == 201
    assert edge_of(fresh_graph(b), x, y) is None                                      # one person, however often
    assert ack(c)[0] == 201
    edge = edge_of(fresh_graph(b), x, y)
    assert edge['people'] == 2 and edge['closeness'] == 0.4
