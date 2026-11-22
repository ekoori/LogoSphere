# When repeating events happen: pure dates and zones.
from datetime import date, datetime

from app.utils import recurrence as r


def days(first, repeats, n=5, until=None):
    out = []
    for found in r.dates(first, repeats, until):
        out.append(found.isoformat())
        if len(out) == n:
            break
    return out


def test_weeks_and_fortnights():
    assert days(date(2027, 2, 23), r.WEEKLY, 3) == ['2027-02-23', '2027-03-02', '2027-03-09']
    assert days(date(2027, 2, 23), r.FORTNIGHTLY, 3) == ['2027-02-23', '2027-03-09', '2027-03-23']
    assert days(date(2027, 2, 23), r.NEVER) == ['2027-02-23']


def test_the_31st_is_a_short_months_last_day():
    assert days(date(2027, 12, 31), r.MONTHLY, 5) == ['2027-12-31', '2028-01-31', '2028-02-29', '2028-03-31', '2028-04-30']


def test_the_second_tuesday_and_a_fifth_is_the_last():
    assert days(date(2027, 1, 12), r.MONTHLY_WEEKDAY, 3) == ['2027-01-12', '2027-02-09', '2027-03-09']
    assert days(date(2027, 3, 31), r.MONTHLY_WEEKDAY, 3) == ['2027-03-31', '2027-04-28', '2027-05-26']


def test_until_is_included_and_then_it_stops():
    assert days(date(2027, 2, 2), r.WEEKLY, 9, date(2027, 2, 16)) == ['2027-02-02', '2027-02-09', '2027-02-16']


def test_seven_stays_seven_when_the_clocks_change():
    first = datetime(2027, 3, 25, 19, 0)        # Paris moves its clocks on 28 March 2027
    found = r.times(first, 'Europe/Paris', r.WEEKLY, count=2)
    assert [t.starts for t in found] == [datetime(2027, 3, 25, 18, 0), datetime(2027, 4, 1, 17, 0)]


def test_the_next_one_thats_on():
    first = datetime(2027, 1, 5, 10, 0)
    on_now = r.upcoming(first, 'UTC', r.WEEKLY, None, 60, datetime(2027, 1, 12, 10, 30))
    assert on_now.day == '2027-01-12'       # it hasn't ended
    assert r.upcoming(first, 'UTC', r.WEEKLY, None, 60, datetime(2027, 1, 12, 10, 30), {'2027-01-12'}).day == '2027-01-19'
    assert r.upcoming(first, 'UTC', r.NEVER, None, 60, datetime(2027, 1, 5, 11, 0)) is None


def test_only_its_own_dates():
    first = datetime(2027, 1, 5, 10, 0)
    assert r.falls_on(first, r.WEEKLY, None, '2027-01-19') == date(2027, 1, 19)
    for day in ('2027-01-20', '2026-12-29', 'soon', None, 7, '9999-12-31'):
        assert r.falls_on(first, r.WEEKLY, None, day) is None, day


def test_only_zones_there_are():
    assert r.zone('Atlantic/Reykjavik')
    for name in ('Mars/Base', '../../etc/passwd', '', None, 7, [], 'x' * 100, 'Europe', 'Factory', 'localtime', 'right/UTC'):
        assert r.zone(name) is None, name
