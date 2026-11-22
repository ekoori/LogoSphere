"""When a repeating event happens.

An event is kept as the wall-clock time it starts at, in its own time zone, so
"Tuesdays at seven" stays at seven when the clocks change. Each time is named
by its local date. Pure: no database.
"""
import calendar
from collections import namedtuple
from datetime import date, datetime, timedelta, timezone
from functools import lru_cache
from zoneinfo import ZoneInfo, available_timezones

NEVER, WEEKLY, FORTNIGHTLY, MONTHLY, MONTHLY_WEEKDAY = 'never', 'weekly', 'fortnightly', 'monthly', 'monthly_weekday'
REPEATS = (NEVER, WEEKLY, FORTNIGHTLY, MONTHLY, MONTHLY_WEEKDAY)
STEP_DAYS = {WEEKLY: 7, FORTNIGHTLY: 14}
MOST_TIMES = 3000       # weekly for more than fifty years

# `starts` and `ends` are UTC, without a zone, like the rest of the API's times.
Time = namedtuple('Time', 'day starts ends skipped')


@lru_cache(maxsize=1)
def _known():
    # Not the server's own clock, nor (never listed) those that count leap seconds.
    return frozenset(available_timezones() - {'Factory', 'localtime'})


def zone(name):
    """The zone of that IANA name, or None."""
    return ZoneInfo(name) if isinstance(name, str) and name in _known() else None


def nth(first, repeats, n):
    """The n-th date, counting the first as 0."""
    if n == 0:
        return first
    if repeats in STEP_DAYS:
        return first + timedelta(days=STEP_DAYS[repeats] * n)
    month = first.month - 1 + n
    year, month = first.year + month // 12, month % 12 + 1
    days = calendar.monthrange(year, month)[1]
    if repeats == MONTHLY:
        return date(year, month, min(first.day, days))      # the 31st is the last day of a short month
    # The same weekday as the first: "the second Tuesday". A fifth is the last.
    day = 1 + (first.weekday() - date(year, month, 1).weekday()) % 7 + 7 * ((first.day - 1) // 7)
    return date(year, month, day if day <= days else day - 7)


def dates(first, repeats, until=None):
    for n in range(1 if repeats == NEVER else MOST_TIMES):
        try:
            found = nth(first, repeats, n)
        except (OverflowError, ValueError):
            return      # past the last year there is
        if until and found > until and n:
            return
        yield found


def to_utc(local, tz_name):
    return local.replace(tzinfo=zone(tz_name)).astimezone(timezone.utc).replace(tzinfo=None)


def times(first, tz_name, repeats=NEVER, until=None, length_min=60, after=None, count=1, skipped=()):
    """Up to `count` times that haven't ended by `after` (UTC); skipped ones too, marked."""
    out = []
    if not zone(tz_name):
        return out
    skip = set(skipped or ())
    for found in dates(first.date(), repeats, until):
        starts = to_utc(datetime.combine(found, first.time()), tz_name)
        ends = starts + timedelta(minutes=length_min)
        if after and ends <= after:
            continue
        out.append(Time(found.isoformat(), starts, ends, found.isoformat() in skip))
        if len(out) >= count:
            break
    return out


def upcoming(first, tz_name, repeats, until, length_min, after, skipped=()):
    """The next that's on, or None."""
    found = times(first, tz_name, repeats, until, length_min, after, 1 + len(skipped or ()), skipped)
    return next((t for t in found if not t.skipped), None)


def falls_on(first, repeats, until, day):
    """The date, when `day` (YYYY-MM-DD) is one of the event's; else None."""
    try:
        wanted = date.fromisoformat(day)
    except (TypeError, ValueError):
        return None
    for found in dates(first.date(), repeats, until):
        if found >= wanted:
            return wanted if found == wanted else None
    return None
