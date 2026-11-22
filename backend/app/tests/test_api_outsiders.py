# Every GET the API has, asked by someone outside: none gives away what is
# inside a private sphere, a message, an address or a point on the map.
# The people are conftest's: Ada and Ben share Ada's sphere; Cy is outside it.
import itertools
import re
from datetime import datetime, timedelta

import pytest

from app.utils import demo
from app.utils.search_vectors import invalidate_index

WORD = 'zqxvinside'                                     # in everything written inside
WHISPER = 'zqxvwhisper'                                 # in a private message
LAT, LON = -40.123456, -20.654321                       # open sea, where no member is
SKIP = ('/api/email/unsubscribe/<token>',)              # acts on a token


@pytest.fixture
def inside(db, people):
    ada, ben, sphere = people['ada'], people['ben'], str(people['sphere'])
    status, made = ada.post('/api/openings', {'type': 'offer', 'title': f'{WORD} ladder', 'description': f'{WORD} tall',
                                              'sphere_id': sphere})
    assert status == 201, made
    opening = made['service_id']
    assert ben.post(f'/api/openings/{opening}/accept')[0] == 200
    status, done = ada.post(f'/api/openings/{opening}/confirm', {'accepter_id': str(ben.id)})
    assert status == 200, done
    exchange = done['exchange_id']
    assert ada.post(f'/api/exchange/{exchange}/status', {'status': 'In Progress'})[0] == 200
    assert ada.post(f'/api/exchange/{exchange}/status', {'status': 'Finished'})[0] == 200
    status, said = ben.post(f'/api/exchange/{exchange}/comment', {'type': 'gratitude', 'text': f'{WORD} thanks'})
    assert status == 200, said
    starts = (datetime.utcnow() + timedelta(days=9)).strftime('%Y-%m-%dT19:00')
    status, event = ada.post('/api/events', {'title': f'{WORD} supper', 'starts': starts, 'tz': 'UTC', 'host_id': sphere})
    assert status == 201, event
    assert ada.post(f'/api/announcements/{sphere}', {'text': f'{WORD} bins'})[0] == 201
    assert ada.post(f'/api/messages/{ben.id}', {'text': f'{WORD} {WHISPER} hello'})[0] in (200, 201)
    status, placed = ada.post(f'/api/places/users/{ada.id}', {
        'place': {'lat': LAT, 'lon': LON, 'precision': 'exact', 'label': 'Test Island'}, 'findable': True})
    assert status == 200, placed
    invalidate_index()
    yield {**people, 'ids': [str(ada.id), str(ben.id), sphere, opening, exchange, event['id']]}
    for who in (ada, ben):
        for row in db.execute('SELECT exchange_id FROM meaning_trail WHERE user_id = %s', [who.id]):
            db.execute('DELETE FROM trail_acknowledgements WHERE trail_id = %s', [row.exchange_id])
        db.execute('DELETE FROM meaning_trail WHERE user_id = %s', [who.id])
    demo.forget()
    invalidate_index()


def addresses(app, ids):
    ada, _, sphere, opening, _, _ = ids
    queries = ('', '?q=ladder', '?q=thanks&kinds=opening,exchange,receipt,event,user', f'?group={sphere}',
               f'?opening={opening}', f'?around={ada}', '?status=all')
    for rule in app.url_map.iter_rules():
        if 'GET' not in rule.methods or rule.endpoint == 'static' or rule.rule in SKIP:
            continue
        parts = re.split('<[^>]+>', rule.rule)
        names = [name.split(':')[-1] for name in re.findall('<([^>]+)>', rule.rule)]
        if not names:
            for query in queries:
                yield rule.rule, rule.rule + query
            continue
        for values in itertools.product(*[('0',) if name == 'idx' else ids for name in names]):
            yield rule.rule, parts[0] + ''.join(value + rest for value, rest in zip(values, parts[1:]))


def test_outsiders_get_nothing_from_inside_by_any_route(app, inside):
    ada, ben, cy = inside['ada'], inside['ben'], inside['cy']
    visitor = app.test_client()                         # no cookie, no token
    secrets = [WORD, ada.email, ben.email, '40.1234', '20.6543', 'pbkdf2:', 'scrypt:',
               ada.headers['Authorization'].split()[1]]
    leaks, broke, insiders_saw = [], [], set()
    for rule, address in addresses(app, inside['ids']):
        for who, response in (('outsider', cy.client.get(address, headers=cy.headers)),
                              ('visitor', visitor.get(address))):
            if response.status_code >= 500:
                broke.append((who, rule, response.status_code))
            text = response.get_data(as_text=False).lower()
            for secret in secrets:
                if secret.lower().encode() in text:
                    leaks.append((who, rule, secret if secret in (WORD, '40.1234', '20.6543') else 'a credential or address'))
        if WORD.encode() in ben.client.get(address, headers=ben.headers).get_data().lower():
            insiders_saw.add(rule)
    assert not leaks, sorted(set(leaks))
    assert not broke, sorted(set(broke))
    # The sweep does reach what's inside: someone in there sees it by many routes.
    assert len(insiders_saw) >= 8, sorted(insiders_saw)


def test_administrators_get_no_point_and_no_private_message(app, api, inside):
    from conftest import USERS
    email, password = USERS['admin']
    admin = app.test_client()
    token = admin.post('/api/login', json={'email': email, 'password': password}).get_json()['session_id']
    held = []
    try:
        for rule, address in addresses(app, inside['ids']):
            text = admin.get(address, headers={'Authorization': f'Bearer {token}'}).get_data().lower()
            for secret in ('40.1234', '20.6543', WHISPER, 'pbkdf2:', 'scrypt:'):
                if secret.encode() in text:
                    held.append((rule, secret))
    finally:
        api.logout_token(token)
    assert not held, sorted(set(held))
