# Pytest bootstrap.
#
# The suite is a set of integration tests: they drive the Flask app through its
# test client against a live Cassandra holding the demo seed (reseed_demo.py +
# seed_phase3.py) - the same data local dev and production start from. If no
# Cassandra is reachable the whole suite skips rather than erroring at import.
#
# Run from backend/:
#   CASSANDRA_HOST=127.0.0.1 .venv/Scripts/python -m pytest app/tests -q
from gevent import monkey  # noqa: E402 - the driver's reactor needs this on py3.12+
monkey.patch_all()

import os
import socket
import sys
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

    def uid(self, who):
        self.login(who)
        return self.ids[who]


@pytest.fixture(scope='session')
def api(app):
    return Api(app.test_client())


_EXIT = {'status': 0}


@pytest.hookimpl(trylast=True)
def pytest_sessionfinish(session, exitstatus):
    _EXIT['status'] = int(exitstatus)


def pytest_unconfigure(config):
    """The models open a live Cassandra connection at import time whose
    background threads (under the gevent reactor) keep the interpreter from
    exiting cleanly. Force exit once pytest has printed its summary,
    preserving its status code."""
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(_EXIT['status'])
