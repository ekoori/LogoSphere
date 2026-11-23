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

# The suite never pushes to real phones, though it runs with production's
# settings (app/utils/push); test_api_push stands in for Firebase.
os.environ.pop('FCM_CREDENTIALS', None)
# Nor sends email, whatever mail.env holds; test_api_email stands in for Mailgun.
os.environ['MAIL'] = 'off'

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
def test_admin(request):
    """A platform admin for this run only. Joe Rogan is an AI persona now and
    no longer an admin, and no real person's account belongs in a test. The
    account (random password, never stored) and everything registration gave
    it are removed afterwards. While the suite runs the personas are paused,
    so they don't react to what the tests do."""
    if not CASSANDRA_UP:
        yield None          # unit tests (backend/agents/tests) need no database
        return
    app, db = request.getfixturevalue('app'), request.getfixturevalue('db')
    import secrets
    from datetime import datetime, timedelta
    email = f'test-admin-{uuid.uuid4().hex[:10]}@example.com'
    password = secrets.token_urlsafe(18)
    r = app.test_client().post('/api/register', json={'name': 'Test Admin', 'email': email, 'password': password})
    assert r.status_code == 200, r.get_json()
    uid = uuid.UUID(str(r.get_json()['user_id']))
    db.execute('UPDATE users SET is_platform_admin = true WHERE user_id = %s', [uid])
    USERS['admin'] = (email, password)
    _pause_personas(db, datetime.utcnow() + timedelta(minutes=30))
    yield uid
    _pause_personas(db, None)
    # Feed rows of openings the tests made and removed go too (app/utils/openings_feed.py).
    from app.utils import openings_feed
    openings_feed.repair()
    USERS.pop('admin', None)
    # Out of every sphere it ended up in (sandboxes at registration, the demo
    # spheres a test joined it to).
    for row in db.execute('SELECT sphere_id, participants FROM spheres'):
        if row.participants and uid in row.participants:
            db.execute('UPDATE spheres SET participants = participants - %s WHERE sphere_id = %s', [[uid], row.sphere_id])
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


@pytest.fixture(autouse=True)
def wrong_passwords(monkeypatch):
    """Each test counts its own failed sign-ins, in memory: never the real allowances."""
    if not CASSANDRA_UP:
        return None
    from app.utils import attempts
    counts = {}
    monkeypatch.setattr(attempts, '_used', lambda name: counts.get(name, 0))
    monkeypatch.setattr(attempts, '_count', lambda name, most: counts.update({name: counts.get(name, 0) + 1}))
    return counts


PERSON_PASSWORD = 'a-long-password-1'


class Person:
    def __init__(self, client, email, user_id, token):
        self.client, self.email, self.id = client, email, user_id
        self.headers = {'Authorization': f'Bearer {token}'}

    def get(self, path):
        r = self.client.get(path, headers=self.headers)
        return r.status_code, r.get_json(silent=True)

    def post(self, path, json=None):
        r = self.client.post(path, headers=self.headers, json=json if json is not None else {})
        return r.status_code, r.get_json(silent=True)

    def told(self, kind):
        return [n for n in self.get('/api/notifications')[1]['notifications'] if n['type'] == kind]


@pytest.fixture
def people(app, db, keep_rows, test_admin, monkeypatch):
    """Ada and Ben share only a sphere of their own; Cy shares nothing with either."""
    from app.models.spheres import Sphere
    from app.utils import mailer, messaging, safety
    used, run = set(), uuid.uuid4().hex

    def bucket(name):
        key = f'test:{run}:{name}'
        used.add(key)
        return key

    monkeypatch.setattr(mailer, '_bucket', bucket)              # never the real allowances
    monkeypatch.setattr(safety, 'administrators', lambda: [test_admin])     # never the real one's inbox
    sandboxes = Sphere.sandbox_ids()
    for sid in sandboxes:
        keep_rows('spheres', sphere_id=sid)
    made = {}
    for name in ('Ada', 'Ben', 'Cy'):
        client = app.test_client()
        email = f'test-{name.lower()}-{uuid.uuid4().hex[:10]}@example.com'
        r = client.post('/api/register', json={'name': f'Test {name}', 'email': email, 'password': PERSON_PASSWORD})
        assert r.status_code == 200, r.get_json()
        uid = uuid.UUID(str(r.get_json()['user_id']))
        token = client.post('/api/login', json={'email': email, 'password': PERSON_PASSWORD}).get_json()['session_id']
        made[name.lower()] = Person(client, email, uid, token)
        for sid in sandboxes:       # a sandbox would make every newcomer sphere-mates
            db.execute('UPDATE spheres SET participants = participants - %s WHERE sphere_id = %s', [[uid], sid])
    status, shared = made['ada'].post('/api/spheres', {'name': 'Messages test sphere (delete me)', 'description': 'x'})
    assert status == 201, shared
    sphere = uuid.UUID(shared['sphere_id'])
    assert made['ben'].post(f'/api/spheres/{sphere}/join')[0] in (200, 201)
    made['sphere'] = sphere
    yield made

    ids = {p.id for p in (made['ada'], made['ben'], made['cy'])}
    everyone = list(ids)
    for a in everyone:
        for b in everyone:
            if str(a) < str(b):
                db.execute('DELETE FROM direct_messages WHERE conversation_id = %s', [messaging.conversation(a, b)])
        for table in ('message_inbox', 'notifications', 'blocks', 'trail_acknowledgements'):
            key = 'trail_id' if table == 'trail_acknowledgements' else 'user_id'
            db.execute(f'DELETE FROM {table} WHERE {key} = %s', [a])
        db.execute('DELETE FROM follows WHERE follower_id = %s', [a])
        for table in ('users', 'user_credentials'):
            db.execute(f'DELETE FROM {table} WHERE user_id = %s', [a])
    for r in db.execute('SELECT session_id, user_id FROM sessions'):
        if r.user_id in ids:
            db.execute('DELETE FROM sessions WHERE session_id = %s', [r.session_id])
    for r in db.execute('SELECT report_id, reporter_id FROM reports'):
        if r.reporter_id in ids:
            db.execute('DELETE FROM reports WHERE report_id = %s', [r.report_id])
    for r in db.execute('SELECT service_id, provider_id FROM services'):
        if r.provider_id in ids:
            for table in ('services', 'opening_acceptances', 'opening_likes'):
                db.execute(f'DELETE FROM {table} WHERE service_id = %s', [r.service_id])
    for r in db.execute('SELECT event_id, creator_id FROM events'):
        if r.creator_id in ids:
            for table in ('events', 'event_replies'):
                db.execute(f'DELETE FROM {table} WHERE event_id = %s', [r.event_id])
    for r in db.execute('SELECT invite_hash, made_by FROM invites'):
        if r.made_by in ids:
            for table in ('invites', 'invite_uses'):
                db.execute(f'DELETE FROM {table} WHERE invite_hash = %s', [r.invite_hash])
    db.execute('DELETE FROM announcements WHERE group_id = %s', [sphere])
    db.execute('DELETE FROM spheres WHERE sphere_id = %s', [sphere])
    db.execute('DELETE FROM notifications WHERE user_id = %s', [test_admin])
    for key in used:
        db.execute('DELETE FROM mail_counts WHERE bucket = %s', [key])


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
