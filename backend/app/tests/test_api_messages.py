# Private messages, blocking and reporting. The named demo accounts are AI
# personas now, so these people are made for the test and removed after it.
import re
import uuid
from pathlib import Path

import pytest

from app.models.notification import Notification
from app.utils import mailer, messaging, safety

PASSWORD = 'a-long-password-1'
APP = Path(__file__).resolve().parents[1]


class Person:
    def __init__(self, client, email, user_id, token):
        self.client, self.email, self.id = client, email, user_id
        self.headers = {'Authorization': f'Bearer {token}'}

    def get(self, path):
        r = self.client.get(path, headers=self.headers)
        return r.status_code, r.get_json(silent=True)

    def post(self, path, json=None):
        r = self.client.post(path, headers=self.headers, json=json if json is not None else {})
        return r.status_code, r.get_json(silent=True)

    def told(self, kind):
        return [n for n in self.get('/api/notifications')[1]['notifications'] if n['type'] == kind]


@pytest.fixture
def people(app, db, keep_rows, test_admin, monkeypatch):
    """Ada and Ben share only a sphere of their own; Cy shares nothing with either."""
    from app.models.spheres import Sphere
    used, run = set(), uuid.uuid4().hex

    def bucket(name):
        key = f'test:{run}:{name}'
        used.add(key)
        return key

    monkeypatch.setattr(mailer, '_bucket', bucket)              # never the real allowances
    monkeypatch.setattr(safety, 'administrators', lambda: [test_admin])     # never the real one's inbox
    sandboxes = Sphere.sandbox_ids()
    for sid in sandboxes:
        keep_rows('spheres', sphere_id=sid)
    made = {}
    for name in ('Ada', 'Ben', 'Cy'):
        client = app.test_client()
        email = f'test-{name.lower()}-{uuid.uuid4().hex[:10]}@example.com'
        r = client.post('/api/register', json={'name': f'Test {name}', 'email': email, 'password': PASSWORD})
        assert r.status_code == 200, r.get_json()
        uid = uuid.UUID(str(r.get_json()['user_id']))
        token = client.post('/api/login', json={'email': email, 'password': PASSWORD}).get_json()['session_id']
        made[name.lower()] = Person(client, email, uid, token)
        for sid in sandboxes:       # a sandbox would make every newcomer sphere-mates
            db.execute('UPDATE spheres SET participants = participants - %s WHERE sphere_id = %s', [[uid], sid])
    status, shared = made['ada'].post('/api/spheres', {'name': 'Messages test sphere (delete me)', 'description': 'x'})
    assert status == 201, shared
    sphere = uuid.UUID(shared['sphere_id'])
    assert made['ben'].post(f'/api/spheres/{sphere}/join')[0] in (200, 201)
    made['sphere'] = sphere
    yield made

    ids = {p.id for p in (made['ada'], made['ben'], made['cy'])}
    everyone = list(ids)
    for a in everyone:
        for b in everyone:
            if str(a) < str(b):
                db.execute('DELETE FROM direct_messages WHERE conversation_id = %s', [messaging.conversation(a, b)])
        for table in ('message_inbox', 'notifications', 'blocks', 'trail_acknowledgements'):
            key = 'trail_id' if table == 'trail_acknowledgements' else 'user_id'
            db.execute(f'DELETE FROM {table} WHERE {key} = %s', [a])
        db.execute('DELETE FROM follows WHERE follower_id = %s', [a])
        for table in ('users', 'user_credentials'):
            db.execute(f'DELETE FROM {table} WHERE user_id = %s', [a])
    for r in db.execute('SELECT session_id, user_id FROM sessions'):
        if r.user_id in ids:
            db.execute('DELETE FROM sessions WHERE session_id = %s', [r.session_id])
    for r in db.execute('SELECT report_id, reporter_id FROM reports'):
        if r.reporter_id in ids:
            db.execute('DELETE FROM reports WHERE report_id = %s', [r.report_id])
    for r in db.execute('SELECT service_id, provider_id FROM services'):
        if r.provider_id in ids:
            for table in ('services', 'opening_acceptances', 'opening_likes'):
                db.execute(f'DELETE FROM {table} WHERE service_id = %s', [r.service_id])
    db.execute('DELETE FROM spheres WHERE sphere_id = %s', [sphere])
    db.execute('DELETE FROM notifications WHERE user_id = %s', [test_admin])
    for key in used:
        db.execute('DELETE FROM mail_counts WHERE bucket = %s', [key])


def say(sender, to, text='Hello there', **more):
    return sender.post(f'/api/messages/{to.id}', {'text': text, **more})


# -- Messages ---------------------------------------------------------------------
def test_sphere_mates_talk_and_nobody_else_listens(api, people):
    ada, ben, cy = people['ada'], people['ben'], people['cy']
    status, body = say(ada, ben, 'Is the ladder free on Saturday?')
    assert status == 201, body
    assert body['sent']['mine'] is True

    status, theirs = ben.get(f'/api/messages/{ada.id}')
    assert status == 200 and [m['text'] for m in theirs['messages']] == ['Is the ladder free on Saturday?']
    assert theirs['messages'][0]['mine'] is False and theirs['can_send'] is True
    listed = ben.get('/api/messages')[1]
    assert listed['unread_count'] == 1 and listed['conversations'][0]['person']['id'] == str(ada.id)

    # Nobody else's view of either has it: not a stranger's, not an administrator's.
    for path in (f'/api/messages/{ada.id}', f'/api/messages/{ben.id}', '/api/messages'):
        for seen in (cy.get(path)[1], api.get(path, who='admin')[1]):
            assert 'ladder' not in str(seen), path


def test_a_notification_once_until_read_and_never_the_words(people):
    ada, ben = people['ada'], people['ben']
    for text in ('A very private first', 'and a second'):
        assert say(ada, ben, text)[0] == 201
    told, = ben.told('message')
    assert 'private' not in told['message'] and told['link'] == f'/messages?with={ada.id}'
    first, second = ben.get(f'/api/messages/{ada.id}')[1]['messages']
    assert ben.post(f'/api/messages/{ada.id}/read', {'up_to': first['id']})[1]['unread'] is True
    assert ben.post(f'/api/messages/{ada.id}/read', {'up_to': second['id']})[1]['unread'] is False
    assert ben.told('message') == [] and ben.get('/api/messages')[1]['unread_count'] == 0
    assert say(ada, ben, 'a third')[0] == 201 and len(ben.told('message')) == 1


def test_strangers_cant_start_unless_invited_somehow(db, people):
    ada, ben, cy = people['ada'], people['ben'], people['cy']
    status, body = say(cy, ada)
    assert status == 403 and body['message'] == messaging.NOT_ALLOWED
    assert cy.get(f'/api/users/{ada.id}')[1]['can_message'] is False
    assert ben.get(f'/api/users/{ada.id}')[1]['can_message'] is True

    assert ada.post(f'/api/users/{cy.id}/follow')[1]['following'] is True
    assert say(cy, ada)[0] == 201                                       # she follows them
    assert say(ada, cy)[0] == 201                                       # and answers carry on

    assert say(cy, ben)[0] == 403
    db.execute('UPDATE users SET place = %s WHERE user_id = %s',
               ['{"lat": -40.12, "lon": -20.65, "precision": "1km", "findable": true}', ben.id])
    assert say(cy, ben)[0] == 201                                       # he chose to be found


def test_about_an_opening(people):
    ada, cy = people['ada'], people['cy']
    status, made = ada.post('/api/openings', {'type': 'offer', 'title': 'Messages test ladder', 'description': 'x'})
    assert status == 201, made
    oid = made['service_id']
    assert cy.get(f'/api/openings/{oid}')[1]['contact_id'] == str(ada.id)
    assert cy.get(f'/api/messages/{ada.id}?opening={oid}')[1]['can_send'] is True
    assert say(cy, ada, 'Is it tall?', opening_id=oid)[0] == 201
    got, = ada.get(f'/api/messages/{cy.id}')[1]['messages']
    assert got['opening'] == {'id': oid, 'title': 'Messages test ladder'}


def test_an_opening_in_a_sphere_opens_nothing_to_outsiders(people):
    ada, cy = people['ada'], people['cy']
    oid = ada.post('/api/openings', {'type': 'offer', 'title': 'Inside only', 'sphere_id': str(people['sphere'])})[1]['service_id']
    assert say(cy, ada, opening_id=oid)[0] == 403


def test_everyone_who_responded_each_privately(people):
    ada, ben, cy = people['ada'], people['ben'], people['cy']
    oid = ada.post('/api/openings', {'type': 'offer', 'title': 'Messages test seedlings'})[1]['service_id']
    for person in (ben, cy):
        assert person.post(f'/api/openings/{oid}/accept')[0] == 200
    path = f'/api/openings/{oid}/message_respondents'
    assert ben.post(path, {'text': 'Not mine to send'})[0] == 403
    status, body = ada.post(path, {'text': 'Come by at ten'})
    assert status == 200 and body['sent'] == 2, body
    for person, other in ((ben, cy), (cy, ben)):
        assert [m['text'] for m in person.get(f'/api/messages/{ada.id}')[1]['messages']] == ['Come by at ten']
        assert str(other.id) not in str(person.get('/api/messages')[1])     # nobody learns who else responded


def test_personas_neither_read_nor_write(api, people):
    marie = api.uid('marie')
    status, body = people['ada'].post(f'/api/messages/{marie}', {'text': 'Hello'})
    assert status == 403 and body['message'] == messaging.PERSONA
    assert api.post(f"/api/messages/{people['ada'].id}", who='marie', json={'text': 'Hello'})[0] == 403


def test_refuses_what_isnt_a_message(people):
    ada, ben = people['ada'], people['ben']
    for text in ('', '   ', None, 7, 'x' * (messaging.TEXT_MAX + 1)):
        assert ada.post(f'/api/messages/{ben.id}', {'text': text})[0] == 400, text
    assert ada.get(f'/api/messages/{ben.id}?before=junk')[0] == 400
    assert ada.post(f'/api/messages/{ben.id}/read', {'up_to': str(uuid.uuid4())})[0] == 400
    assert ada.get(f'/api/messages/{ada.id}')[0] == 404
    assert ada.client.application.test_client().get('/api/messages').status_code == 401


def test_too_many_is_too_many(people, monkeypatch):
    monkeypatch.setattr(messaging, 'PER_HOUR', 2)
    ada, ben = people['ada'], people['ben']
    assert [say(ada, ben)[0] for _ in range(3)] == [201, 201, 429]


def test_older_ones_come_a_page_at_a_time(people, monkeypatch):
    ada, ben = people['ada'], people['ben']
    for n in range(3):
        assert say(ada, ben, f'number {n}')[0] == 201
    monkeypatch.setattr(messaging, 'PAGE', 2)
    page = ben.get(f'/api/messages/{ada.id}')[1]
    assert [m['text'] for m in page['messages']] == ['number 1', 'number 2'] and page['more'] is True
    older = ben.get(f"/api/messages/{ada.id}?before={page['messages'][0]['id']}")[1]
    assert [m['text'] for m in older['messages']] == ['number 0'] and older['more'] is False


# -- Blocking -------------------------------------------------------------------
def test_a_block_stops_it_all_and_isnt_told(db, people):
    ada, ben = people['ada'], people['ben']
    assert say(ben, ada)[0] == 201
    assert ben.post(f'/api/users/{ada.id}/follow')[1]['following'] is True
    oid = ada.post('/api/openings', {'type': 'offer', 'title': 'Block test'})[1]['service_id']

    assert ada.post(f'/api/blocks/{ben.id}', {'blocked': True})[1] == {'blocked': True}
    assert [b['id'] for b in ada.get('/api/blocks')[1]] == [str(ben.id)]
    assert ada.told('message') == [] and ada.told('new_follower') == []

    status, body = say(ben, ada)
    assert status == 403 and body['message'] == messaging.NOT_ALLOWED       # reads like any refusal
    assert 'block' not in body['message'].lower()
    assert say(ada, ben)[1]['message'] == messaging.YOU_BLOCKED
    seen = ben.get(f'/api/users/{ada.id}')[1]
    assert seen['blocked'] is False and seen['is_following'] is False and seen['can_message'] is False
    assert ben.post(f'/api/users/{ada.id}/follow')[0] == 403
    assert ben.post(f'/api/openings/{oid}/accept')[0] == 403
    assert ben.post(f'/api/trails/{ada.id}/acknowledgements', {'text': 'Hello again'})[0] == 403
    for person, lat in ((ada, -40.121), (ben, -40.122)):
        db.execute('UPDATE users SET place = %s WHERE user_id = %s',
                   [f'{{"lat": {lat}, "lon": -20.65, "precision": "1km", "findable": true}}', person.id])
    assert str(ben.id) not in str(ada.get('/api/nearby')[1])
    assert str(ada.id) not in str(ben.get('/api/nearby')[1])
    Notification.create(ada.id, ben.id, 'Test Ben', 'acknowledgement', 'x', '/')
    assert ada.told('acknowledgement') == []

    assert ada.post(f'/api/blocks/{ben.id}', {'blocked': False})[0] == 200
    assert say(ben, ada)[0] == 201
    assert str(ada.id) in str(ben.get('/api/nearby')[1])


def test_nobody_blocks_themselves(people):
    ada = people['ada']
    assert ada.post(f'/api/blocks/{ada.id}', {'blocked': True})[0] == 400
    assert ada.post(f'/api/blocks/{uuid.uuid4()}', {'blocked': True})[0] == 404
    assert ada.post(f"/api/blocks/{people['ben'].id}", {})[0] == 400


# -- Reporting --------------------------------------------------------------------
def test_a_reported_message_reaches_the_administrators_and_can_go(api, people):
    ada, ben, cy = people['ada'], people['ben'], people['cy']
    said = say(ben, ada, 'Something unkind')[1]['sent']['id']
    report = {'kind': 'message', 'id': said, 'person_id': str(ben.id), 'excerpt': 'made up by the client'}
    assert cy.post('/api/reports', report)[0] == 404                    # not their conversation
    assert ben.post('/api/reports', {**report, 'person_id': str(ada.id)})[0] == 404     # nor their own words
    assert ada.post('/api/reports', report)[0] == 201
    assert ada.get('/api/admin/reports')[0] == 403

    queue = api.get('/api/admin/reports', who='admin')[1]
    mine = next(r for r in queue['reports'] if r['item_id'] == said)
    assert mine['excerpt'] == 'Something unkind' and mine['subject']['id'] == str(ben.id)       # as the server read it
    assert mine['removable'] is True and queue['open'] >= 1

    status, _ = api.post(f"/api/admin/reports/{mine['id']}", who='admin',
                         json={'status': 'handled', 'remove': True, 'note': 'Removed'})
    assert status == 200
    assert ada.get(f'/api/messages/{ben.id}')[1]['messages'] == []
    assert ada.get('/api/messages')[1]['conversations'][0]['last']['text'] == messaging.REMOVED
    assert said not in str(api.get('/api/admin/reports', who='admin')[1])       # no longer waiting


def test_reporting_an_acknowledgement_or_a_person(api, people):
    ada, ben = people['ada'], people['ben']
    ack = ben.post(f'/api/trails/{ada.id}/acknowledgements', {'text': 'Not kind'})[1]['acknowledgement']
    ack_id = ack.get('ack_id') or ack.get('id')
    assert ada.post('/api/reports', {'kind': 'acknowledgement', 'id': ack_id, 'trail_id': str(ada.id)})[0] == 201
    assert ada.post('/api/reports', {'kind': 'person', 'id': str(ben.id)})[0] == 400        # say what happened
    assert ada.post('/api/reports', {'kind': 'person', 'id': str(ben.id), 'note': 'Keeps at it'})[0] == 201
    assert ada.post('/api/reports', {'kind': 'person', 'id': str(ada.id), 'note': 'Me'})[0] == 400
    rows = [r for r in api.get('/api/admin/reports', who='admin')[1]['reports'] if r['reporter']['id'] == str(ada.id)]
    assert sorted(r['kind'] for r in rows) == ['acknowledgement', 'person']


# -- Accounts -------------------------------------------------------------------
def test_export_has_messages_and_leaving_keeps_the_others_copy(people):
    ada, ben = people['ada'], people['ben']
    assert say(ada, ben, 'Kept for both')[0] == 201
    assert ada.post(f"/api/blocks/{people['cy'].id}", {'blocked': True})[0] == 200
    r = ada.client.get('/api/account/export', headers=ada.headers)
    data = r.get_json(force=True)
    assert data['messages'][0]['messages'][0]['text'] == 'Kept for both'
    assert data['blocked'] == [str(people['cy'].id)]

    assert ada.post('/api/account/delete', {'password': PASSWORD})[0] == 200
    left = ben.get(f'/api/messages/{ada.id}')[1]
    assert left['person']['name'] == 'A former member' and left['can_send'] is False
    assert [m['text'] for m in left['messages']] == ['Kept for both']


def test_an_email_address_never_stands_in_for_a_name(db, people):
    ada, ben = people['ada'], people['ben']
    db.execute('UPDATE users SET name = null, surname = null WHERE user_id = %s', [ben.id])
    assert ben.post(f'/api/users/{ada.id}/follow')[1]['following'] is True
    told, = ada.told('new_follower')
    assert ben.email not in str(told)
    # ...and no route falls back on one.
    for source in (APP / 'routes').glob('*.py'):
        assert not re.search(r'\bor \w+\.email\b', source.read_text(encoding='utf-8')), source.name
