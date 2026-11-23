"""The openings list, as Cassandra likes it: a query table, newest first, a page at a time.

  openings_feed ((place), created_at DESC, service_id DESC)
      one partition per sphere, and one (EVERYONE) for openings posted to no sphere
  opening_feed_rows ((service_id), place)
      where an opening's rows are, so a change can take them out

An opening has a row in its own sphere's partition and in each sphere it is shared with, while it is listed: the
current version, not withdrawn, and not a single one already under way. The model's own writes call sync() (see
app/models/openings.py), and start-up repairs the whole feed against `services` (cheap at this size).

A page for a viewer merges the partitions of the spheres they are in (all of them for a platform administrator) with
EVERYONE, newest first, reading only as far as the page needs. See docs/2026-11-23-cassandra-audit.md.
"""
import heapq
import uuid
from datetime import datetime

from app.db import session
from app.utils.access import as_uuid

EVERYONE = uuid.UUID(int=0)
EPOCH = datetime(1970, 1, 1)
CHUNK = 40              # rows read from one partition at a time
MOST_READ = 300         # rows one request may look at before it says where to carry on
PAGE_MAX = 60

DDL = (
    'CREATE TABLE IF NOT EXISTS openings_feed ('
    'place uuid, created_at timestamp, service_id uuid, PRIMARY KEY ((place), created_at, service_id)) '
    'WITH CLUSTERING ORDER BY (created_at DESC, service_id DESC)',
    'CREATE TABLE IF NOT EXISTS opening_feed_rows ('
    'service_id uuid, place uuid, created_at timestamp, PRIMARY KEY ((service_id), place))',
)


def ensure_tables():
    for statement in DDL:
        session.execute(statement)


def _service(service_or_id):
    if hasattr(service_or_id, 'service_id'):
        return service_or_id
    from app.models.openings import Service
    key = as_uuid(service_or_id)
    return Service.get_by_id(key) if key else None


def listed(s):
    """Whether the marketplace lists it at all (the same rule as the whole list in routes/openings.py)."""
    if not s.is_current or s.status == 'Cancelled':
        return False
    return not (s.cadence != 'perpetual' and s.status in ('In Progress', 'Completed'))


def places_of(s):
    return {s.sphere_id or EVERYONE} | set(s.shared_with or ())


def sync(service_or_id):
    """Its rows, as they should be now. Idempotent; call after any change to an opening."""
    s = _service(service_or_id)
    if s is None:
        return
    when = s.created_at or EPOCH
    want = places_of(s) if listed(s) else set()
    have = {r.place: r.created_at for r in
            session.execute('SELECT place, created_at FROM opening_feed_rows WHERE service_id = %s', [s.service_id])}
    for place in set(have) - want:
        _remove(s.service_id, place, have[place] or when)
    for place in want - set(have):
        session.execute('INSERT INTO openings_feed (place, created_at, service_id) VALUES (%s, %s, %s)',
                        [place, when, s.service_id])
        session.execute('INSERT INTO opening_feed_rows (service_id, place, created_at) VALUES (%s, %s, %s)',
                        [s.service_id, place, when])


def _remove(service_id, place, when):
    session.execute('DELETE FROM openings_feed WHERE place = %s AND created_at = %s AND service_id = %s',
                    [place, when, service_id])
    session.execute('DELETE FROM opening_feed_rows WHERE service_id = %s AND place = %s', [service_id, place])


def drop(service_id):
    """An opening that is gone altogether."""
    key = as_uuid(service_id)
    for r in session.execute('SELECT place, created_at FROM opening_feed_rows WHERE service_id = %s', [key]):
        _remove(key, r.place, r.created_at)


def repair():
    """The whole feed, checked against `services`: what start-up does."""
    from app.models.openings import Service
    known = set()
    for s in Service.get_all():
        known.add(s.service_id)
        sync(s)
    for r in list(session.execute('SELECT service_id, place, created_at FROM opening_feed_rows')):
        if r.service_id not in known:
            _remove(r.service_id, r.place, r.created_at)


# -- Reading --------------------------------------------------------------------
def cursor_of(created_at, service_id):
    return f'{(created_at or EPOCH).isoformat()}~{service_id}'


def parse_cursor(text):
    """(created_at, service_id) or None for no cursor; ValueError for a broken one."""
    if not text:
        return None
    when, _, sid = str(text).partition('~')
    return datetime.fromisoformat(when), uuid.UUID(sid)


def _partition(place, before):
    """One partition's rows, newest first, below `before`, read a chunk at a time."""
    last = before
    while True:
        if last:
            rows = list(session.execute(
                f'SELECT created_at, service_id FROM openings_feed WHERE place = %s AND (created_at, service_id) < (%s, %s) '
                f'LIMIT {CHUNK}', [place, last[0], last[1]]))
        else:
            rows = list(session.execute(
                f'SELECT created_at, service_id FROM openings_feed WHERE place = %s LIMIT {CHUNK}', [place]))
        for r in rows:
            yield r.created_at, r.service_id
        if len(rows) < CHUNK:
            return
        last = (rows[-1].created_at, rows[-1].service_id)


def viewer_places(sight, only=None):
    if sight.admin:
        mine = {r.sphere_id for r in session.execute('SELECT sphere_id FROM spheres')}
    else:
        mine = set(sight.spheres)
    mine.add(EVERYONE)
    if only is not None:
        return {only} & mine
    return mine


def page(sight, limit, before=None, keep=lambda s: True, only=None):
    """(the openings, oldest-first cursor to carry on from or None). `keep` filters; `only` is one sphere."""
    from app.models.openings import Service
    limit = max(1, min(int(limit), PAGE_MAX))
    feeds = [_partition(p, before) for p in viewer_places(sight, only)]
    merged = heapq.merge(*feeds, reverse=True)
    out, seen, read, last = [], set(), 0, None
    for created_at, sid in merged:
        if sid in seen:
            continue                    # shared into two of the viewer's spheres
        seen.add(sid)
        read += 1
        last = (created_at, sid)
        s = Service.get_by_id(sid)
        if s and listed(s) and sight.opening(s) and keep(s):
            out.append(s)
        if len(out) >= limit or read >= MOST_READ:
            break
    else:
        return out, None                # read to the end
    more = any(sid not in seen for _, sid in merged)
    return out, cursor_of(*last) if more else None
