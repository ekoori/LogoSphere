"""Members' phones get their notifications (app/utils/push): a phone is
registered at sign-in for that session, follows whoever signed in on it last,
and is dropped when Firebase no longer knows it or its session has ended."""
import uuid

import pytest

from app.utils import push


@pytest.fixture
def phones(api, db):
    """register(who) -> a test token registered for `who`; every row goes afterwards."""
    made = []

    def register(who):
        token = f'test-{uuid.uuid4().hex}'
        status, body = api.post('/api/push/devices', who=who, json={'token': token, 'platform': 'android'})
        assert status == 200 and body['registered'], body
        made.append(token)
        return token
    yield register
    for token in made:
        db.execute('DELETE FROM push_token_owner WHERE token = %s', [token])
        for who in ('marie', 'david'):
            db.execute('DELETE FROM push_devices WHERE user_id = %s AND token = %s', [uuid.UUID(api.uid(who)), token])


class Fcm:
    """Stands in for Firebase: keeps what it was sent, answers `status`."""
    def __init__(self):
        self.sent, self.status = [], 200

    def __call__(self, body):
        self.sent.append(body['message'])
        return self.status, '{}' if self.status < 300 else '{"error": {"status": "NOT_FOUND"}}'

    def to(self, token):
        return [m for m in self.sent if m['token'] == token]


class Inline:
    def submit(self, fn, *args):
        fn(*args)


@pytest.fixture
def fcm(monkeypatch):
    fake = Fcm()
    monkeypatch.setenv('FCM_CREDENTIALS', '/nonexistent/test-key.json')
    monkeypatch.setattr(push, '_post', fake)
    monkeypatch.setattr(push, '_pool', Inline())
    return fake


def _tokens(api, who):
    return [t for t, _ in push.devices(api.uid(who))]


def test_a_phone_follows_whoever_signed_in_on_it_last(api, phones):
    token = phones('marie')
    assert token in _tokens(api, 'marie')
    assert api.post('/api/push/devices', who='david', json={'token': token})[0] == 200
    assert token not in _tokens(api, 'marie') and token in _tokens(api, 'david')
    assert api.post('/api/push/devices/forget', who='david', json={'token': token})[0] == 200
    assert token not in _tokens(api, 'david')


def test_a_notification_reaches_the_members_phones(api, phones, fcm):
    token = phones('marie')
    push.notify(api.uid('marie'), 'David left you a receipt', link='/exchange?id=x1',
                kind='receipt_received', notification_id='n1')
    [msg] = fcm.to(token)
    assert msg['notification']['body'] == 'David left you a receipt'
    assert msg['data'] == {'link': '/exchange?id=x1', 'type': 'receipt_received', 'notification_id': 'n1'}
    assert msg['android']['notification']['channel_id'] == push.CHANNEL


def test_a_phone_firebase_no_longer_knows_is_dropped(api, phones, fcm):
    token = phones('marie')
    fcm.status = 404
    push.notify(api.uid('marie'), 'Hello')
    assert fcm.to(token) and token not in _tokens(api, 'marie')


def test_a_phone_whose_session_ended_gets_nothing(api, phones, fcm, db):
    token = phones('marie')
    db.execute('UPDATE push_devices SET session_id = %s WHERE user_id = %s AND token = %s',
               [uuid.uuid4(), uuid.UUID(api.uid('marie')), token])
    push.notify(api.uid('marie'), 'Hello')
    assert not fcm.to(token) and token not in _tokens(api, 'marie')


def test_registering_needs_a_token_and_a_known_platform(api):
    assert api.post('/api/push/devices', who='marie', json={'platform': 'android'})[0] == 400
    assert api.post('/api/push/devices', who='marie', json={'token': 't', 'platform': 'ios'})[0] == 400
