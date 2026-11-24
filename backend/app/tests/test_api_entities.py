# Generic entity routes: detail, visibility, join guards, roles, approval flow.
import pytest
from conftest import RIVERSIDE, REPAIR_CAFE, TOOL_LIBRARY, AI_COMMONS

NIL = '00000000-0000-0000-0000-000000000000'


def test_sphere_detail_embeds_members_cards_and_children(api):
    status, d = api.get(f'/api/spheres/{RIVERSIDE}', who='marie')
    assert status == 200
    assert d['name'] == 'Riverside Commons'
    assert any(m['name'] == 'Marie Konda' for m in d['members'])
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
    # alliance Lead is not assignable, not even by a platform admin
    status, _ = api.post(f'/api/alliances/{REPAIR_CAFE}/members/{api.uid("marie")}/role', who='admin', json={'role': 'admin'})
    assert status == 400


@pytest.fixture
def approval_project(api, keep_rows):
    """Put Community Tool Library on join_policy=approval for one test; the
    project row (policy, members, roles) is put back exactly afterwards."""
    keep_rows('projects', project_id=TOOL_LIBRARY)
    api.patch(f'/api/projects/{TOOL_LIBRARY}', who='admin', json={'join_policy': 'approval'})
    yield TOOL_LIBRARY


def test_join_approval_flow(api, approval_project):
    pid = approval_project
    david = api.uid('david')
    status, body = api.post(f'/api/projects/{pid}/join', who='david')
    assert status == 202 and body['pending'] is True
    # repeat is idempotent
    status, body = api.post(f'/api/projects/{pid}/join', who='david')
    assert status == 200 and body['pending'] is True
    # manager sees the request; the requester does not appear as a member yet
    _, d = api.get(f'/api/projects/{pid}', who='admin')
    assert [p['id'] for p in d['pending_members']] == [david]
    assert all(m['id'] != david for m in d['members'])
    # the requester can't see (or approve) pending requests
    _, dd = api.get(f'/api/projects/{pid}', who='david')
    assert 'pending_members' not in dd
    assert api.post(f'/api/projects/{pid}/members/{david}/role', who='david', json={'role': 'contributor'})[0] == 403
    # manager approves -> member with the default role
    status, body = api.post(f'/api/projects/{pid}/members/{david}/role', who='admin', json={'role': 'contributor'})
    assert status == 200
    _, d = api.get(f'/api/projects/{pid}', who='admin')
    assert any(m['id'] == david and m['role'] == 'contributor' for m in d['members'])
    assert d['pending_members'] == []


def test_founder_cannot_be_removed(api):
    steve = '16f033ca-2b2c-4745-a537-82999209774c'
    status, body = api.post(f'/api/projects/{TOOL_LIBRARY}/members/{steve}/role', who='admin', json={'role': 'remove'})
    assert status == 400 and 'founder' in body['message'].lower()


def test_public_sphere_endpoint_only_for_public_spheres(api, keep_rows):
    # Whatever AI Commons' flag is on this database, it's put back afterwards
    # (the demo data on production has Riverside public, so no sphere's
    # flag is assumed).
    keep_rows('spheres', sphere_id=AI_COMMONS)
    assert api.post(f'/api/spheres/{AI_COMMONS}/governance', who='admin', json={'is_public': False})[0] == 200
    assert api.get(f'/api/public/spheres/{AI_COMMONS}')[0] == 404
    assert api.post(f'/api/spheres/{AI_COMMONS}/governance', who='admin', json={'is_public': True})[0] == 200
    status, d = api.get(f'/api/public/spheres/{AI_COMMONS}')
    assert status == 200 and d['is_public'] is True and 'openings' in d


def test_a_signed_out_visitor_is_told_what_is_demo(api, keep_rows):
    # The site keeps stand-in pictures to the demo and labels personas: it can only do either if told.
    keep_rows('spheres', sphere_id=RIVERSIDE)
    assert api.post(f'/api/spheres/{RIVERSIDE}/governance', who='admin', json={'is_public': True})[0] == 200
    status, d = api.get(f'/api/public/spheres/{RIVERSIDE}')
    assert status == 200 and d['openings']
    assert all(o['is_demo'] is True for o in d['openings'])
    assert all(isinstance(o['provider_is_agent'], bool) for o in d['openings'])
    assert any(o['provider_is_agent'] for o in d['openings'])


def test_sandbox_flag_is_platform_admin_only(api):
    status, _ = api.post(f'/api/spheres/{RIVERSIDE}/governance', who='marie', json={'is_sandbox': True})
    assert status == 403


# ── Founding spheres, alliances and projects; banners ───────────────────────
@pytest.fixture
def founded(db):
    """(table, id column, id) of everything a test founds; deleted afterwards."""
    import uuid
    made = []
    yield made
    for table, column, eid in made:
        db.execute(f'DELETE FROM {table} WHERE {column} = %s', [uuid.UUID(eid)])


def test_a_sphere_needs_a_name(api):
    assert api.post('/api/spheres', who='marie', json={'description': 'nameless'})[0] == 400
    assert api.post('/api/spheres', who='marie', json={'name': '   '})[0] == 400
    assert api.post('/api/spheres', who='marie', content_type='multipart/form-data', data={'description': 'x'})[0] == 400
    # No Content-Type at all is a clean 400 (it used to be a 500).
    r = api.client.post('/api/spheres', headers={'Authorization': f"Bearer {api.login('marie')}"})
    assert r.status_code == 400


def test_found_a_sphere(api, founded):
    import io
    status, s = api.post('/api/spheres', who='marie', json={'name': 'Test sphere (delete me)', 'description': 'temporary'})
    assert status == 201 and s['name'] == 'Test sphere (delete me)'
    founded.append(('spheres', 'sphere_id', s['sphere_id']))
    _, detail = api.get(f"/api/spheres/{s['sphere_id']}", who='marie')
    assert detail['can_manage'] is True and str(detail['admin1']) == api.uid('marie')
    status, _ = api.post('/api/spheres', who='marie', content_type='multipart/form-data',
                         data={'name': 'Bad image sphere', 'image': (io.BytesIO(b'not an image at all'), 'x.png')})
    assert status == 400


def test_found_an_alliance_inside_your_sphere(api, founded):
    assert api.post('/api/alliances', who='marie', json={'sphere_id': RIVERSIDE})[0] == 400          # no name
    assert api.post('/api/alliances', who='marie', json={'name': 'Test alliance'})[0] == 400        # no sphere
    assert api.post('/api/alliances', who='marie', json={'name': 'T', 'sphere_id': NIL})[0] == 404   # no such sphere
    # Elon belongs to AI Commons only: he can't found an alliance in Riverside.
    assert api.post('/api/alliances', who='elon', json={'name': 'Test alliance', 'sphere_id': RIVERSIDE})[0] == 403
    status, a = api.post('/api/alliances', who='marie', json={'name': 'Test alliance (delete me)', 'sphere_id': RIVERSIDE})
    assert status == 201, a
    aid = a.get('alliance_id') or a.get('id')
    founded.append(('alliances', 'alliance_id', aid))
    _, detail = api.get(f'/api/alliances/{aid}', who='marie')
    assert detail['name'] == 'Test alliance (delete me)'
    assert any(m['id'] == api.uid('marie') for m in detail['members'])


def test_found_a_project_inside_your_sphere(api, founded):
    assert api.post('/api/projects', who='elon', json={'name': 'Test project', 'sphere_id': RIVERSIDE})[0] == 403
    assert api.post('/api/projects', who='marie', json={'name': 'Test project', 'sphere_id': NIL})[0] == 404
    status, p = api.post('/api/projects', who='marie', json={'name': 'Test project (delete me)', 'sphere_id': RIVERSIDE})
    assert status == 201, p
    founded.append(('projects', 'project_id', p.get('project_id') or p.get('id')))


def test_banners_are_for_managers(app, api, founded):
    import io
    from conftest import PNG_1PX
    status, p = api.post('/api/projects', who='marie', json={'name': 'Test banner project (delete me)', 'sphere_id': RIVERSIDE})
    assert status == 201, p
    pid = p.get('project_id') or p.get('id')
    founded.append(('projects', 'project_id', pid))

    def upload(who, data, target=pid):
        return api.post(f'/api/projects/{target}/image', who=who, content_type='multipart/form-data',
                        data={'image': (io.BytesIO(data), 'banner.png')})[0]

    assert upload('david', PNG_1PX) == 403
    assert upload('marie', b'not an image, not at all') == 400
    assert upload('marie', PNG_1PX) == 200
    r = app.test_client().get(f'/api/projects/{pid}/image')            # public, for <img src>
    assert r.status_code == 200 and r.data == PNG_1PX
    assert upload('marie', PNG_1PX, target=NIL) == 404


# ── The demonstration ───────────────────────────────────────────────────────
def test_demo_spheres_are_listed_and_joined_at_once(api, keep_rows, db):
    """New members are invited to the demo spheres, then join them all in one go."""
    import uuid as _uuid
    from app.utils.demo import forget
    from app.utils.demo import demo_sphere_ids
    # Joining "all demo spheres" touches every one of them: keep them all.
    for sid in {RIVERSIDE, AI_COMMONS} | {str(s) for s in demo_sphere_ids()}:
        keep_rows('spheres', sphere_id=sid)
    db.execute('UPDATE spheres SET is_demo = true WHERE sphere_id IN (%s, %s)',
               [_uuid.UUID(RIVERSIDE), _uuid.UUID(AI_COMMONS)])
    forget()
    status, demo = api.get('/api/demo', who='admin')
    assert status == 200
    ids = {s['id'] for s in demo['spheres']}
    assert {RIVERSIDE, AI_COMMONS} <= ids and not demo['joined_all']
    status, body = api.post('/api/demo/join', who='admin')
    assert status == 200 and {RIVERSIDE, AI_COMMONS} <= set(body['joined'])
    _, demo = api.get('/api/demo', who='admin')
    assert all(s['joined'] for s in demo['spheres'] if s['id'] in (RIVERSIDE, AI_COMMONS))
    # Labelled as demo wherever it shows.
    _, sphere = api.get(f'/api/spheres/{RIVERSIDE}', who='admin')
    assert sphere['is_demo'] is True


def test_registration_invites_to_the_demo(app, new_member, db):
    r = app.test_client().post('/api/register', json={'name': 'Test Person', 'email': new_member,
                                                      'password': 'a-long-password'})
    assert r.status_code == 200
    import uuid as _uuid
    uid = _uuid.UUID(str(r.get_json()['user_id']))
    rows = list(db.execute('SELECT type, link FROM notifications WHERE user_id = %s', [uid]))
    # Only when there are demo spheres to invite to.
    from app.utils.demo import demo_sphere_ids
    if demo_sphere_ids():
        assert any(n.type == 'demo_invite' and n.link == '/spheres#demo' for n in rows)
    db.execute('DELETE FROM notifications WHERE user_id = %s', [uid])
