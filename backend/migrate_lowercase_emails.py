# migrate_lowercase_emails.py — one-off: store every email lower-case. Sign-in
# and registration now lower-case what they're given, so an account stored as
# "Name.Surname@…" could no longer sign in until its row is lower-cased too.
#
#   cd backend && set -a && . ./prod.env && set +a && .venv/bin/python -u migrate_lowercase_emails.py [--apply]
#
# Without --apply it only reports. Two accounts whose emails differ only in
# case are left alone and listed: they need a person to decide.
import os
import sys
from collections import defaultdict

import reactor  # noqa: F401 - picks the driver's event loop before it loads
from cassandra.cluster import Cluster  # noqa: E402

apply = '--apply' in sys.argv
session = Cluster(os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')).connect('logosphere')
session.default_timeout = 60

by_lower = defaultdict(list)
for r in session.execute('SELECT user_id, email FROM user_credentials'):
    if r.email:
        by_lower[r.email.strip().lower()].append(r)

changed = clashes = 0
for lower, rows in by_lower.items():
    if len(rows) > 1:
        clashes += 1
        print(f'CLASH, left alone: {len(rows)} accounts share {lower!r}: {[str(r.user_id) for r in rows]}')
        continue
    row = rows[0]
    if row.email == lower:
        continue
    changed += 1
    print(f'{"lower-casing" if apply else "would lower-case"} the email of {row.user_id}')
    if apply:
        session.execute('UPDATE user_credentials SET email = %s WHERE user_id = %s', [lower, row.user_id])
        session.execute('UPDATE users SET email = %s WHERE user_id = %s', [lower, row.user_id])

print(f'{changed} {"changed" if apply else "to change"}, {clashes} clashes'
      + ('' if apply else ' (dry run: add --apply)'))
os._exit(0)
