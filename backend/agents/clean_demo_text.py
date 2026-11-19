"""One-off: give the demo real-sounding text (agents/demo_rewrites.json) in
place of generator placeholders, write up exchanges that had no description,
and take members' likes off their own openings. Ids, dates, likes, acceptances
and exchanges stay as they are. Dry run unless --apply.

  cd backend && set -a && . ./prod.env && set +a
  .venv/bin/python -m agents.clean_demo_text [--apply]
"""
import json
import os
import sys
from pathlib import Path

import reactor  # noqa: F401 - picks the driver's event loop before it loads

from app.db import session as db  # noqa: E402

DATA = json.loads(Path(__file__).with_name('demo_rewrites.json').read_text(encoding='utf-8'))
APPLY = '--apply' in sys.argv


def resolve(key, ids, what):
    found = [i for i in ids if str(i) == key or str(i).startswith(key)]
    if len(found) != 1:
        raise SystemExit(f'{what} {key!r} matches {len(found)} rows - fix demo_rewrites.json')
    return found[0]


def main():
    services = {r.service_id: r for r in db.execute(
        'SELECT service_id, title, description, provider_id, acting_user_id FROM services')}
    changed = 0
    for key, new in DATA['openings'].items():
        sid = resolve(key, services, 'opening')
        old = services[sid]
        print(f'opening {str(sid)[:8]}: {old.title!r}\n    -> {new["title"]!r}')
        if APPLY:
            db.execute('UPDATE services SET title = %s, description = %s WHERE service_id = %s',
                       [new['title'], new['description'], sid])
        changed += 1
    for old_title, new_title in DATA.get('opening_titles', {}).items():
        for sid, s in services.items():
            if s.title == old_title:
                print(f'opening {str(sid)[:8]}: {old_title!r} -> {new_title!r}')
                if APPLY:
                    db.execute('UPDATE services SET title = %s WHERE service_id = %s', [new_title, sid])
                changed += 1

    trail = {r.exchange_id: r for r in db.execute(
        'SELECT user_id, exchange_id, exchange_description, exchange_long_description FROM meaning_trail')}
    for key, new in DATA['exchanges'].items():
        xid = resolve(key, trail, 'exchange')
        row = trail[xid]
        sets, params = [], []
        if 'title' in new:
            sets.append('exchange_description = %s'); params.append(new['title'])
        if 'description' in new:
            sets.append('exchange_long_description = %s'); params.append(new['description'])
        print(f'exchange {str(xid)[:8]}: {row.exchange_description!r} -> {new.get("title", "(title kept)")!r}'
              + (f' + description' if 'description' in new else ''))
        if APPLY:
            db.execute(f'UPDATE meaning_trail SET {", ".join(sets)} WHERE user_id = %s AND exchange_id = %s',
                       params + [row.user_id, xid])
        changed += 1

    # The placeholders were all posted in one go (the same second), so they
    # read newest-first in blocks per person. Spread the ones nobody has acted
    # on across the following months - deterministic per id.
    import hashlib
    from datetime import datetime, timedelta
    start, span = datetime(2026, 7, 6, 7, 0), timedelta(days=130)
    acted = {r.service_id for r in db.execute('SELECT service_id FROM opening_acceptances')}
    spread = 0
    for key in DATA['openings']:
        sid = resolve(key, services, 'opening')
        status = db.execute('SELECT status FROM services WHERE service_id = %s', [sid]).one().status
        if sid in acted or status != 'Posted':
            continue
        frac = int(hashlib.sha256(str(sid).encode()).hexdigest()[:8], 16) / 0xFFFFFFFF
        when = start + span * frac
        when = when.replace(hour=7 + int(frac * 1000) % 14, minute=int(frac * 100000) % 60)
        if APPLY:
            db.execute('UPDATE services SET created_at = %s WHERE service_id = %s', [when, sid])
        spread += 1
    print(f'{spread} untouched openings {"re-dated" if APPLY else "would be re-dated"} between '
          f'{start:%d %b} and {start + span:%d %b %Y}')

    self_likes = 0
    for sid, s in services.items():
        own = {s.provider_id, s.acting_user_id} - {None}
        for like in db.execute('SELECT user_id FROM opening_likes WHERE service_id = %s', [sid]):
            if like.user_id in own:
                print(f'self-like off {str(sid)[:8]} ({s.title!r})')
                if APPLY:
                    db.execute('DELETE FROM opening_likes WHERE service_id = %s AND user_id = %s', [sid, like.user_id])
                self_likes += 1

    print(f'\n{changed} texts and {self_likes} self-likes {"changed" if APPLY else "would change (dry run: add --apply)"}')


if __name__ == '__main__':
    main()
    sys.stdout.flush()
    os._exit(0)
