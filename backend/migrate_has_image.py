# migrate_has_image.py — one-off backfill: add has_image flags so list endpoints
# never have to read banner blobs, and stamp existing rows. Idempotent.
#
#   CASSANDRA_HOST=127.0.0.1 .venv/bin/python migrate_has_image.py
import os
import sys

from gevent import monkey  # noqa: E402
monkey.patch_all()
from cassandra.cluster import Cluster  # noqa: E402

session = Cluster(os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')).connect('logosphere')
session.default_timeout = 60

for t in ('spheres', 'alliances', 'projects', 'services'):
    try:
        session.execute(f'ALTER TABLE {t} ADD has_image boolean')
        print(f'added {t}.has_image')
    except Exception:
        pass

for table, idcol in (('spheres', 'sphere_id'), ('alliances', 'alliance_id'),
                     ('projects', 'project_id'), ('services', 'service_id')):
    n = flagged = 0
    for r in session.execute(f'SELECT {idcol}, image FROM {table}'):
        n += 1
        has = bool(r.image)
        session.execute(f'UPDATE {table} SET has_image = %s WHERE {idcol} = %s', [has, getattr(r, idcol)])
        flagged += has
    print(f'{table}: {n} rows, {flagged} with an image')

print('done')
sys.stdout.flush()
os._exit(0)
