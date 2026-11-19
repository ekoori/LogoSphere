# People: your own account and profile, other members' avatars, following,
# profile edits and registration. Everything a test changes is put back.
import io
import uuid

import pytest

from conftest import USERS, PNG_1PX


def test_own_user_and_profile(api):
    status, me = api.get('/api/user', who='marie')
    assert status == 200 and me['user_id'] == api.uid('marie') and me['email'] == USERS['marie'][0]
    status, profile = api.get('/api/user/profile', who='marie')
    assert status == 200 and profile['user_id'] == api.uid('marie')
    assert 'session_id' not in profile


def test_profile_needs_a_session(app):
    assert app.test_client().get('/api/user/profile').status_code == 401


def test_avatar_is_public_and_always_an_image(app, api):
    anon = app.test_client()
    r = anon.get(f"/api/users/{api.uid('marie')}/avatar")
    assert r.status_code == 200 and r.mimetype.startswith('image/')
    # Nobody by that id: an initials placeholder rather than a broken image.
    r = anon.get(f'/api/users/{uuid.uuid4()}/avatar')
    assert r.status_code == 200 and r.mimetype == 'image/svg+xml'


def test_follow_toggles_and_lists(api, keep_rows):
    marie, david = api.uid('marie'), api.uid('david')
    keep_rows('follows', follower_id=marie, followee_id=david)   # whatever was there stays
    _, before = api.get('/api/following', who='marie')
    was = any(f['id'] == david for f in before)

    status, body = api.post(f'/api/users/{david}/follow', who='marie')
    assert status == 200 and body['following'] is (not was)
    _, now = api.get('/api/following', who='marie')
    assert any(f['id'] == david for f in now) is (not was)
    _, profile = api.get(f'/api/users/{david}', who='marie')
    assert profile['is_following'] is (not was)

    status, body = api.post(f'/api/users/{david}/follow', who='marie')
    assert status == 200 and body['following'] is was


def test_follow_guards(api):
    status, _ = api.post(f"/api/users/{api.uid('marie')}/follow", who='marie')
    assert status == 400                                   # not yourself
    status, _ = api.post(f'/api/users/{uuid.uuid4()}/follow', who='marie')
    assert status == 404                                   # not nobody


def test_update_own_profile(api, keep_rows):
    marie = api.uid('marie')
    keep_rows('users', user_id=marie)
    status, body = api.post('/api/updateuser', who='marie', json={'location': 'Kyoto (test)'})
    assert status == 200 and body['location'] == 'Kyoto (test)'
    # Fields not sent are left alone.
    assert body['name'].startswith('Marie')
    _, profile = api.get('/api/user/profile', who='marie')
    assert profile['location'] == 'Kyoto (test)'


def test_profile_fields_can_be_cleared(api, keep_rows):
    """An empty surname or location used to be ignored, so neither could ever
    be removed. A name can't be blanked."""
    keep_rows('users', user_id=api.uid('marie'))
    status, body = api.post('/api/updateuser', who='marie', json={'location': 'Kyoto (test)', 'surname': 'K (test)'})
    assert status == 200 and body['location'] == 'Kyoto (test)'
    status, body = api.post('/api/updateuser', who='marie', json={'location': '', 'surname': '', 'name': '  '})
    assert status == 200 and body['location'] is None and body['surname'] is None
    assert body['name'].startswith('Marie')


@pytest.fixture
def keep_marie_picture(api, db):
    """keep_rows leaves image blobs alone; this test uploads one, so put
    Marie's picture (usually none) back exactly."""
    marie = uuid.UUID(api.uid('marie'))
    row = db.execute('SELECT profile_picture FROM users WHERE user_id = %s', [marie]).one()
    before = row.profile_picture if row else None
    yield
    db.execute('UPDATE users SET profile_picture = %s WHERE user_id = %s', [before, marie])


def test_profile_picture_is_a_validated_upload(api, keep_rows, keep_marie_picture):
    marie = api.uid('marie')
    keep_rows('users', user_id=marie)
    status, _ = api.post('/api/updateuser', who='marie', content_type='multipart/form-data',
                         data={'location': 'x', 'profile_picture': (io.BytesIO(b'not an image at all'), 'p.txt')})
    assert status == 400
    # A picture sent as JSON is ignored rather than stored unchecked.
    status, body = api.post('/api/updateuser', who='marie', json={'location': 'Kyoto (test)', 'profile_picture': 'aGVsbG8='})
    assert status == 200 and body['has_picture'] is False
    # A real upload is stored, flagged, and served by the avatar endpoint.
    status, body = api.post('/api/updateuser', who='marie', content_type='multipart/form-data',
                            data={'location': 'Kyoto (test)', 'profile_picture': (io.BytesIO(PNG_1PX), 'p.png')})
    assert status == 200 and body['has_picture'] is True
    r = api.client.get(f'/api/users/{marie}/avatar')
    assert r.status_code == 200 and r.data == PNG_1PX and r.mimetype == 'image/png'


def test_responses_never_carry_the_picture(api):
    """Regression: user data embedded the profile picture as base64, so every
    session check and profile view carried megabytes (3 MB for one demo user)."""
    for path in ('/api/check_session', '/api/user/profile', f"/api/users/{api.uid('joe')}"):
        status, body = api.get(path, who='joe')
        user = body.get('user_data', body)
        assert status == 200 and 'profile_picture' not in user and 'has_picture' in user, path
        assert len(str(body)) < 10_000, path


# ── Registration ────────────────────────────────────────────────────────────
@pytest.mark.parametrize('body', [
    {'name': 'Test', 'email': 'not-an-email', 'password': 'long-enough-1'},
    {'name': 'Test', 'email': 'someone@example.com', 'password': 'short'},
    {'name': '', 'email': 'someone@example.com', 'password': 'long-enough-1'},
    {},
])
def test_registration_validates(app, body):
    assert app.test_client().post('/api/register', json=body).status_code == 400


def test_registration_refuses_a_taken_email(app):
    r = app.test_client().post('/api/register', json={
        'name': 'Joe', 'email': USERS['joe'][0], 'password': 'long-enough-1'})
    assert r.status_code == 400


def test_register_then_sign_in(app, new_member):
    client = app.test_client()
    r = client.post('/api/register', json={'name': 'Test Person', 'email': new_member, 'password': 'a-long-password'})
    assert r.status_code == 200 and r.get_json()['reg_success'] is True
    uid = r.get_json()['user_id']
    r = client.post('/api/login', json={'email': new_member, 'password': 'a-long-password'})
    assert r.status_code == 200 and r.get_json()['data']['user_id'] == uid
    token = r.get_json()['session_id']
    r = client.get('/api/check_session', headers={'Authorization': f'Bearer {token}'})
    assert r.get_json()['status'] == 'active'
    client.post('/api/logout', headers={'Authorization': f'Bearer {token}'})


def test_registration_stores_the_email_lower_case(app, db, new_member):
    client = app.test_client()
    r = client.post('/api/register', json={'name': 'Test Person', 'email': new_member.upper(), 'password': 'a-long-password'})
    assert r.status_code == 200
    row = db.execute('SELECT email FROM user_credentials WHERE email = %s', [new_member]).one()
    assert row and row.email == new_member
    # ...so the same address, typed any way, can't register twice.
    r = client.post('/api/register', json={'name': 'Again', 'email': new_member.title(), 'password': 'a-long-password'})
    assert r.status_code == 400
