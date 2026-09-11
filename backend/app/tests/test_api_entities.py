# Generic entity routes: detail, visibility, join guards, roles, approval flow.
import pytest
from conftest import RIVERSIDE, REPAIR_CAFE, TOOL_LIBRARY, AI_COMMONS

NIL = '00000000-0000-0000-0000-000000000000'


def test_sphere_detail_embeds_members_cards_and_children(api):
    status, d = api.get(f'/api/spheres/{RIVERSIDE}', who='marie')
    assert status == 200
    assert d['name'] == 'Riverside Commons'
    assert any(m['name'] == 'Marie Kondo' for m in d['members'])
    assert isinstance(d['value_cards'], list)
    assert any(a['id'] == REPAIR_CAFE for a in d['alliance_list'])
    assert any(p['id'] == TOOL_LIBRARY for p in d['project_list'])
    assert d['can_manage'] is False       # a member is not an admin


def test_lists_embed_value_cards_and_skip_blobs(api):
    status, rows = api.get('/api/spheres', who='joe')
    assert status == 200
    first = rows[0]
    assert 'value_cards' in first and 'has_image' in first
    assert first.get('image') in (None, '')  # never the base64 blob in a list


def test_alliance_detail_hidden_outside_its_sphere(api):
    assert api.get(f'/api/alliances/{REPAIR_CAFE}', who='marie')[0] == 200
    status, body = api.get(f'/api/alliances/{REPAIR_CAFE}', who='elon')   # not in Riverside
    assert status == 404 and body['message'] == 'Alliance not found'


def test_platform_admin_sees_everything(api):
    # Joe is in every seeded sphere anyway; the flag is what matters for AI Commons projects
    status, rows = api.get('/api/projects', who='joe')
    assert status == 200 and len(rows) >= 4


def test_join_nonexistent_does_not_upsert_a_phantom_row(api, db):
    import uuid
    status, body = api.post(f'/api/spheres/{NIL}/join', who='marie')
    assert status == 404
    assert db.execute('SELECT sphere_id FROM spheres WHERE sphere_id = %s', [uuid.UUID(NIL)]).one() is None


def test_join_alliance_requires_sphere_membership(api):
    status, body = api.post(f'/api/alliances/{REPAIR_CAFE}/join', who='elon')
    assert status == 403


def test_only_managers_may_patch(api):
    status, _ = api.patch(f'/api/alliances/{REPAIR_CAFE}', who='elon', json={'description': 'x'})
    assert status in (403, 404)   # not visible / not authorised
    # Marie is a steward -> may edit; write the same value back so nothing changes
    status, d = api.get(f'/api/alliances/{REPAIR_CAFE}', who='marie')
    status2, d2 = api.patch(f'/api/alliances/{REPAIR_CAFE}', who='marie', json={'description': d['description']})
    assert status2 == 200 and d2['description'] == d['description']


def test_only_sphere_admins_manage_a_sphere(api):
    """Being a participant is not enough: the banner upload is manager-only."""
    import io
    r = api.client.post(f'/api/spheres/{RIVERSIDE}/image', headers=api._hdr('marie'),
                        data={'image': (io.BytesIO(b'\x89PNG\r\n\x1a\n' + b'0' * 32), 'x.png')},
                        content_type='multipart/form-data')
    assert r.status_code == 403


def test_role_change_guards(api):
    # non-admin
    status, _ = api.post(f'/api/spheres/{RIVERSIDE}/members/{api.uid("joe")}/role', who='marie', json={'role': 'admin'})
    assert status == 403
    # admin, but target isn't a member
    status, body = api.post(f'/api/spheres/{RIVERSIDE}/members/{NIL}/role', who='joe', json={'role': 'admin'})
    assert status == 404
    # alliance Lead is not assignable
    status, _ = api.post(f'/api/alliances/{REPAIR_CAFE}/members/{api.uid("marie")}/role', who='joe', json={'role': 'admin'})
    assert status == 400


@pytest.fixture
def approval_project(api):
    """Put Community Tool Library on join_policy=approval for one test, then
    restore it and make sure David is not left as a member."""
    api.patch(f'/api/projects/{TOOL_LIBRARY}', who='joe', json={'join_policy': 'approval'})
    yield TOOL_LIBRARY
    api.post(f'/api/projects/{TOOL_LIBRARY}/members/{api.uid("david")}/role', who='joe', json={'role': 'remove'})
    api.patch(f'/api/projects/{TOOL_LIBRARY}', who='joe', json={'join_policy': 'open'})


def test_join_approval_flow(api, approval_project):
    pid = approval_project
    david = api.uid('david')
    status, body = api.post(f'/api/projects/{pid}/join', who='david')
    assert status == 202 and body['pending'] is True
    # repeat is idempotent
    status, body = api.post(f'/api/projects/{pid}/join', who='david')
    assert status == 200 and body['pending'] is True
    # manager sees the request; the requester does not appear as a member yet
    _, d = api.get(f'/api/projects/{pid}', who='joe')
    assert [p['id'] for p in d['pending_members']] == [david]
    assert all(m['id'] != david for m in d['members'])
    # the requester can't see (or approve) pending requests
    _, dd = api.get(f'/api/projects/{pid}', who='david')
    assert 'pending_members' not in dd
    assert api.post(f'/api/projects/{pid}/members/{david}/role', who='david', json={'role': 'contributor'})[0] == 403
    # manager approves -> member with the default role
    status, body = api.post(f'/api/projects/{pid}/members/{david}/role', who='joe', json={'role': 'contributor'})
    assert status == 200
    _, d = api.get(f'/api/projects/{pid}', who='joe')
    assert any(m['id'] == david and m['role'] == 'contributor' for m in d['members'])
    assert d['pending_members'] == []


def test_founder_cannot_be_removed(api):
    steve = '16f033ca-2b2c-4745-a537-82999209774c'
    status, body = api.post(f'/api/projects/{TOOL_LIBRARY}/members/{steve}/role', who='joe', json={'role': 'remove'})
    assert status == 400 and 'founder' in body['message'].lower()


def test_public_sphere_endpoint_only_for_public_spheres(api):
    assert api.get(f'/api/public/spheres/{RIVERSIDE}')[0] == 404
    api.post(f'/api/spheres/{AI_COMMONS}/governance', who='joe', json={'is_public': True})
    try:
        status, d = api.get(f'/api/public/spheres/{AI_COMMONS}')
        assert status == 200 and d['is_public'] is True and 'openings' in d
    finally:
        api.post(f'/api/spheres/{AI_COMMONS}/governance', who='joe', json={'is_public': False})


def test_sandbox_flag_is_platform_admin_only(api):
    status, _ = api.post(f'/api/spheres/{RIVERSIDE}/governance', who='marie', json={'is_sandbox': True})
    assert status == 403
