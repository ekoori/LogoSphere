# Hours on a receipt: optional, to the nearest quarter hour, only from whoever
# writes the receipt, and never counted towards anything.
import pytest

from test_api_sharing import exchange_between, post_opening


@pytest.fixture
def gone_after(db, people):
    yield
    for who in (people['ada'], people['ben']):
        for row in db.execute('SELECT exchange_id FROM meaning_trail WHERE user_id = %s', [who.id]):
            db.execute('DELETE FROM trail_acknowledgements WHERE trail_id = %s', [row.exchange_id])
        db.execute('DELETE FROM meaning_trail WHERE user_id = %s', [who.id])


def test_a_receipt_may_say_how_long_it_took(people, gone_after):
    ada, ben = people['ada'], people['ben']
    xid = exchange_between(ada, ben, post_opening(ada, people['sphere']))
    for status in ('In Progress', 'Finished'):
        assert ada.post(f'/api/exchange/{xid}/status', {'status': status})[0] == 200
    receipt = {'type': 'gratitude', 'text': 'Thank you, the shelf is up'}
    for bad in (0, 0.1, 101, 'lots', True, -2):
        assert ben.post(f'/api/exchange/{xid}/comment', {**receipt, 'hours': bad})[0] == 400, bad
    assert ada.get(f'/api/exchange/{xid}')[1]['exchange']['gratitude_comment'] is None      # nothing kept from those
    assert ben.post(f'/api/exchange/{xid}/comment', {**receipt, 'hours': 2.4})[0] == 200
    assert ada.get(f'/api/exchange/{xid}')[1]['exchange']['effort_hours'] == 2.5
    # The initiator's note says no hours of its own.
    assert ada.post(f'/api/exchange/{xid}/comment', {'type': 'user', 'text': 'Glad to help', 'hours': 9})[0] == 200
    assert ben.get(f'/api/exchange/{xid}')[1]['exchange']['effort_hours'] == 2.5


def test_a_receipt_without_hours_is_as_before(people, gone_after):
    ada, ben = people['ada'], people['ben']
    xid = exchange_between(ada, ben, post_opening(ada, people['sphere']))
    for status in ('In Progress', 'Finished'):
        assert ada.post(f'/api/exchange/{xid}/status', {'status': status})[0] == 200
    assert ben.post(f'/api/exchange/{xid}/comment', {'type': 'gratitude', 'text': 'Thanks', 'hours': None})[0] == 200
    assert ada.get(f'/api/exchange/{xid}')[1]['exchange']['effort_hours'] is None


def test_hours_never_count_towards_closeness(app):
    method = app.test_client().get('/api/meaning_graph/method').get_json()
    assert 'hours given' in str(method)
