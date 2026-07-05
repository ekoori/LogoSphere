# seed_phase3.py — ADDITIVE demo-data seed (safe to re-run; upserts, never deletes).
#
#   1. Ensures every existing user belongs to at least one sphere.
#   2. Creates two openings (one offer, one need) for every user.
#
# Opening ids are derived deterministically (uuid5) from the user id, so
# re-running upserts the same two rows per user instead of piling up duplicates.
# Run from backend/:  CASSANDRA_HOST=127.0.0.1 .venv/Scripts/python seed_phase3.py
import os
import uuid
from datetime import datetime, timedelta

from gevent import monkey  # noqa: E402
monkey.patch_all()
from cassandra.cluster import Cluster  # noqa: E402

HOST = os.environ.get('CASSANDRA_HOST', '127.0.0.1')
KS = 'logosphere'
NS = uuid.UUID('7f0a1b2c-3d4e-5f60-7182-93a4b5c6d7e8')  # stable namespace for this seed

cluster = Cluster([HOST])
session = cluster.connect(KS)
session.default_timeout = 30

# ── Load users & spheres ─────────────────────────────────────────────────────
users = [(r.user_id, (r.name or 'A member'), (getattr(r, 'surname', '') or ''))
         for r in session.execute('SELECT user_id, name, surname FROM users')]
spheres = [(r.sphere_id, r.name, list(r.participants or []))
           for r in session.execute('SELECT sphere_id, name, participants FROM spheres')]
spheres.sort(key=lambda s: str(s[0]))  # deterministic round-robin order

print(f'Loaded {len(users)} users and {len(spheres)} spheres')

# Set of users already in at least one sphere.
member_of = {}  # user_id -> (sphere_id, sphere_name)
for sid, sname, parts in spheres:
    for uid in parts:
        member_of.setdefault(uid, (sid, sname))

# ── 1. Assign sphere-less users round-robin across spheres ────────────────────
assigned = 0
rr = 0
for uid, name, surname in users:
    if uid in member_of:
        continue
    sid, sname, parts = spheres[rr % len(spheres)]
    rr += 1
    session.execute(
        'UPDATE spheres SET participants = participants + %s, '
        'member_roles = member_roles + %s WHERE sphere_id = %s',
        [[uid], {uid: 'member'}, sid])
    member_of[uid] = (sid, sname)
    assigned += 1
print(f'Assigned {assigned} previously sphere-less users to a sphere')

# ── 2. Two openings per user (one offer, one need) ────────────────────────────
OFFERS = [
    ('Sharing what I know', 'Happy to teach or lend a hand with something I am good at — reach out and let us set a time.', ['skill sharing', 'generosity']),
    ('A pair of willing hands', 'Got a free afternoon and would love to help a neighbour with a project. No charge, only good company.', ['mutual aid', 'community']),
    ('Tools & gear to borrow', 'I have equipment sitting idle that someone could put to good use this week. Borrow it, return it cared-for.', ['sharing over owning', 'repair culture']),
    ('Homegrown surplus to give', 'More than I can use from my own patch — take what you will enjoy and pass some on.', ['food sovereignty', 'generosity']),
]
NEEDS = [
    ('Looking for a helping hand', 'I have a small project I cannot finish alone. If you have an hour to spare, I would be grateful.', ['mutual aid', 'trust']),
    ('Seeking someone who knows how', 'Trying to learn a new skill and would love a patient guide to point me in the right direction.', ['skill sharing', 'learning']),
    ('Could use a tool for a day', 'Just need to borrow the right kit for one job — will treat it as my own and return it promptly.', ['sharing over owning', 'community']),
    ('Hoping to swap for something', 'Have things to offer in return — let us find a fair, money-free exchange that works for us both.', ['gift economy', 'reciprocity']),
]

base = datetime(2026, 6, 25, 9, 0, 0)
SERVICE_Q = (
    'INSERT INTO services '
    '(service_id, type, title, description, provider_id, provider_name, '
    'sphere_id, sphere_name, status, created_at, values, cadence) '
    'VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)')

made = 0
for i, (uid, name, surname) in enumerate(users):
    sid, sname = member_of[uid]
    full = (f'{name} {surname}').strip()
    o_title, o_desc, o_vals = OFFERS[i % len(OFFERS)]
    n_title, n_desc, n_vals = NEEDS[i % len(NEEDS)]
    offer_id = uuid.uuid5(NS, f'{uid}-seed-offer')
    need_id = uuid.uuid5(NS, f'{uid}-seed-need')
    session.execute(SERVICE_Q, (
        offer_id, 'offer', o_title, o_desc, uid, full, sid, sname,
        'Posted', base + timedelta(minutes=i), o_vals, 'perpetual'))
    session.execute(SERVICE_Q, (
        need_id, 'need', n_title, n_desc, uid, full, sid, sname,
        'Open', base + timedelta(minutes=i, seconds=30), n_vals, 'single'))
    made += 2

print(f'Upserted {made} openings ({made // 2} per-user pairs)')
print('Done.')
cluster.shutdown()
os._exit(0)
