#!/usr/bin/env python
# Seed Value Cards for demo users.
# Run from the backend/ directory:
#   PYTHONPATH=backend python seed_value_cards.py

from gevent import monkey
monkey.patch_all()

import os, uuid, sys
os.environ.setdefault('CASSANDRA_HOST', '127.0.0.1')

from cassandra.cluster import Cluster
from datetime import datetime

CASSANDRA_HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(CASSANDRA_HOSTS)
session = cluster.connect('logosphere')

# ── 1. Create table if missing ────────────────────────────────────────────────
session.execute("""
CREATE TABLE IF NOT EXISTS value_cards (
    user_id          uuid,
    card_id          uuid,
    title            text,
    care_about       text,
    because          text,
    looks_like       list<text>,
    drift_looks_like text,
    in_conflict      text,
    never_do         text,
    frankl_mode      text,
    color_key        text,
    created_at       timestamp,
    PRIMARY KEY (user_id, card_id)
) WITH CLUSTERING ORDER BY (card_id ASC)
""")
print("[OK] value_cards table ready")

# ── 2. Resolve user IDs by name ───────────────────────────────────────────────
def find_user(needle):
    """Return first user_id whose combined name+surname contains needle."""
    rows = session.execute("SELECT user_id, name, surname FROM users")
    needle_l = needle.lower()
    for r in rows:
        full = f"{r.name or ''} {r.surname or ''}".strip().lower()
        if needle_l in full:
            return r.user_id
    return None

def list_users():
    rows = session.execute("SELECT user_id, name, surname FROM users")
    for r in rows:
        print(f"  {r.user_id} | name={r.name!r} | surname={r.surname!r}")

print("Users in DB:")
list_users()

joe_id = find_user('Joe Rogan') or find_user('Rogan') or find_user('Joe')
if not joe_id:
    print("[SKIP] Joe Rogan not found in users table")
    sys.exit(0)

print(f"[OK] Found Joe Rogan: {joe_id}")

# ── 3. Delete existing cards for Joe (idempotent re-seed) ────────────────────
existing = list(session.execute("SELECT card_id FROM value_cards WHERE user_id = %s", [joe_id]))
for row in existing:
    session.execute("DELETE FROM value_cards WHERE user_id = %s AND card_id = %s", [joe_id, row.card_id])
print(f"  cleared {len(existing)} existing cards")

# ── 4. Insert seed cards ─────────────────────────────────────────────────────
INSERT = """
INSERT INTO value_cards
(user_id, card_id, title, care_about, because, looks_like,
 drift_looks_like, in_conflict, never_do, frankl_mode, color_key, created_at)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

cards = [
    {
        "title": "Conversations that change minds",
        "care_about": "Long-form dialogue that takes ideas seriously — the kind where both people walk away different.",
        "because": "Most public discourse is performative. Real thinking happens in the space where no one is playing to an audience.",
        "looks_like": [
            "Sitting with a guest for 3+ hours without cutting to a break",
            "Letting an idea develop fully before pushing back",
            "Saying 'I don't know' when I genuinely don't",
        ],
        "drift_looks_like": "Booking guests for their audience not their ideas. Cutting off a thread because it's getting uncomfortable.",
        "in_conflict": "The quality of the conversation over the size of the audience.",
        "never_do": "Fake agreement to avoid conflict.",
        "frankl_mode": "creative",
        "color_key": "honey",
    },
    {
        "title": "Physical presence as a practice",
        "care_about": "The discipline of keeping the body trained — martial arts, hunting, fitness — not for aesthetics but for clarity.",
        "because": "A sharp body makes a sharp mind. Comfort is entropy. The people I respect most take their physical practice seriously.",
        "looks_like": [
            "Training jiu-jitsu at least 4 days a week regardless of schedule",
            "Taking a hunt seriously as a multi-day commitment",
            "Treating sleep and nutrition as inputs, not luxuries",
        ],
        "drift_looks_like": "Skipping training because the podcast got busy. Using 'I deserve rest' as a cover for avoidance.",
        "in_conflict": "The training over the convenience.",
        "never_do": "Shame someone for where they are in their physical journey.",
        "frankl_mode": "attitudinal",
        "color_key": "terracotta",
    },
    {
        "title": "Genuine curiosity across the spectrum",
        "care_about": "Finding what's actually interesting in every kind of person — the scientist, the comedian, the fighter, the philosopher.",
        "because": "Everyone has a world inside them that most people never ask about. Most interviewers ask questions they already know the answer to.",
        "looks_like": [
            "Researching a guest's work before the interview even if it's outside my comfort zone",
            "Following a rabbit hole on air when something surprises me",
            "Having guests I fundamentally disagree with and treating their ideas fairly",
        ],
        "drift_looks_like": "Only booking people I already like. Staying on safe topics because controversy is exhausting.",
        "in_conflict": "The unexpected insight over the comfortable brand.",
        "never_do": "Pretend to understand something I haven't thought about.",
        "frankl_mode": "experiential",
        "color_key": "leaf",
    },
]

for i, c in enumerate(cards):
    card_id = uuid.uuid4()
    session.execute(INSERT, (
        joe_id, card_id,
        c["title"], c["care_about"], c["because"], c["looks_like"],
        c["drift_looks_like"], c["in_conflict"], c["never_do"],
        c["frankl_mode"], c["color_key"],
        datetime.utcnow()
    ))
    print(f"  [OK] inserted card {i+1}: {c['title']}")

print(f"\n[DONE] Seeded {len(cards)} value cards for Joe Rogan ({joe_id})")
cluster.shutdown()
