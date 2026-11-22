# The rule for runs of acknowledgements and their highlights (app/utils/timeline.py).
from datetime import datetime, timedelta
from types import SimpleNamespace

from app.utils import timeline

T0 = datetime(2026, 11, 1)


def ack(n, lit=None):
    return SimpleNamespace(ack_id=f'a{n}', created_at=T0 + timedelta(hours=n),
                           highlighted_at=T0 + timedelta(days=lit) if lit else None)


def exchange(n):
    return (T0 + timedelta(hours=n), f'x{n}')


def ids(entries):
    return [thing if what == 'exchange' else [a.ack_id for a in thing] for what, thing in entries]


def test_an_exchange_splits_a_run():
    entries = timeline.chronology([exchange(3)], [ack(1), ack(2), ack(4), ack(5)])
    assert ids(entries) == [['a5', 'a4'], 'x3', ['a2', 'a1']]


def test_order_of_input_does_not_matter():
    acks = [ack(1), ack(2), ack(4)]
    assert ids(timeline.chronology([exchange(3)], acks)) == ids(timeline.chronology([exchange(3)], acks[::-1]))


def test_undated_exchanges_go_last():
    assert ids(timeline.chronology([(None, 'old')], [ack(1)])) == [['a1'], 'old']


def test_one_or_two_are_never_folded():
    assert timeline.shown([ack(2), ack(1)]) == {'a2', 'a1'}


def test_a_long_run_folds_to_the_newest_until_something_is_highlighted():
    assert timeline.shown([ack(3), ack(2), ack(1)]) == {'a3'}
    assert timeline.shown([ack(3), ack(2, lit=1), ack(1)]) == {'a2'}


def test_no_third_highlight_in_a_run():
    entries = timeline.chronology([], [ack(1, lit=1), ack(2, lit=2), ack(3)])
    assert not timeline.may_highlight(entries, 'a3')
    assert timeline.may_highlight(entries, 'a1')         # already one of the two


def test_each_run_has_its_own_two():
    entries = timeline.chronology([exchange(3)], [ack(1, lit=1), ack(2, lit=2), ack(4)])
    assert timeline.may_highlight(entries, 'a4')


def test_when_runs_merge_the_two_latest_highlights_show():
    assert timeline.highlights([ack(4, lit=1), ack(3, lit=3), ack(1, lit=2)]) == {'a3', 'a1'}
