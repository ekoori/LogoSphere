# Search: plain text match across people / spheres / alliances / projects /
# openings / value cards, and value-graph vicinity ranking.
from conftest import RIVERSIDE


def test_text_search_finds_spheres_people_and_openings(api):
    status, body = api.get('/api/search?q=riverside', who='marie')
    assert status == 200
    kinds = {g['kind']: g for g in body['groups']}
    assert 'sphere' in kinds
    assert any(i['id'] == RIVERSIDE for i in kinds['sphere']['items'])
    assert kinds['sphere']['items'][0]['link'].startswith('/sphere?id=')

    status, body = api.get('/api/search?q=rogan', who='marie')
    kinds = {g['kind']: g for g in body['groups']}
    assert 'user' in kinds and kinds['user']['items'][0]['name'].startswith('Joe')

    status, body = api.get('/api/search?q=sharing&kinds=opening', who='marie')
    assert status == 200
    assert body['groups'] and body['groups'][0]['kind'] == 'opening'
    assert all(g['kind'] == 'opening' for g in body['groups'])


def test_short_queries_return_nothing(api):
    status, body = api.get('/api/search?q=a', who='marie')
    assert status == 200 and body['groups'] == [] and body['total'] == 0


def test_openings_outside_my_spheres_are_not_searchable(api):
    # Elon is only in AI Commons; Riverside-scoped openings must not leak.
    status, body = api.get('/api/search?q=sharing&kinds=opening', who='elon')
    assert status == 200
    for g in body['groups']:
        for item in g['items']:
            assert item['sphere_id'] != RIVERSIDE


def test_vicinity_around_me_ranks_by_shared_values(api):
    status, body = api.get('/api/search/vicinity', who='joe')
    assert status == 200, body
    assert body['around']['id'] == api.uid('joe') and body['around']['kind'] == 'user'
    assert body['total'] > 0
    for g in body['groups']:
        for item in g['items']:
            assert 0 < item['similarity'] <= 1
            assert item['id'] != api.uid('joe')
        sims = [i['similarity'] for i in g['items']]
        assert sims == sorted(sims, reverse=True)


def test_vicinity_with_text_and_bad_anchor(api):
    status, body = api.get('/api/search/vicinity?q=community%20care%20trust', who='marie')
    assert status == 200 and body['around'] is None
    assert body['total'] > 0
    status, body = api.get('/api/search/vicinity?around=not-a-uuid', who='marie')
    assert status == 400
    status, body = api.get(f'/api/search/vicinity?around={RIVERSIDE}&kinds=user', who='marie')
    assert status == 200 and body['around']['kind'] == 'sphere'
    assert all(g['kind'] == 'user' for g in body['groups'])
