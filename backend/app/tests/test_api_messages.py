# Private messages, blocking and reporting. The named demo accounts are AI
# personas now, so these people are made for the test and removed after it.
import re
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

import pytest

from conftest import PERSON_PASSWORD
from app.models.notification import Notification
from app.utils import messaging

APP = Path(__file__).resolve().parents[1]


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


@pytest.fixture
def with_marie(api, db, people, keep_rows):
    """Ada joins Marie's demo spheres, to write to her. Their talk and Marie's notifications go afterwards."""
    from app.models.spheres import Sphere
    for sid in [s.sphere_id for s in Sphere.get_all() if s.is_demo]:
        keep_rows('spheres', sphere_id=sid)
    marie = uuid.UUID(api.uid('marie'))
    before = {r.notification_id for r in db.execute('SELECT notification_id FROM notifications WHERE user_id = %s', [marie])}
    yield marie
    db.execute('DELETE FROM direct_messages WHERE conversation_id = %s', [messaging.conversation(people['ada'].id, marie)])
    for who, other in ((marie, people['ada'].id), (people['ada'].id, marie)):
        db.execute('DELETE FROM message_inbox WHERE user_id = %s AND other_id = %s', [who, other])
    for r in list(db.execute('SELECT created_at, notification_id FROM notifications WHERE user_id = %s', [marie])):
        if r.notification_id not in before:
            db.execute('DELETE FROM notifications WHERE user_id = %s AND created_at = %s AND notification_id = %s',
                       [marie, r.created_at, r.notification_id])


def test_personas_answer_but_never_start(api, people, with_marie):
    ada, ben, marie = people['ada'], people['ben'], with_marie
    joe = api.uid('joe')
    # Without anything in common there is still nothing to write about.
    assert say(ada, SimpleNamespace(id=marie), 'Hello')[0] == 403
    assert ada.post('/api/demo/join')[0] == 200
    assert ada.get(f'/api/messages/{marie}')[1]['can_send'] is True
    assert say(ada, SimpleNamespace(id=marie), 'Hello Marie, is the shed still a mess?')[0] == 201
    assert [n['type'] for n in api.get('/api/notifications', who='marie')[1]['notifications']][:1] == ['message']
    # Marie answers Ada, who wrote; she can't start with Ben, nor write to another persona.
    assert api.post(f'/api/messages/{ada.id}', who='marie', json={'text': 'Still a mess, come and help.'})[0] == 201
    assert api.post(f'/api/messages/{ben.id}', who='marie', json={'text': 'Hello'})[0] == 403
    status, body = api.post(f'/api/messages/{joe}', who='marie', json={'text': 'Hello'})
    assert status == 403 and body['message'] == messaging.PERSONA
    assert [m['text'] for m in ada.get(f'/api/messages/{marie}')[1]['messages']][-1] == 'Still a mess, come and help.'
    # A block stops the answers too.
    assert ada.post(f'/api/blocks/{marie}', {'blocked': True})[0] == 200
    assert api.post(f'/api/messages/{ada.id}', who='marie', json={'text': 'Hello again'})[0] == 403
    assert ada.post(f'/api/blocks/{marie}', {'blocked': False})[0] == 200


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


def test_reporting_what_ai_help_gave(api, people):
    ada = people['ada']
    said = 'Cares about: shouting at the neighbours'
    assert ada.post('/api/reports', {'kind': 'ai', 'id': 'value_card', 'excerpt': said, 'note': 'Unkind'})[0] == 201
    assert ada.post('/api/reports', {'kind': 'ai', 'id': 'value_card'})[0] == 404             # nothing to look at
    assert ada.post('/api/reports', {'kind': 'ai', 'id': 'poem', 'excerpt': said})[0] == 404  # no such AI help
    mine = [r for r in api.get('/api/admin/reports', who='admin')[1]['reports']
            if r['reporter']['id'] == str(ada.id) and r['kind'] == 'ai']
    assert [(r['item_id'], r['excerpt'], r['subject'], r['removable']) for r in mine] == [('value_card', said, None, False)]


def test_the_problem_flag_files_a_report_signed_in_or_out(api, people):
    ada = people['ada']
    said = {'category': 'Confusing', 'note': 'The map never loads',
            'context': {'screen': 'NearbyRoute', 'app': 'LogoSphere 0.4.0 (400)'}}
    assert ada.post('/api/problems', said)[0] == 201
    assert ada.post('/api/problems', {**said, 'note': '  '})[0] == 400                 # say what went wrong
    assert api.post('/api/problems', json={**said, 'note': 'Signed out', 'category': 'Whatever'})[0] == 201
    rows = [r for r in api.get('/api/admin/reports', who='admin')[1]['reports'] if r['kind'] == 'problem']
    mine = next(r for r in rows if r['note'] == 'The map never loads')
    assert mine['reporter']['id'] == str(ada.id) and mine['item_id'] == 'Confusing' and mine['subject'] is None
    assert 'screen: NearbyRoute' in mine['excerpt'] and mine['removable'] is False
    anon = next(r for r in rows if r['note'] == 'Signed out')
    assert anon['reporter'] is None and anon['item_id'] == 'Other'


# -- Accounts -------------------------------------------------------------------
def test_export_has_messages_and_leaving_keeps_the_others_copy(people):
    ada, ben = people['ada'], people['ben']
    assert say(ada, ben, 'Kept for both')[0] == 201
    assert ada.post(f"/api/blocks/{people['cy'].id}", {'blocked': True})[0] == 200
    r = ada.client.get('/api/account/export', headers=ada.headers)
    data = r.get_json(force=True)
    assert data['messages'][0]['messages'][0]['text'] == 'Kept for both'
    assert data['blocked'] == [str(people['cy'].id)]

    assert ada.post('/api/account/delete', {'password': PERSON_PASSWORD})[0] == 200
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


# -- About a group, an event, or something both can see --------------------------------
def test_about_a_group_reaches_its_founder(db, people):
    ada, ben, cy = people['ada'], people['ben'], people['cy']
    sphere = str(people['sphere'])          # Ada's; Ben is in it, Cy isn't
    assert ben.get(f'/api/spheres/{sphere}')[1]['contact']['id'] == str(ada.id)
    assert cy.get(f'/api/spheres/{sphere}')[1]['contact'] is None       # outside a private sphere: not who runs it
    assert say(cy, ada, about={'kind': 'sphere', 'id': sphere})[0] == 403
    db.execute('UPDATE spheres SET is_public = true WHERE sphere_id = %s', [people['sphere']])
    assert cy.get(f'/api/messages/{ada.id}?about=sphere:{sphere}')[1]['can_send'] is True
    status, body = say(cy, ada, 'May I join?', about={'kind': 'sphere', 'id': sphere})
    assert status == 201, body
    assert body['sent']['about'] == {'kind': 'sphere', 'id': sphere, 'title': 'Messages test sphere (delete me)',
                                     'link': f'/sphere?id={sphere}'}
    assert body['sent']['opening'] is None
    got, = ada.get(f'/api/messages/{cy.id}')[1]['messages']
    assert got['about']['link'] == f'/sphere?id={sphere}' and got['opening'] is None
    assert say(cy, ada, about={'kind': 'project', 'id': sphere})[0] == 201      # the wrong kind names nothing,
    assert ada.get(f'/api/messages/{cy.id}')[1]['messages'][-1]['about'] is None    # but they talk already


def test_about_an_event_reaches_its_host(people):
    ada, cy = people['ada'], people['cy']
    starts = (datetime.utcnow() + timedelta(days=9)).strftime('%Y-%m-%dT19:00')
    status, event = ada.post('/api/events', {'title': 'Messages test supper', 'starts': starts, 'tz': 'UTC'})
    assert status == 201, event
    assert cy.get(f"/api/messages/{ada.id}?about=event:{event['id']}")[1]['can_send'] is True
    assert say(cy, ada, 'Can I bring a friend?', about={'kind': 'event', 'id': event['id']})[0] == 201
    got, = ada.get(f'/api/messages/{cy.id}')[1]['messages']
    assert got['about'] == {'kind': 'event', 'id': event['id'], 'title': 'Messages test supper',
                            'link': f"/event?id={event['id']}"}


def test_naming_what_both_see_opens_nothing_new(people):
    ada, ben, cy = people['ada'], people['ben'], people['cy']
    oid = cy.post('/api/openings', {'type': 'offer', 'title': 'Messages test kettle', 'description': 'x'})[1]['service_id']
    listed = next(o for o in ada.get('/api/openings')[1] if o['id'] == oid)
    assert listed['contact_id'] == str(cy.id)           # cards in a list know whom to write to
    status, body = say(ada, ben, 'Shall we ask for it?', about={'kind': 'opening', 'id': oid})
    assert status == 201 and body['sent']['about']['title'] == 'Messages test kettle'
    assert body['sent']['opening'] == {'id': oid, 'title': 'Messages test kettle'}
    # Ada and Ben may talk anyway. Naming Cy's opening to Ben gives Ada nothing she lacked,
    # and naming it to Cy, who posted it, lets her start.
    assert say(ada, cy, 'Is it still there?', about={'kind': 'opening', 'id': oid})[0] == 201
