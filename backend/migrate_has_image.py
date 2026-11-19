# migrate_has_image.py — one-off backfill: add has_image flags so reads never
# have to load image blobs, and stamp existing rows. Idempotent; safe to re-run.
#
#   cd backend && set -a && . ./prod.env && set +a && .venv/bin/python -u migrate_has_image.py
#
# Run it BEFORE deploying code whose models list has_image (cqlengine selects
# every model column, so a missing column fails every read of that table).
#
# Whether a row has an image is read from writetime(<blob>) - null exactly when
# the cell is unset - so the backfill never pulls an image through the driver
# either (megabyte blobs are what stalled connections in the first place).
import os
import sys

import reactor  # noqa: F401 - picks the driver's event loop before it loads
from cassandra.cluster import Cluster  # noqa: E402

session = Cluster(os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')).connect('logosphere')
session.default_timeout = 60

# table -> (primary key columns, blob column)
TABLES = {
    'spheres': (['sphere_id'], 'image'),
    'alliances': (['alliance_id'], 'image'),
    'projects': (['project_id'], 'image'),
    'services': (['service_id'], 'image'),
    'meaning_trail': (['user_id', 'exchange_id'], 'exchange_image'),
}

for table in TABLES:
    try:
        session.execute(f'ALTER TABLE {table} ADD has_image boolean')
        print(f'added {table}.has_image')
    except Exception:
        pass  # already there

for table, (keys, blob) in TABLES.items():
    where = ' AND '.join(f'{k} = %s' for k in keys)
    n = stamped = flagged = 0
    for r in session.execute(f'SELECT {", ".join(keys)}, has_image, writetime({blob}) AS wt FROM {table}'):
        n += 1
        if r.has_image is not None:
            continue  # already kept up to date by the writes
        has = r.wt is not None
        session.execute(f'UPDATE {table} SET has_image = %s WHERE {where}', [has] + [getattr(r, k) for k in keys])
        stamped += 1
        flagged += has
    print(f'{table}: {n} rows, {stamped} stamped ({flagged} with an image)')

print('done')
sys.stdout.flush()
os._exit(0)
