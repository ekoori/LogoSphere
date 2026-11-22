"""Your own account: changing your password, downloading your data, deleting
your account, leaving a group — and an admin's one-time password reset link.
Every test works on a throwaway account (new_member) and removes what it made."""
import uuid
from datetime import datetime, timedelta

import pytest

OLD = 'old-password-1'


def _auth(token):
    return {'Authorization': f'Bearer {token}'}


@pytest.fixture
def member(app, db, new_member):
    """A registered throwaway member: (email, user_id, sign_in). sign_in(password)
    returns (status, session token). Their sessions and cards go afterwards."""
    r = app.test_client().post('/api/register', json={'name': 'Test Member', 'email': new_member, 'password': OLD})
    assert r.status_code == 200, r.get_json()
    uid = r.get_json()['user_id']

    def sign_in(password=OLD):
        r = app.test_client().post('/api/login', json={'email': new_member, 'password': password})
        return r.status_code, (r.get_json() or {}).get('session_id')

    yield new_member, uid, sign_in
    for row in db.execute('SELECT session_id FROM sessions WHERE user_id = %s', [uuid.UUID(uid)]):
        db.execute('DELETE FROM sessions WHERE session_id = %s', [row.session_id])
    db.execute('DELETE FROM value_cards WHERE user_id = %s', [uuid.UUID(uid)])


def _active(app, token):
    r = app.test_client().get('/api/check_session', headers=_auth(token))
    return r.status_code == 200 and (r.get_json() or {}).get('status') == 'active'


def test_changing_your_password_keeps_this_session_and_ends_the_others(app, member):
    _, _, sign_in = member
    _, here = sign_in()
    _, there = sign_in()
    c = app.test_client()
    r = c.post('/api/account/password', headers=_auth(here), json={'current_password': 'not-it', 'new_password': 'new-password-2'})
    assert r.status_code == 403
    r = c.post('/api/account/password', headers=_auth(here), json={'current_password': OLD, 'new_password': 'short'})
    assert r.status_code == 400
    r = c.post('/api/account/password', headers=_auth(here), json={'current_password': OLD, 'new_password': 'new-password-2'})
    assert r.status_code == 200, r.get_json()
    assert r.get_json()['signed_out'] == 1
    assert _active(app, here)
    assert not _active(app, there)
    assert sign_in(OLD)[0] == 401
    assert sign_in('new-password-2')[0] == 200


def test_your_data_comes_whole_and_never_with_the_password(app, member):
    email, uid, sign_in = member
    _, token = sign_in()
    c = app.test_client()
    r = c.post('/api/value_cards', headers=_auth(token), json={'title': 'Care', 'care_about': 'Testing the export'})
    assert r.status_code == 201
    r = c.get('/api/account/export', headers=_auth(token))
    assert r.status_code == 200
    assert 'attachment' in r.headers['Content-Disposition']
    data = r.get_json()
    assert data['profile']['email'] == email
    assert data['profile']['user_id'] == uid
    assert [c['care_about'] for c in data['value_cards']] == ['Testing the export']
    for key in ('memberships', 'openings', 'exchanges', 'acknowledgements', 'following', 'followers', 'governance', 'notifications'):
        assert key in data
    text = r.get_data(as_text=True)
    assert token not in text
    assert 'pbkdf2:' not in text and 'scrypt:' not in text
    assert c.get('/api/account/export').status_code == 401


def test_simple_for_newcomers_and_the_choice_is_yours(app, db, api, member):
    _, uid, sign_in = member
    _, token = sign_in()
    c = app.test_client()

    def mine():
        return c.get('/api/check_session', headers=_auth(token)).get_json()['user_data']['ui_mode']

    def choose(body):
        return c.post('/api/account/preferences', headers=_auth(token), json=body)

    assert mine() == 'simple'
    r = choose({'ui_mode': 'advanced'})
    assert r.status_code == 200 and r.get_json() == {'ui_mode': 'advanced'}
    assert mine() == 'advanced'
    assert c.get('/api/account/export', headers=_auth(token)).get_json()['profile']['ui_mode'] == 'advanced'

    for bad in ({}, {'ui_mode': 'expert'}, {'ui_mode': ['simple']}, {'ui_mode': None}, ['simple']):
        assert choose(bad).status_code == 400, bad
    assert app.test_client().post('/api/account/preferences', json={'ui_mode': 'simple'}).status_code == 401
    assert mine() == 'advanced'

    # An account from before there was a choice keeps seeing everything.
    db.execute('UPDATE users SET ui_mode = null WHERE user_id = %s', [uuid.UUID(uid)])
    assert mine() == 'advanced'
    assert choose({'ui_mode': 'simple'}).status_code == 200
    assert mine() == 'simple'

    # Yours to see, nobody else's, admins included.
    assert c.get(f'/api/users/{uid}', headers=_auth(token)).get_json()['ui_mode'] == 'simple'
    status, seen = api.get(f'/api/users/{uid}', who='admin')
    assert status == 200 and 'ui_mode' not in seen


def test_signing_in_tells_the_choice_and_logs_no_address(app, member, caplog):
    email, _, _ = member
    with caplog.at_level('DEBUG'):
        r = app.test_client().post('/api/login', json={'email': email, 'password': OLD})
    assert r.status_code == 200
    assert r.get_json()['data']['ui_mode'] == 'simple'
    said = [m.getMessage() for m in caplog.records if not m.name.startswith('cassandra')]
    assert not [line for line in said if email in line]


def test_deleting_your_account_needs_your_password(app, db, member):
    _, uid, sign_in = member
    _, token = sign_in()
    c = app.test_client()
    assert c.post('/api/account/delete', headers=_auth(token), json={'password': 'not-it'}).status_code == 403
    r = c.post('/api/account/delete', headers=_auth(token), json={'password': OLD})
    assert r.status_code == 200, r.get_json()
    assert db.execute('SELECT user_id FROM users WHERE user_id = %s', [uuid.UUID(uid)]).one() is None
    assert not _active(app, token)
    assert sign_in(OLD)[0] == 401


def test_a_member_can_leave_or_withdraw_a_request_but_the_founder_stays(api, app, db, member):
    _, uid, sign_in = member
    status, body = api.post('/api/spheres', who='admin', json={'name': 'Leave test sphere', 'description': 'Temporary.'})
    assert status == 201, body
    sid = body['sphere_id']
    try:
        status, body = api.post(f'/api/spheres/{sid}/leave', who='admin')
        assert status == 400 and 'founder' in body['message']

        _, token = sign_in()
        c = app.test_client()
        assert c.post(f'/api/spheres/{sid}/join', headers=_auth(token)).status_code == 200
        r = c.post(f'/api/spheres/{sid}/leave', headers=_auth(token))
        assert r.status_code == 200 and r.get_json()['left']
        row = db.execute('SELECT participants FROM spheres WHERE sphere_id = %s', [uuid.UUID(sid)]).one()
        assert uuid.UUID(uid) not in (row.participants or [])
        assert c.post(f'/api/spheres/{sid}/leave', headers=_auth(token)).status_code == 404

        # Asking to join a sphere that needs approval, then thinking better of it.
        assert api.patch(f'/api/spheres/{sid}', who='admin', json={'join_policy': 'approval'})[0] == 200
        r = c.post(f'/api/spheres/{sid}/join', headers=_auth(token))
        assert r.get_json()['pending']
        r = c.post(f'/api/spheres/{sid}/leave', headers=_auth(token))
        assert r.status_code == 200 and 'withdrawn' in r.get_json()['message']
        row = db.execute('SELECT member_roles FROM spheres WHERE sphere_id = %s', [uuid.UUID(sid)]).one()
        assert uuid.UUID(uid) not in (row.member_roles or {})
    finally:
        api.delete(f'/api/admin/spheres/{sid}', who='admin')


def test_a_reset_link_works_once_and_signs_the_member_out(api, app, db, member):
    _, uid, sign_in = member
    _, token = sign_in()
    c = app.test_client()
    # Only platform admins make them.
    assert c.post(f'/api/admin/users/{uid}/reset_link', headers=_auth(token)).status_code == 403
    status, body = api.post(f'/api/admin/users/{uid}/reset_link', who='admin')
    assert status == 200, body
    assert body['path'].startswith('/reset-password#token=')
    link = body['path'].split('#token=', 1)[1]
    assert c.post('/api/password/reset', json={'token': link, 'password': 'short'}).status_code == 400
    r = c.post('/api/password/reset', json={'token': link, 'password': 'brand-new-pass'})
    assert r.status_code == 200, r.get_json()
    assert c.post('/api/password/reset', json={'token': link, 'password': 'another-pass-1'}).status_code == 400
    assert not _active(app, token)
    assert sign_in(OLD)[0] == 401
    assert sign_in('brand-new-pass')[0] == 200
    assert c.post('/api/password/reset', json={'token': 'made-up', 'password': 'brand-new-pass'}).status_code == 400


def test_an_expired_reset_link_is_refused(app, db, member):
    from app.utils.password_reset import _hash
    _, uid, _ = member
    db.execute('INSERT INTO password_resets (token_hash, user_id, expires_at) VALUES (%s, %s, %s) USING TTL 600',
               [_hash('expired-token'), uuid.UUID(uid), datetime.utcnow() - timedelta(minutes=1)])
    try:
        r = app.test_client().post('/api/password/reset', json={'token': 'expired-token', 'password': 'brand-new-pass'})
        assert r.status_code == 400
    finally:
        db.execute('DELETE FROM password_resets WHERE token_hash = %s', [_hash('expired-token')])
