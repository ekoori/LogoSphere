# Platform administration: admin-only gate, user flag guards, entity delete
# with its dependency checks, opening delete. Everything created is removed.
import uuid
import pytest

from conftest import RIVERSIDE


def test_admin_endpoints_are_platform_admin_only(api):
    for path in ('/api/admin/overview', '/api/admin/users', '/api/admin/spheres', '/api/admin/openings'):
        status, body = api.get(path, who='marie')
        assert status == 403, (path, body)
    status, body = api.get('/api/admin/overview', who='joe')
    assert status == 200
    c = body['counts']
    assert c['users'] >= 4 and c['spheres'] >= 2 and c['platform_admins'] >= 1
    assert any(a['email'] == 'joe.rogan@example.com' for a in body['platform_admins'])


def test_user_list_and_admin_flag_guards(api):
    status, body = api.get('/api/admin/users', who='joe')
    assert status == 200
    users = {u['email']: u for u in body['users']}
    assert users['joe.rogan@example.com']['is_platform_admin'] is True
    assert users['joe.rogan@example.com']['is_you'] is True
    assert users['david.attenborough@example.com']['is_platform_admin'] is False

    joe = api.uid('joe')
    david = api.uid('david')
    # can't change your own flag
    status, body = api.patch(f'/api/admin/users/{joe}', who='joe', json={'is_platform_admin': False})
    assert status == 400
    # grant, observe, revoke
    status, body = api.patch(f'/api/admin/users/{david}', who='joe', json={'is_platform_admin': True})
    assert status == 200 and body['user']['is_platform_admin'] is True
    try:
        _, d = api.get('/api/admin/overview', who='david')      # David is an admin now
        assert d['counts']['platform_admins'] >= 2
    finally:
        status, body = api.patch(f'/api/admin/users/{david}', who='joe', json={'is_platform_admin': False})
        assert status == 200 and body['user']['is_platform_admin'] is False
    status, _ = api.get('/api/admin/overview', who='david')
    assert status == 403


def test_admin_edits_a_users_name(api, db):
    david = api.uid('david')
    status, body = api.patch(f'/api/admin/users/{david}', who='joe', json={'location': 'Bristol'})
    assert status == 200 and body['user']['location'] == 'Bristol'
    status, _ = api.patch(f'/api/admin/users/{david}', who='joe', json={'name': ''})
    assert status == 400
    db.execute('UPDATE users SET location = null WHERE user_id = %s', [uuid.UUID(david)])


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
    status, body = api.get('/api/admin/projects', who='joe')
    assert status == 200
    mine = next((p for p in body['items'] if p['id'] == throwaway_project), None)
    assert mine and mine['kind'] == 'project' and mine['member_count'] >= 1
    status, _ = api.delete(f'/api/admin/projects/{throwaway_project}', who='marie')
    assert status == 403
    status, body = api.delete(f'/api/admin/projects/{throwaway_project}', who='joe')
    assert status == 200, body
    status, _ = api.get(f'/api/projects/{throwaway_project}', who='joe')
    assert status == 404


def test_sphere_with_children_cannot_be_deleted(api):
    status, body = api.delete(f'/api/admin/spheres/{RIVERSIDE}', who='joe')
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
    status, body = api.get('/api/admin/openings', who='joe')
    assert status == 200
    mine = next((o for o in body['items'] if o['service_id'] == throwaway_opening), None)
    assert mine and mine['is_open'] is True and mine['pending_count'] == 0
    status, body = api.delete(f'/api/admin/openings/{throwaway_opening}', who='joe')
    assert status == 200, body
    status, _ = api.get(f'/api/openings/{throwaway_opening}', who='joe')
    assert status == 404
