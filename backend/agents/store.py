"""The director's state, in Cassandra next to the platform's data.

  agent_settings  small key/value: paused_until, seen markers, ripple credits,
                  per-member counters, persona session tokens
  agent_queue     planned reactions with a due time (restart-safe)
  agent_done      keys of reactions already planned, so none repeats (60 days)
  agent_log       what each persona did, with Claude/image usage per day
"""
import json
import uuid
from datetime import datetime, timedelta

from cassandra.util import uuid_from_time

from app.db import session as db

QUEUE = 'queue'
DDL = [
    "CREATE TABLE IF NOT EXISTS agent_settings (key text PRIMARY KEY, value text)",
    "CREATE TABLE IF NOT EXISTS agent_queue (bucket text, due_at timestamp, task_id timeuuid, persona_id uuid, "
    "action text, payload text, origin text, sphere_id uuid, PRIMARY KEY (bucket, due_at, task_id))",
    "CREATE TABLE IF NOT EXISTS agent_done (key text PRIMARY KEY, done_at timestamp) "
    "WITH default_time_to_live = 5184000",
    "CREATE TABLE IF NOT EXISTS agent_log (day text, at timestamp, entry_id timeuuid, persona_id uuid, "
    "action text, detail text, claude_in int, claude_out int, claude_calls int, images int, dry_run boolean, "
    "PRIMARY KEY (day, at, entry_id))",
]


def ensure_tables():
    for statement in DDL:
        db.execute(statement)


# ── Settings ─────────────────────────────────────────────────────────────────
def setting(key, default=None):
    row = db.execute('SELECT value FROM agent_settings WHERE key = %s', [key]).one()
    return row.value if row else default


def set_setting(key, value):
    db.execute('INSERT INTO agent_settings (key, value) VALUES (%s, %s)', [key, value])


def json_setting(key, default=None):
    raw = setting(key)
    try:
        return json.loads(raw) if raw else default
    except ValueError:
        return default


def set_json_setting(key, value):
    set_setting(key, json.dumps(value))


def paused(now=None):
    """The test suite pauses the personas while it runs."""
    until = setting('paused_until')
    if not until:
        return False
    try:
        return datetime.fromisoformat(until) > (now or datetime.utcnow())
    except ValueError:
        return False


# ── Done keys (no reaction twice) ────────────────────────────────────────────
def is_done(key):
    return db.execute('SELECT key FROM agent_done WHERE key = %s', [key]).one() is not None


def mark_done(key):
    db.execute('INSERT INTO agent_done (key, done_at) VALUES (%s, %s)', [key, datetime.utcnow()])


# ── Queue ────────────────────────────────────────────────────────────────────
def enqueue(due_at, persona_id, action, payload, origin='real', sphere_id=None):
    task_id = uuid_from_time(datetime.utcnow())
    db.execute(
        'INSERT INTO agent_queue (bucket, due_at, task_id, persona_id, action, payload, origin, sphere_id) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s, %s)',
        [QUEUE, due_at, task_id, uuid.UUID(str(persona_id)), action, json.dumps(payload), origin,
         uuid.UUID(str(sphere_id)) if sphere_id else None])
    return task_id


def due(now=None, limit=10):
    rows = db.execute('SELECT due_at, task_id, persona_id, action, payload, origin, sphere_id FROM agent_queue '
                      'WHERE bucket = %s AND due_at <= %s LIMIT %s', [QUEUE, now or datetime.utcnow(), limit])
    return [{'due_at': r.due_at, 'task_id': r.task_id, 'persona_id': str(r.persona_id), 'action': r.action,
             'payload': json.loads(r.payload or '{}'), 'origin': r.origin,
             'sphere_id': str(r.sphere_id) if r.sphere_id else None} for r in rows]


def pending_count():
    return db.execute('SELECT COUNT(*) AS n FROM agent_queue WHERE bucket = %s', [QUEUE]).one().n


def remove(task):
    db.execute('DELETE FROM agent_queue WHERE bucket = %s AND due_at = %s AND task_id = %s',
               [QUEUE, task['due_at'], task['task_id']])


def postpone(task, minutes):
    remove(task)
    enqueue(datetime.utcnow() + timedelta(minutes=minutes), task['persona_id'], task['action'],
            task['payload'], task['origin'], task['sphere_id'])


# ── Log and usage ────────────────────────────────────────────────────────────
def log_action(persona_id, action, detail, claude_in=0, claude_out=0, claude_calls=0, images=0, dry_run=False):
    now = datetime.utcnow()
    db.execute(
        'INSERT INTO agent_log (day, at, entry_id, persona_id, action, detail, claude_in, claude_out, '
        'claude_calls, images, dry_run) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)',
        [now.strftime('%Y-%m-%d'), now, uuid_from_time(now), uuid.UUID(str(persona_id)) if persona_id else None,
         action, detail[:2000], claude_in, claude_out, claude_calls, images, dry_run])


def usage_today():
    day = datetime.utcnow().strftime('%Y-%m-%d')
    total = {'claude_calls': 0, 'claude_in': 0, 'claude_out': 0, 'images': 0, 'actions': 0}
    for r in db.execute('SELECT claude_calls, claude_in, claude_out, images FROM agent_log WHERE day = %s', [day]):
        total['claude_calls'] += r.claude_calls or 0
        total['claude_in'] += r.claude_in or 0
        total['claude_out'] += r.claude_out or 0
        total['images'] += r.images or 0
        total['actions'] += 1
    return total


# ── Persona sessions ─────────────────────────────────────────────────────────
def token_for(user_id, email, days=30):
    """A session for a persona, minted here like a service account's (no
    password involved), reused while it has more than a day left."""
    key = f'token:{user_id}'
    token = setting(key)
    if token:
        row = db.execute('SELECT expire_at FROM sessions WHERE session_id = %s', [uuid.UUID(token)]).one()
        if row and row.expire_at and row.expire_at > datetime.utcnow() + timedelta(days=1):
            return token
    token = str(uuid.uuid4())
    now = datetime.utcnow()
    db.execute('INSERT INTO sessions (session_id, user_email, user_id, creation_time, last_access_time, '
               'expire_at, data) VALUES (%s, %s, %s, %s, %s, %s, %s)',
               [uuid.UUID(token), email, uuid.UUID(str(user_id)), now, now, now + timedelta(days=days), {}])
    set_setting(key, token)
    return token
