# Auth contract: login, session check, platform-admin flag, error envelope.


def test_login_returns_session_and_profile(api):
    status, body = api.post('/api/login', json={'email': 'joe.rogan@example.com', 'password': 'Joe'})
    assert status == 200
    assert body['session_id']
    assert body['data']['name'].startswith('Joe')
    assert 'password' not in body['data']
    api.logout_token(body['session_id'])


def test_login_response_carries_only_the_new_session(api):
    """The user data in a login response must not carry a session token. It
    used to include another live session of the same user (from an earlier
    sign-in), handing out a second bearer credential."""
    creds = {'email': 'marie.kondo@example.com', 'password': 'Marie'}
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
    assert own['email'] == 'marie.kondo@example.com'
    _, admin = api.get(f'/api/users/{marie}', who='joe')
    assert admin['email'] == 'marie.kondo@example.com'


def test_bad_password_is_401_with_message(api):
    status, body = api.post('/api/login', json={'email': 'joe.rogan@example.com', 'password': 'nope'})
    assert status == 401
    assert body == {'message': 'Invalid email or password'}


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
    """Joe is flagged in users.is_platform_admin; Marie is not. Registering an
    admin's email must never grant the flag (it isn't verified)."""
    status, body = api.get('/api/check_session', who='joe')
    assert status == 200 and body['user_data']['is_platform_admin'] is True
    status, body = api.get('/api/check_session', who='marie')
    assert status == 200 and body['user_data']['is_platform_admin'] is False
    import uuid
    row = db.execute('SELECT is_platform_admin FROM users WHERE user_id = %s', [uuid.UUID(api.uid('joe'))]).one()
    assert row.is_platform_admin is True
