# Platform administration: admin-only gate, user flag guards, entity delete
# with its dependency checks, opening delete. Everything created is removed.
import uuid
import pytest

from conftest import RIVERSIDE, USERS


def test_admin_endpoints_are_platform_admin_only(api):
    for path in ('/api/admin/overview', '/api/admin/users', '/api/admin/spheres', '/api/admin/openings'):
        status, body = api.get(path, who='marie')
        assert status == 403, (path, body)
    status, body = api.get('/api/admin/overview', who='admin')
    assert status == 200
    c = body['counts']
    assert c['users'] >= 4 and c['spheres'] >= 2 and c['platform_admins'] >= 1
    assert any(a['email'] == USERS['admin'][0] for a in body['platform_admins'])


def test_user_list_and_admin_flag_guards(api, keep_rows):
    keep_rows('users', user_id=api.uid('david'))
    status, body = api.get('/api/admin/users', who='admin')
    assert status == 200
    users = {u['email']: u for u in body['users']}
    assert users[USERS['admin'][0]]['is_platform_admin'] is True
    assert users[USERS['admin'][0]]['is_you'] is True
    assert users['david.attenborough@example.com']['is_platform_admin'] is False

    me = api.uid('admin')
    david = api.uid('david')
    # can't change your own flag
    status, body = api.patch(f'/api/admin/users/{me}', who='admin', json={'is_platform_admin': False})
    assert status == 400
    # grant, observe, revoke
    status, body = api.patch(f'/api/admin/users/{david}', who='admin', json={'is_platform_admin': True})
    assert status == 200 and body['user']['is_platform_admin'] is True
    try:
        _, d = api.get('/api/admin/overview', who='david')      # David is an admin now
        assert d['counts']['platform_admins'] >= 2
    finally:
        status, body = api.patch(f'/api/admin/users/{david}', who='admin', json={'is_platform_admin': False})
        assert status == 200 and body['user']['is_platform_admin'] is False
    status, _ = api.get('/api/admin/overview', who='david')
    assert status == 403


def test_admin_edits_a_users_name(api, keep_rows):
    david = api.uid('david')
    keep_rows('users', user_id=david)   # David keeps his own location afterwards
    status, body = api.patch(f'/api/admin/users/{david}', who='admin', json={'location': 'Bristol'})
    assert status == 200 and body['user']['location'] == 'Bristol'
    status, _ = api.patch(f'/api/admin/users/{david}', who='admin', json={'name': ''})
    assert status == 400


@pytest.fixture
def throwaway_project(api, db):
    status, body = api.post('/api/projects', who='joe', json={
        'name': 'Admin test project', 'description': 'temporary', 'sphere_id': RIVERSIDE})
    assert status in (200, 201), body
    pid = body.get('project_id') or body.get('id') or (body.get('project') or {}).get('project_id')
    assert pid, body
    yield pid
    db.execute('DELETE FROM projects WHERE project_id = %s', [uuid.UUID(pid)])
    db.execute("UPDATE spheres SET projects = projects - ['Admin test project'] WHERE sphere_id = %s",
               [uuid.UUID(RIVERSIDE)])


def test_admin_lists_and_deletes_a_project(api, throwaway_project):
    status, body = api.get('/api/admin/projects', who='admin')
    assert status == 200
    mine = next((p for p in body['items'] if p['id'] == throwaway_project), None)
    assert mine and mine['kind'] == 'project' and mine['member_count'] >= 1
    status, _ = api.delete(f'/api/admin/projects/{throwaway_project}', who='marie')
    assert status == 403
    status, body = api.delete(f'/api/admin/projects/{throwaway_project}', who='admin')
    assert status == 200, body
    status, _ = api.get(f'/api/projects/{throwaway_project}', who='joe')
    assert status == 404


def test_sphere_with_children_cannot_be_deleted(api):
    status, body = api.delete(f'/api/admin/spheres/{RIVERSIDE}', who='admin')
    assert status == 409 and 'first' in body['message']


@pytest.fixture
def throwaway_opening(api, db):
    status, body = api.post('/api/openings', who='david', json={
        'type': 'offer', 'title': 'Admin test opening', 'description': 'temporary', 'sphere_id': RIVERSIDE})
    assert status == 201, body
    sid = body['service_id']
    yield sid
    db.execute('DELETE FROM services WHERE service_id = %s', [uuid.UUID(sid)])
    db.execute('DELETE FROM opening_acceptances WHERE service_id = %s', [uuid.UUID(sid)])


def test_admin_lists_and_deletes_an_opening(api, throwaway_opening):
    status, body = api.get('/api/admin/openings', who='admin')
    assert status == 200
    mine = next((o for o in body['items'] if o['service_id'] == throwaway_opening), None)
    assert mine and mine['is_open'] is True and mine['pending_count'] == 0
    status, body = api.delete(f'/api/admin/openings/{throwaway_opening}', who='admin')
    assert status == 200, body
    status, _ = api.get(f'/api/openings/{throwaway_opening}', who='joe')
    assert status == 404


def test_persona_flag_is_an_admin_toggle(api, keep_rows):
    """users.is_agent marks an AI persona; it shows on the person wherever the
    API names them, and only a platform admin sets it."""
    david = api.uid('david')
    keep_rows('users', user_id=david)
    assert api.patch(f'/api/admin/users/{david}', who='marie', json={'is_agent': True})[0] == 403
    status, body = api.patch(f'/api/admin/users/{david}', who='admin', json={'is_agent': True})
    assert status == 200 and body['user']['is_agent'] is True
    _, person = api.get(f'/api/users/{david}', who='marie')
    assert person['is_agent'] is True
    status, body = api.patch(f'/api/admin/users/{david}', who='admin', json={'is_agent': False})
    assert status == 200 and body['user']['is_agent'] is False


def test_demo_flag_is_an_admin_toggle(api, keep_rows):
    keep_rows('spheres', sphere_id=RIVERSIDE)
    assert api.patch(f'/api/admin/spheres/{RIVERSIDE}', who='marie', json={'is_demo': True})[0] == 403
    assert api.patch(f'/api/admin/spheres/{RIVERSIDE}', who='admin', json={})[0] == 400
    status, _ = api.patch(f'/api/admin/spheres/{RIVERSIDE}', who='admin', json={'is_demo': True})
    assert status == 200
    _, sphere = api.get(f'/api/spheres/{RIVERSIDE}', who='marie')
    assert sphere['is_demo'] is True
    # ...and what lives in it says so too.
    _, items = api.get('/api/openings', who='marie')
    assert all(o['is_demo'] for o in items if o.get('sphere_id') == RIVERSIDE)
