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

# ── 5. Elon Musk ─────────────────────────────────────────────────────────────
elon_id = find_user('Elon Musk') or find_user('Musk') or find_user('Elon')
if not elon_id:
    print("[SKIP] Elon Musk not found in users table")
else:
    print(f"[OK] Found Elon Musk: {elon_id}")

    existing_elon = list(session.execute("SELECT card_id FROM value_cards WHERE user_id = %s", [elon_id]))
    for row in existing_elon:
        session.execute("DELETE FROM value_cards WHERE user_id = %s AND card_id = %s", [elon_id, row.card_id])
    print(f"  cleared {len(existing_elon)} existing cards")

    elon_cards = [
        {
            "title": "Making humanity multi-planetary",
            "care_about": "Ensuring the long-term survival of consciousness by making life multiplanetary before an extinction event wipes out everything we've built.",
            "because": "All civilisations that have ever existed are gone. Earth is the only backup. A single-planet species is an unacceptable risk over geological timescales.",
            "looks_like": [
                "Setting reusable rocket timelines that most engineers call impossible",
                "Treating Mars colonisation as an engineering problem, not a dream",
                "Funding SpaceX personally when it was weeks from bankruptcy",
            ],
            "drift_looks_like": "Treating space as a prestige project rather than a survival imperative. Optimising for quarterly revenue over a 10-year mission.",
            "in_conflict": "The mission over the optics.",
            "never_do": "Accept that something is impossible without doing the physics.",
            "frankl_mode": "creative",
            "color_key": "terracotta",
        },
        {
            "title": "Accelerating the energy transition",
            "care_about": "Moving civilisation off fossil fuels as fast as physically possible — not out of environmentalism but because sustainable energy is simply the correct long-term path.",
            "because": "The atmosphere is a finite buffer. Every year of delay locks in compounding consequences. The technology exists; the bottleneck is manufacturing scale and political inertia.",
            "looks_like": [
                "Building the world's largest battery factories before there was demand",
                "Treating the energy problem as a manufacturing problem first",
                "Publishing Tesla's patents openly to accelerate the entire industry",
            ],
            "drift_looks_like": "Treating sustainability as a marketing angle. Optimising vehicle range for luxury buyers over energy density for affordability.",
            "in_conflict": "Speed of transition over profit margin on any single product.",
            "never_do": "Pretend that incremental improvement is enough.",
            "frankl_mode": "attitudinal",
            "color_key": "leaf",
        },
        {
            "title": "Free flow of information",
            "care_about": "The ability of any person to say what they actually think without institutional gatekeeping deciding what is and isn't permitted discourse.",
            "because": "Centralised control of speech has historically been the first tool of authoritarians. An open forum — even a messy one — is preferable to a curated one.",
            "looks_like": [
                "Reinstating accounts banned for political speech rather than illegal activity",
                "Publishing moderation decisions and algorithms rather than hiding them",
                "Tolerating criticism of myself on the platform I own",
            ],
            "drift_looks_like": "Permitting any speech I personally agree with while suppressing speech I find inconvenient. Treating 'free speech' as a brand rather than a practice.",
            "in_conflict": "The open forum over advertiser comfort.",
            "never_do": "Silence someone for saying something true that I find uncomfortable.",
            "frankl_mode": "experiential",
            "color_key": "honey",
        },
    ]

    for i, c in enumerate(elon_cards):
        card_id = uuid.uuid4()
        session.execute(INSERT, (
            elon_id, card_id,
            c["title"], c["care_about"], c["because"], c["looks_like"],
            c["drift_looks_like"], c["in_conflict"], c["never_do"],
            c["frankl_mode"], c["color_key"],
            datetime.utcnow()
        ))
        print(f"  [OK] inserted card {i+1}: {c['title']}")

    print(f"\n[DONE] Seeded {len(elon_cards)} value cards for Elon Musk ({elon_id})")

cluster.shutdown()
