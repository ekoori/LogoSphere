# Meaning Trail: your own, someone else's, a project's. Exchanges only come
# from openings (accept -> confirm), never from a bare "add" call.
import uuid

from conftest import TOOL_LIBRARY


def test_own_trail(api):
    status, rows = api.get('/api/meaning_trail', who='joe')
    assert status == 200 and isinstance(rows, list)
    for row in rows:
        assert row['exchange_id'] and 'exchange_status' in row and 'likes' in row


def test_trails_are_newest_first(api):
    """Regression: a trail came back as "exchanges I started, then the ones
    others started with me", each in id order, so dates jumped about."""
    for path in ('/api/meaning_trail', f'/api/meaning_trail/by_project/{TOOL_LIBRARY}'):
        status, rows = api.get(path, who='joe')
        stamps = [r.get('project_start_timestamp') or '' for r in rows]
        assert status == 200 and stamps == sorted(stamps, reverse=True), path


def test_someone_elses_trail_is_two_sided(api):
    """An exchange shows in both parties' trails."""
    marie = api.uid('marie')
    status, rows = api.post('/api/meaning_trail', who='joe', json={'userId': marie})
    assert status == 200 and isinstance(rows, list)
    for row in rows:
        assert marie in (row.get('initiator_id'), row.get('user_id'), row.get('other_user_id'))


def test_project_trail(api):
    status, rows = api.get(f'/api/meaning_trail/by_project/{TOOL_LIBRARY}', who='joe')
    assert status == 200 and all(r.get('project_id') == TOOL_LIBRARY for r in rows)
    status, _ = api.get(f'/api/meaning_trail/by_project/{uuid.uuid4()}', who='joe')
    assert status == 404


def test_trail_needs_a_session(app):
    assert app.test_client().get('/api/meaning_trail').status_code == 401


def test_exchanges_cannot_be_added_without_an_opening(api):
    """POST /api/meaning_trail/add_exchange let anyone write an exchange into
    anyone's trail, with no acceptance or confirmation. It is gone."""
    status, _ = api.post('/api/meaning_trail/add_exchange', who='joe', json={
        'other_user_id': api.uid('marie'), 'project_id': TOOL_LIBRARY})
    assert status in (404, 405)
