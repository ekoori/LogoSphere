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


@pytest.fixture(scope='session', autouse=True)
def test_admin(app, db):
    """A platform admin for this run only. Joe Rogan is an AI persona now and
    no longer an admin, and no real person's account belongs in a test. The
    account (random password, never stored) and everything registration gave
    it are removed afterwards. While the suite runs the personas are paused,
    so they don't react to what the tests do."""
    import secrets
    from datetime import datetime, timedelta
    from app.models.spheres import Sphere
    email = f'test-admin-{uuid.uuid4().hex[:10]}@example.com'
    password = secrets.token_urlsafe(18)
    sandboxes = list(Sphere.sandbox_ids())
    r = app.test_client().post('/api/register', json={'name': 'Test Admin', 'email': email, 'password': password})
    assert r.status_code == 200, r.get_json()
    uid = uuid.UUID(str(r.get_json()['user_id']))
    db.execute('UPDATE users SET is_platform_admin = true WHERE user_id = %s', [uid])
    USERS['admin'] = (email, password)
    _pause_personas(db, datetime.utcnow() + timedelta(minutes=30))
    yield uid
    _pause_personas(db, None)
    USERS.pop('admin', None)
    for sid in sandboxes:
        db.execute('UPDATE spheres SET participants = participants - %s WHERE sphere_id = %s', [[uid], sid])
    db.execute('DELETE FROM notifications WHERE user_id = %s', [uid])
    db.execute('DELETE FROM users WHERE user_id = %s', [uid])
    db.execute('DELETE FROM user_credentials WHERE user_id = %s', [uid])
    from app.utils.permissions import forget_admin_flag
    forget_admin_flag(uid)


def _pause_personas(db, until):
    """The agents' director checks agent_settings.paused_until before acting."""
    try:
        if until is None:
            db.execute("DELETE FROM agent_settings WHERE key = 'paused_until'")
        else:
            db.execute("INSERT INTO agent_settings (key, value) VALUES ('paused_until', %s)", [until.isoformat()])
    except Exception:
        pass    # no agents installed (no table): nothing to pause


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


@pytest.fixture
def new_member(db, keep_rows):
    """A throwaway account's email; afterwards the account, its credentials and
    any sandbox-sphere membership registration gave it are removed again."""
    from app.models.spheres import Sphere
    for sid in Sphere.sandbox_ids():
        keep_rows('spheres', sphere_id=sid)
    email = f'test-{uuid.uuid4().hex[:12]}@example.com'
    yield email
    row = db.execute('SELECT user_id FROM user_credentials WHERE email = %s', [email]).one()
    if row:
        db.execute('DELETE FROM users WHERE user_id = %s', [row.user_id])
        db.execute('DELETE FROM user_credentials WHERE user_id = %s', [row.user_id])
        db.execute('DELETE FROM notifications WHERE user_id = %s', [row.user_id])   # the demo invitation


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
