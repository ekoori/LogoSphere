# Pytest bootstrap.
#
# The suite is a set of integration tests: they drive the Flask app through its
# test client against a live Cassandra holding the demo seed (reseed_demo.py +
# seed_phase3.py) - the same data local dev and production start from. If no
# Cassandra is reachable the whole suite skips rather than erroring at import.
#
# Run from backend/:
#   CASSANDRA_HOST=127.0.0.1 .venv/Scripts/python -m pytest app/tests -q
import reactor  # noqa: F401 - picks the driver's event loop before it loads

import os
import socket
import sys
import uuid
import pytest

os.environ.setdefault('CASSANDRA_HOST', '127.0.0.1')
os.environ.setdefault('LOG_LEVEL', 'WARNING')


def _cassandra_up():
    host = os.environ['CASSANDRA_HOST'].split(',')[0]
    try:
        with socket.create_connection((host, 9042), timeout=2):
            return True
    except OSError:
        return False


CASSANDRA_UP = _cassandra_up()

# Demo accounts (password = first name; see database/genpass.py).
USERS = {
    'joe': ('joe.rogan@example.com', 'Joe'),          # admin1 of every seeded sphere, platform admin
    'marie': ('marie.kondo@example.com', 'Marie'),    # Riverside member; steward of Repair Cafe
    'david': ('david.attenborough@example.com', 'David'),  # Riverside member, not in Tool Library
    'elon': ('elon.musk@example.com', 'Elon'),        # AI Commons only - not in Riverside
}
# A 1x1 PNG, for image upload tests.
PNG_1PX = __import__('base64').b64decode(
    'iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==')
RIVERSIDE = '11111111-1111-1111-1111-111111111111'
AI_COMMONS = '22222222-2222-2222-2222-222222222222'
REPAIR_CAFE = 'aaaaaaaa-0000-0000-0000-000000000001'
TOOL_LIBRARY = 'bbbbbbbb-0000-0000-0000-000000000001'


@pytest.fixture(scope='session')
def app():
    if not CASSANDRA_UP:
        pytest.skip('Cassandra is not reachable on CASSANDRA_HOST:9042 - integration tests skipped')
    from app.main import app as flask_app
    flask_app.config['TESTING'] = True
    return flask_app


@pytest.fixture(scope='session')
def db(app):
    from app.db import session
    return session


class Api:
    """Thin wrapper over the Flask test client that speaks the API's auth
    contract (`Authorization: Bearer <session_id>`) and returns (status, json)."""

    def __init__(self, client):
        self.client = client
        self.tokens = {}
        self.ids = {}

    def login(self, who):
        if who not in self.tokens:
            email, pwd = USERS[who]
            r = self.client.post('/api/login', json={'email': email, 'password': pwd})
            assert r.status_code == 200, f'login failed for {who}: {r.get_json()}'
            self.tokens[who] = r.get_json()['session_id']
            self.ids[who] = r.get_json()['data']['user_id']
        return self.tokens[who]

    def _hdr(self, who):
        return {'Authorization': f'Bearer {self.login(who)}'} if who else {}

    def get(self, path, who=None):
        r = self.client.get(path, headers=self._hdr(who))
        return r.status_code, r.get_json(silent=True)

    def post(self, path, who=None, json=None, **kw):
        r = self.client.post(path, headers=self._hdr(who), json=json, **kw)
        return r.status_code, r.get_json(silent=True)

    def patch(self, path, who=None, json=None):
        r = self.client.patch(path, headers=self._hdr(who), json=json)
        return r.status_code, r.get_json(silent=True)

    def delete(self, path, who=None):
        r = self.client.delete(path, headers=self._hdr(who))
        return r.status_code, r.get_json(silent=True)

    def uid(self, who):
        self.login(who)
        return self.ids[who]

    def logout_token(self, token):
        """Ends a session a test created outside login() (e.g. by logging in itself)."""
        self.client.post('/api/logout', headers={'Authorization': f'Bearer {token}'})


@pytest.fixture(scope='session')
def api(app, db):
    """The shared client. When the session ends it logs its test accounts out
    and removes the notifications they caused, so a run against a database
    whose data matters (the demo data on ts.krbavcic.com) leaves no trace."""
    import datetime
    started = datetime.datetime.utcnow() - datetime.timedelta(seconds=5)
    client = Api(app.test_client())
    yield client
    for who in list(client.tokens):
        client.post('/api/logout', who=who)
    actors = [uuid.UUID(i) for i in client.ids.values()]
    if actors:
        for r in db.execute('SELECT user_id, created_at, notification_id, actor_id FROM notifications '
                            'WHERE created_at > %s ALLOW FILTERING', [started]):
            if r.actor_id in actors:
                db.execute('DELETE FROM notifications WHERE user_id = %s AND created_at = %s AND notification_id = %s',
                           [r.user_id, r.created_at, r.notification_id])


@pytest.fixture
def keep_rows(db):
    """Puts rows back exactly as the test found them, whatever the test does to
    them: `keep_rows('users', user_id=david)` before changing David's row. A row
    that didn't exist is deleted again; one that did is re-inserted with every
    column (via SELECT JSON / INSERT JSON). Teardowns used to write fixed "seed"
    values instead, which on real data cost e.g. David his location."""
    saved = []

    def as_key(v):
        # Ids arrive as strings; other key values (timestamps) pass through.
        if isinstance(v, str):
            try:
                return uuid.UUID(v)
            except ValueError:
                return v
        return v

    def keep(table, **key):
        key = {c: as_key(v) for c, v in key.items()}
        where = ' AND '.join(f'{c} = %s' for c in key)
        # Image blobs are left out (and left alone on restore, DEFAULT UNSET):
        # no test changes them, and reading megabytes of image through the
        # driver can stall the connection until its heartbeat gives up.
        columns = [r.column_name for r in db.execute(
            'SELECT column_name, type FROM system_schema.columns WHERE keyspace_name = %s AND table_name = %s',
            ['logosphere', table]) if r.type != 'blob']
        row = db.execute(f'SELECT JSON {", ".join(columns)} FROM {table} WHERE {where}', list(key.values())).one()
        saved.append((table, where, list(key.values()), row[0] if row else None))

    yield keep
    for table, where, values, raw in reversed(saved):
        if raw is None:
            db.execute(f'DELETE FROM {table} WHERE {where}', values)
        else:
            db.execute(f'INSERT INTO {table} JSON %s DEFAULT UNSET', [raw])


_EXIT = {'status': 0}


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    _EXIT['status'] = int(exitstatus)


def pytest_unconfigure(config):
    """The models open a live Cassandra connection at import time whose
    background threads (the event loop's) keep the interpreter from
    exiting cleanly. Force exit once pytest has printed its summary,
    preserving its status code."""
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_EXIT['status'])
