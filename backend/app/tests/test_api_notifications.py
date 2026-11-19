# Notifications: a member's own inbox, marking one read, marking all read.
import uuid

import pytest


@pytest.fixture
def fresh_notification(api, db):
    """One new, unread notification for David from Marie. It's removed again
    afterwards, and David's other notifications get their read state back."""
    from app.models.notification import Notification
    david, marie = api.uid('david'), api.uid('marie')
    before = {(r.created_at, r.notification_id): r.is_read for r in db.execute(
        'SELECT created_at, notification_id, is_read FROM notifications WHERE user_id = %s', [uuid.UUID(david)])}
    marker = f'Test notification {uuid.uuid4().hex[:8]}'
    Notification.create(user_id=david, actor_id=marie, actor_name='Marie Kondo', type_='test',
                        message=marker, link=f'/user?id={marie}')
    yield marker
    for r in db.execute('SELECT created_at, notification_id, is_read FROM notifications WHERE user_id = %s',
                        [uuid.UUID(david)]):
        key = (r.created_at, r.notification_id)
        if key not in before:
            db.execute('DELETE FROM notifications WHERE user_id = %s AND created_at = %s AND notification_id = %s',
                       [uuid.UUID(david), r.created_at, r.notification_id])
        elif before[key] != r.is_read:
            db.execute('UPDATE notifications SET is_read = %s WHERE user_id = %s AND created_at = %s AND notification_id = %s',
                       [before[key], uuid.UUID(david), r.created_at, r.notification_id])


def _find(api, marker):
    _, inbox = api.get('/api/notifications', who='david')
    return inbox, next(n for n in inbox['notifications'] if n['message'] == marker)


def test_inbox_lists_and_marks_one_read(api, fresh_notification):
    inbox, n = _find(api, fresh_notification)
    assert n['is_read'] is False and inbox['unread_count'] >= 1
    assert n['link'].startswith('/user?id=') and n['actor_name'] == 'Marie Kondo'
    status, _ = api.post('/api/notifications/read', who='david',
                         json={'created_at': n['created_at'], 'notification_id': n['notification_id']})
    assert status == 200
    inbox2, n2 = _find(api, fresh_notification)
    assert n2['is_read'] is True and inbox2['unread_count'] == inbox['unread_count'] - 1


def test_marking_something_that_isnt_there(api, fresh_notification):
    """Regression: the plain UPDATE was an upsert - a key that matched nothing
    inserted a blank notification into the inbox."""
    inbox, n = _find(api, fresh_notification)
    status, _ = api.post('/api/notifications/read', who='david',
                         json={'created_at': n['created_at'], 'notification_id': str(uuid.uuid4())})
    assert status == 404
    after, _ = _find(api, fresh_notification)
    assert len(after['notifications']) == len(inbox['notifications'])
    assert api.post('/api/notifications/read', who='david', json={'notification_id': n['notification_id']})[0] == 400
    assert api.post('/api/notifications/read', who='david',
                    json={'created_at': 'yesterday', 'notification_id': n['notification_id']})[0] == 400


def test_mark_all_read(api, fresh_notification):
    status, _ = api.post('/api/notifications/read_all', who='david')
    assert status == 200
    inbox, n = _find(api, fresh_notification)
    assert n['is_read'] is True and inbox['unread_count'] == 0


def test_inbox_is_your_own(api, fresh_notification):
    _, marie = api.get('/api/notifications', who='marie')
    assert all(n['message'] != fresh_notification for n in marie['notifications'])
