# Auth contract: login, session check, platform-admin flag, error envelope.


def test_login_returns_session_and_profile(api):
    status, body = api.post('/api/login', json={'email': 'jo.rodan@example.com', 'password': 'Joe'})
    assert status == 200
    assert body['session_id']
    assert body['data']['name'].startswith('Jo')
    assert 'password' not in body['data']
    api.logout_token(body['session_id'])


def test_login_response_carries_only_the_new_session(api):
    """The user data in a login response must not carry a session token. It
    used to include another live session of the same user (from an earlier
    sign-in), handing out a second bearer credential."""
    creds = {'email': 'marie.konda@example.com', 'password': 'Marie'}
    _, first = api.post('/api/login', json=creds)
    status, second = api.post('/api/login', json=creds)
    try:
        assert status == 200
        assert 'session_id' not in second['data']
        assert second['session_id'] != first['session_id']
    finally:
        api.logout_token(first['session_id'])
        api.logout_token(second['session_id'])


def test_public_profile_hides_email_from_other_members(api):
    marie = api.uid('marie')
    status, body = api.get(f'/api/users/{marie}', who='david')
    assert status == 200
    assert body['name'].startswith('Marie')
    assert 'email' not in body
    assert 'session_id' not in body
    # The person themself, and platform admins, still see it.
    _, own = api.get(f'/api/users/{marie}', who='marie')
    assert own['email'] == 'marie.konda@example.com'
    _, admin = api.get(f'/api/users/{marie}', who='admin')
    assert admin['email'] == 'marie.konda@example.com'


def test_bad_password_is_401_with_message(api):
    status, body = api.post('/api/login', json={'email': 'jo.rodan@example.com', 'password': 'nope'})
    assert status == 401
    assert body == {'message': 'Invalid email or password'}


def test_wrong_passwords_are_limited_where_they_come_from(api, app):
    from app.utils import attempts
    from conftest import USERS
    email, password = USERS['admin']
    client = app.test_client()

    def sign_in(secret, address):
        return client.post('/api/login', json={'email': email, 'password': secret}, headers={'X-Real-IP': address})

    for _ in range(attempts.PER_ADDRESS):
        assert sign_in('not-it-at-all', '203.0.113.7').status_code == 401
    assert sign_in(password, '203.0.113.7').status_code == 429
    # Nobody is locked out by someone else's guessing.
    elsewhere = sign_in(password, '198.51.100.9')
    assert elsewhere.status_code == 200
    api.logout_token(elsewhere.get_json()['session_id'])


def test_login_with_no_strings_is_401(app):
    for body in (None, [], {'email': 7, 'password': 'x'}, {'email': 'a@example.com'}):
        assert app.test_client().post('/api/login', json=body).status_code == 401


def test_protected_route_without_token_is_401(app):
    # A fresh client: the shared one carries the session cookie from login.
    r = app.test_client().get('/api/spheres')
    assert r.status_code == 401
    assert 'message' in r.get_json()


def test_unknown_api_route_is_json_404(api):
    status, body = api.get('/api/definitely-not-a-route', who='joe')
    assert status == 404
    assert body == {'message': 'Not found'}


def test_platform_admin_flag_is_a_users_column_not_an_email(api, db):
    """The test admin is flagged in users.is_platform_admin; Marie is not.
    Registering an admin's email must never grant the flag (it isn't verified)."""
    status, body = api.get('/api/check_session', who='admin')
    assert status == 200 and body['user_data']['is_platform_admin'] is True
    status, body = api.get('/api/check_session', who='marie')
    assert status == 200 and body['user_data']['is_platform_admin'] is False
    import uuid
    row = db.execute('SELECT is_platform_admin FROM users WHERE user_id = %s', [uuid.UUID(api.uid('admin'))]).one()
    assert row.is_platform_admin is True


def test_cookie_requests_do_not_rewrite_the_session(app, db):
    """Every cookie-authenticated request used to re-insert the whole session
    row (moving creation_time each time) and send a fresh cookie. The row is
    now touched at most every few minutes, and creation_time never moves."""
    import uuid
    from conftest import USERS
    client = app.test_client()
    https = {'base_url': 'https://localhost'}      # the cookie is Secure in production
    r = client.post('/api/login', json={'email': USERS['marie'][0], 'password': USERS['marie'][1]}, **https)
    token = r.get_json()['session_id']
    read = lambda: db.execute('SELECT creation_time, last_access_time FROM sessions WHERE session_id = %s',
                              [uuid.UUID(token)]).one()
    try:
        before = read()
        for _ in range(3):
            r = client.get('/api/user/profile', **https)
            assert r.status_code == 200 and 'Set-Cookie' not in r.headers
        after = read()
        assert (after.creation_time, after.last_access_time) == (before.creation_time, before.last_access_time)
    finally:
        client.post('/api/logout', headers={'Authorization': f'Bearer {token}'}, **https)


def test_errors_inside_a_route_are_not_sign_outs(app, api):
    """validate_session used to wrap the route call itself, so any error inside
    a route came back as 401 "Session validation failed" - and clients sign
    out on 401. Only the session lookup may answer 401 now."""
    from flask import Flask
    from cassandra.cluster import NoHostAvailable
    from app.middleware.session_middleware import validate_session

    probe = Flask('probe')
    probe.session_interface = app.session_interface

    @probe.route('/bug')
    @validate_session
    def bug(user_id=None):
        raise RuntimeError('a bug in the route')

    @probe.route('/me')
    @validate_session
    def me(user_id=None):
        return {'user_id': str(user_id)}

    api.login('marie')
    auth = {'Authorization': f"Bearer {api.tokens['marie']}"}
    client = probe.test_client()
    assert client.get('/bug', headers=auth).status_code == 500
    assert client.get('/me', headers=auth).get_json() == {'user_id': api.uid('marie')}
    assert client.get('/me', headers={'Authorization': 'Bearer not-a-token'}).status_code == 401
    assert client.get('/me').status_code == 401


def test_a_database_outage_is_503_not_a_sign_out(app, api, monkeypatch):
    """A failed session lookup during an outage must not read as "expired"."""
    from cassandra.cluster import NoHostAvailable
    api.login('marie')
    auth = {'Authorization': f"Bearer {api.tokens['marie']}"}

    def down(*args, **kwargs):
        raise NoHostAvailable('no hosts', {})

    monkeypatch.setattr(app.session_interface.cassandra_session, 'execute', down)
    r = app.test_client().get('/api/following', headers=auth)
    assert r.status_code == 503 and 'try again' in r.get_json()['message']
    r = app.test_client().get('/api/check_session', headers=auth)
    assert r.status_code == 503


def test_sign_in_ignores_email_case_and_spaces(api):
    status, body = api.post('/api/login', json={'email': '  jo.rodan@example.com ', 'password': 'Joe'})
    assert status == 200, body
    api.logout_token(body['session_id'])
