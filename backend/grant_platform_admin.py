# grant_platform_admin.py — operator tool: grant or revoke platform-admin status.
#
#   CASSANDRA_HOST=127.0.0.1 .venv/bin/python grant_platform_admin.py joe.rogan@example.com
#   CASSANDRA_HOST=127.0.0.1 .venv/bin/python grant_platform_admin.py --revoke someone@example.com
#   CASSANDRA_HOST=127.0.0.1 .venv/bin/python grant_platform_admin.py --list
#
# Admin status lives in users.is_platform_admin and is only ever set here — never
# from anything a user can do in the app (registration doesn't verify emails).
import argparse
import os
import sys

from gevent import monkey  # noqa: E402  (driver reactor on py3.12+)
monkey.patch_all()
from cassandra.cluster import Cluster  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument('email', nargs='?')
ap.add_argument('--revoke', action='store_true')
ap.add_argument('--list', action='store_true')
args = ap.parse_args()

session = Cluster(os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')).connect('logosphere')
session.default_timeout = 30

try:
    session.execute('ALTER TABLE users ADD is_platform_admin boolean')
except Exception:
    pass  # already there

if args.list:
    for r in session.execute('SELECT user_id, email, name, is_platform_admin FROM users'):
        if getattr(r, 'is_platform_admin', False):
            print(f'{r.user_id}  {r.email}  {r.name}')
    sys.stdout.flush(); os._exit(0)

if not args.email:
    ap.error('email is required unless --list')

row = session.execute('SELECT user_id FROM user_credentials WHERE email = %s', [args.email]).one()
if not row:
    print(f'No account registered with {args.email}')
    sys.stdout.flush(); os._exit(1)

session.execute('UPDATE users SET is_platform_admin = %s WHERE user_id = %s',
                [not args.revoke, row.user_id])
print(f'{"Revoked" if args.revoke else "Granted"} platform admin: {args.email} ({row.user_id})')
sys.stdout.flush(); os._exit(0)
