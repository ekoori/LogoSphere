#!/usr/bin/env python
# Combined demo reseed — Group I.
# Drops and recreates meaning_trail (interaction_* → exchange_*),
# drops/recreates comment_likes, likes, audit_log with exchange_id,
# applies services ALTERs idempotently, re-seeds all demo data,
# and seeds value cards for Joe Rogan + Elon Musk.
#
# SAFE: does NOT touch users, user_credentials, or sessions.
#
# Run from backend/ directory:
#   PYTHONPATH=backend python reseed_demo.py

from gevent import monkey
monkey.patch_all()

import os, uuid, sys
from datetime import datetime

os.environ.setdefault('CASSANDRA_HOST', '127.0.0.1')
from cassandra.cluster import Cluster

HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(HOSTS)
session = cluster.connect()
session.execute("USE logosphere")
print("[OK] Connected to Cassandra, using keyspace logosphere")

def run(cql, params=None):
    try:
        session.execute(cql, params) if params else session.execute(cql)
        return True
    except Exception as e:
        return e

def drop_if(name, kind='TABLE'):
    r = run(f"DROP {kind} IF EXISTS logosphere.{name}")
    msg = f"[OK] Dropped {kind} {name}" if r is True else f"[WARN] Could not drop {kind} {name}: {r}"
    print(msg)

# ── Step 1: Drop dependents first ─────────────────────────────────────────────
drop_if('vw_meaning_trail_summary', 'MATERIALIZED VIEW')
for idx in ['meaning_trail_other_user_id_idx', 'meaning_trail_project_id_idx', 'meaning_trail_exchange_status_idx']:
    drop_if(idx, 'INDEX')

# ── Step 2: Drop and recreate tables with exchange_id ─────────────────────────
for tbl in ['meaning_trail', 'comment_likes', 'likes', 'audit_log']:
    drop_if(tbl)

run("""
CREATE TABLE logosphere.meaning_trail (
    user_id uuid,
    exchange_id uuid,
    gratitude_comment text,
    gratitude_comment_id uuid,
    gratitude_comment_timestamp timestamp,
    last_modified_at timestamp,
    last_modified_by uuid,
    other_comment text,
    other_comment_author_id uuid,
    other_comment_author_name text,
    other_comment_id uuid,
    other_comment_timestamp timestamp,
    other_user_id uuid,
    other_user_name text,
    project_id uuid,
    project_name text,
    project_start_timestamp timestamp,
    exchange_description text,
    exchange_status text,
    user_comment text,
    user_comment_id uuid,
    user_comment_timestamp timestamp,
    validation_flags text,
    PRIMARY KEY (user_id, exchange_id)
) WITH CLUSTERING ORDER BY (exchange_id DESC)
""")
print("[OK] Created meaning_trail (exchange_* columns)")

run("""
CREATE TABLE logosphere.comment_likes (
    exchange_id uuid,
    comment_type text,
    likes counter,
    PRIMARY KEY (exchange_id, comment_type)
) WITH CLUSTERING ORDER BY (comment_type ASC)
""")
print("[OK] Created comment_likes")

run("""
CREATE TABLE logosphere.likes (
    exchange_id uuid,
    comment_type text,
    user_id uuid,
    PRIMARY KEY ((exchange_id, comment_type), user_id)
) WITH CLUSTERING ORDER BY (user_id ASC)
""")
print("[OK] Created likes")

run("""
CREATE TABLE logosphere.audit_log (
    id uuid PRIMARY KEY,
    action_type text,
    description text,
    executed_at timestamp,
    executed_by uuid,
    exchange_id uuid,
    user_id uuid
)
""")
print("[OK] Created audit_log")

# ── Step 3: Recreate indexes + materialized view ──────────────────────────────
run("CREATE INDEX IF NOT EXISTS meaning_trail_other_user_id_idx ON logosphere.meaning_trail (other_user_id)")
run("CREATE INDEX IF NOT EXISTS meaning_trail_project_id_idx    ON logosphere.meaning_trail (project_id)")
run("CREATE INDEX IF NOT EXISTS meaning_trail_exchange_status_idx ON logosphere.meaning_trail (exchange_status)")
print("[OK] Recreated meaning_trail indexes")

r = run("""
CREATE MATERIALIZED VIEW logosphere.vw_meaning_trail_summary AS
    SELECT user_id, exchange_id, exchange_status, project_id
    FROM logosphere.meaning_trail
    WHERE user_id IS NOT NULL AND project_id IS NOT NULL
      AND exchange_status IS NOT NULL AND exchange_id IS NOT NULL
    PRIMARY KEY ((user_id, exchange_id), exchange_status)
    WITH CLUSTERING ORDER BY (exchange_status ASC)
""")
print("[OK] Created materialized view" if r is True else f"[WARN] Materialized view: {r}")

# ── Step 4: Apply services ALTERs idempotently ────────────────────────────────
for col in ["ADD likes int", "ADD project_name text", "ADD image_key text",
            "ADD cadence text", "ADD accepted_by uuid", "ADD accepted_by_name text"]:
    r = run(f"ALTER TABLE logosphere.services {col}")
    if r is True:
        print(f"[OK]   services: {col}")
    elif "already exists" in str(r).lower() or "duplicate" in str(r).lower():
        print(f"[SKIP] services: {col} (already exists)")
    else:
        print(f"[WARN] services: {col} — {r}")

# ── Step 5: Re-seed demo data ─────────────────────────────────────────────────
def U(s): return uuid.UUID(s)
def T(s): return datetime.strptime(s, '%Y-%m-%d %H:%M:%S')

JOE     = U('fe878ccf-aba7-4b16-8b5f-847f7db6e0ad')
ELON    = U('b4dfd93d-a9e0-4bf8-8685-735dbde17ff7')
MARIE   = U('9c89c702-6c61-49c8-9f0c-47b8e4e84e4b')
STEVE   = U('16f033ca-2b2c-4745-a537-82999209774c')
DAVID   = U('aeeb7c42-d2d5-4e4e-8ed3-af313f5d6358')
EMMA    = U('ff52c318-95e0-4f1f-89cc-62551c814a83')
BILL    = U('86eb2b6c-1771-4533-9bd8-fca4f83fe61a')
STEPHEN = U('7d6e67f2-5c64-4175-8330-a0d1b2b9c45f')
SP1 = U('11111111-1111-1111-1111-111111111111')
SP2 = U('22222222-2222-2222-2222-222222222222')
SP3 = U('33333333-3333-3333-3333-333333333333')
AL1 = U('aaaaaaaa-0000-0000-0000-000000000001')
AL2 = U('aaaaaaaa-0000-0000-0000-000000000002')
AL3 = U('aaaaaaaa-0000-0000-0000-000000000003')
PR1 = U('bbbbbbbb-0000-0000-0000-000000000001')
PR2 = U('bbbbbbbb-0000-0000-0000-000000000002')
PR3 = U('bbbbbbbb-0000-0000-0000-000000000003')
PR4 = U('bbbbbbbb-0000-0000-0000-000000000004')
SV1 = U('cccccccc-0000-0000-0000-000000000001')
SV2 = U('cccccccc-0000-0000-0000-000000000002')
SV3 = U('cccccccc-0000-0000-0000-000000000003')
SV4 = U('cccccccc-0000-0000-0000-000000000004')

# Spheres
SPHERE_Q = """INSERT INTO logosphere.spheres
(sphere_id,name,description,meaning_graph,location,admin1,created_at,
 participants,alliances,projects,values) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
session.execute(SPHERE_Q, (SP1,'Riverside Commons',
  'A solarpunk neighbourhood where tools, time and skills are shared freely. We grow food, repair what breaks, and look after one another — no money changes hands, only trust.',
  '#mutualaid #repair #gardens #localfirst','Riverside',JOE,T('2026-01-12 09:00:00'),
  [JOE,MARIE,STEVE,DAVID,EMMA],
  ['Repair Café Collective','Seed Keepers Alliance'],
  ['Community Tool Library','Neighbourhood Solar Microgrid'],
  ['mutual aid','repair culture','food sovereignty','trust']))
session.execute(SPHERE_Q, (SP2,'AI Commons',
  'A sphere pooling open compute and knowledge so that powerful AI research is a public good, not a private moat. Members share GPUs, datasets and mentorship in the spirit of the gift.',
  '#opencompute #knowledgecommons #ai','Distributed',ELON,T('2026-02-03 12:00:00'),
  [ELON,BILL,STEPHEN,JOE],
  ['Open Compute Guild'],['Open GPU Cluster'],
  ['open source','knowledge sharing','compute as commons']))
session.execute(SPHERE_Q, (SP3,'Earthsong Gardens',
  'A regenerative growing community restoring soil and pollinators. We swap heirloom seeds, share harvests, and govern the land together through liquid democracy.',
  '#regenerative #seeds #pollinators #biodiversity','Greenvale',DAVID,T('2026-03-21 08:00:00'),
  [DAVID,EMMA,MARIE],
  ['Seed Keepers Alliance'],['Pollinator Corridor'],
  ['regeneration','biodiversity','stewardship']))
print("[OK] Seeded 3 spheres")

# Alliances
ALLIANCE_Q = """INSERT INTO logosphere.alliances
(alliance_id,name,description,admin1,sphere_id,sphere_name,created_at,
 members,member_names,projects,values,meaning_graph) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
session.execute(ALLIANCE_Q, (AL1,'Repair Café Collective',
  'Neighbours who fix things together every Saturday — bikes, toasters, fences, friendships. Knowledge is shared, never sold.',
  STEVE,SP1,'Riverside Commons',T('2026-01-20 10:00:00'),
  [STEVE,JOE,MARIE],['Steve Wozniak','Joe Rogan','Marie Kondo'],
  ['Community Tool Library'],['repair culture','skill sharing'],'#repair #skillshare'))
session.execute(ALLIANCE_Q, (AL2,'Open Compute Guild',
  'Stewards of the shared GPU cluster. We allocate compute by need and contribution, decided by the members themselves.',
  BILL,SP2,'AI Commons',T('2026-02-10 14:00:00'),
  [BILL,ELON,STEPHEN],['Bill Gates','Elon Musk','Stephen Hawking'],
  ['Open GPU Cluster'],['open compute','fair allocation'],'#compute #governance'))
session.execute(ALLIANCE_Q, (AL3,'Seed Keepers Alliance',
  'Guardians of heirloom seed diversity. Members save, label and swap seeds so no variety is lost.',
  EMMA,SP3,'Earthsong Gardens',T('2026-03-25 09:30:00'),
  [EMMA,DAVID],['Emma Watson','David Attenborough'],
  ['Pollinator Corridor'],['seed sovereignty','biodiversity'],'#seeds #biodiversity'))
print("[OK] Seeded 3 alliances")

# Projects
PROJECT_Q = """INSERT INTO logosphere.projects
(project_id,name,description,owner,owner_alliance,status,sphere_id,sphere_name,
 created_at,participants,participant_names,values) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
session.execute(PROJECT_Q, (PR1,'Community Tool Library',
  'A free lending library of power tools, garden equipment and know-how. Borrow what you need, return it cared-for, teach the next person.',
  'Steve Wozniak','Repair Café Collective','In Progress',SP1,'Riverside Commons',T('2026-02-01 10:00:00'),
  [STEVE,JOE,MARIE],['Steve Wozniak','Joe Rogan','Marie Kondo'],
  ['sharing over owning','repair culture']))
session.execute(PROJECT_Q, (PR2,'Neighbourhood Solar Microgrid',
  'Rooftop panels feeding a shared battery so the block keeps the lights on together. Surplus energy is gifted to households that need it most.',
  'Joe Rogan','Repair Café Collective','Initiated',SP1,'Riverside Commons',T('2026-04-05 11:00:00'),
  [JOE,STEVE],['Joe Rogan','Steve Wozniak'],['energy as commons','resilience']))
session.execute(PROJECT_Q, (PR3,'Open GPU Cluster',
  'A community-run cluster of donated GPUs for open AI research. Time is allocated by the Open Compute Guild through transparent, member-led voting.',
  'Elon Musk','Open Compute Guild','In Progress',SP2,'AI Commons',T('2026-02-15 13:00:00'),
  [ELON,BILL,JOE],['Elon Musk','Bill Gates','Joe Rogan'],['open research','compute commons']))
session.execute(PROJECT_Q, (PR4,'Pollinator Corridor',
  'A ribbon of wildflower meadows linking gardens across the valley so bees and butterflies can travel safely. Planted and tended by volunteers.',
  'David Attenborough','Seed Keepers Alliance','Completed',SP3,'Earthsong Gardens',T('2026-03-28 08:30:00'),
  [DAVID,EMMA],['David Attenborough','Emma Watson'],['biodiversity','stewardship']))
print("[OK] Seeded 4 projects")

# Services / Openings  (now includes cadence)
SERVICE_Q = """INSERT INTO logosphere.services
(service_id,type,title,description,provider_id,provider_name,sphere_id,sphere_name,
 status,created_at,values,cadence) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
session.execute(SERVICE_Q, (SV1,'offer','Free podcasting & audio workshop',
  'I will teach anyone who is curious how to record, edit and publish a podcast. Bring your story; the gear is provided.',
  JOE,'Joe Rogan',SP1,'Riverside Commons','Posted',T('2026-06-20 10:00:00'),
  ['skill sharing','storytelling'],'perpetual'))
session.execute(SERVICE_Q, (SV2,'need','Hands needed for Saturday fence rebuild',
  'The community garden fence came down in the storm. Looking for a few neighbours to help rebuild it this Saturday — lunch is on the garden.',
  MARIE,'Marie Kondo',SP1,'Riverside Commons','Open',T('2026-06-22 08:00:00'),
  ['mutual aid','gardens'],'single'))
session.execute(SERVICE_Q, (SV3,'offer','7x H100 GPUs for open research',
  'Donating time on seven H100 GPUs to any open, non-commercial AI project. Allocated through the Open Compute Guild.',
  ELON,'Elon Musk',SP2,'AI Commons','Posted',T('2026-06-18 15:00:00'),
  ['open compute','generosity'],'perpetual'))
session.execute(SERVICE_Q, (SV4,'offer','Heirloom seeds to share',
  "Tomato, bean and squash seeds saved from this year's harvest. Take what you will grow; bring some back next season.",
  EMMA,'Emma Watson',SP3,'Earthsong Gardens','Posted',T('2026-06-15 09:00:00'),
  ['seed sovereignty','generosity'],'perpetual'))
print("[OK] Seeded 4 openings (with cadence)")

# Meaning Trail — Joe Rogan's 5 exchanges
XC = [U(f'10000000-0000-0000-0000-00000000000{i}') for i in range(1, 6)]

session.execute("""INSERT INTO logosphere.meaning_trail
(user_id,exchange_id,other_user_id,other_user_name,exchange_description,exchange_status,
 project_id,project_name,project_start_timestamp,
 gratitude_comment,gratitude_comment_id,gratitude_comment_timestamp,
 other_comment,other_comment_author_id,other_comment_author_name,other_comment_id,other_comment_timestamp)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
(JOE,XC[0],MARIE,'Marie Kondo',
 'Rebuilt the community garden fence after the spring storm','Receipted',
 PR1,'Community Tool Library',T('2026-05-02 09:00:00'),
 'Joe showed up at dawn with his own tools and stayed until every post was solid. The garden is safe again because of him.',
 U('20000000-0000-0000-0000-000000000001'),T('2026-05-04 18:00:00'),
 'Could not have done this without Marie organising the whole crew. True community spirit.',
 MARIE,'Marie Kondo',U('30000000-0000-0000-0000-000000000001'),T('2026-05-04 19:00:00')))

session.execute("""INSERT INTO logosphere.meaning_trail
(user_id,exchange_id,other_user_id,other_user_name,exchange_description,exchange_status,
 project_id,project_name,project_start_timestamp,
 gratitude_comment,gratitude_comment_id,gratitude_comment_timestamp)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
(JOE,XC[1],ELON,'Elon Musk',
 'Offered 7 H100 GPUs to the Open GPU Cluster for open research','In Progress',
 PR3,'Open GPU Cluster',T('2026-06-01 12:00:00'),
 'Joe pledged serious compute to the commons, no strings attached. This unblocks three research teams.',
 U('20000000-0000-0000-0000-000000000002'),T('2026-06-02 10:00:00')))

session.execute("""INSERT INTO logosphere.meaning_trail
(user_id,exchange_id,other_user_id,other_user_name,exchange_description,exchange_status,
 project_name,project_start_timestamp,
 other_comment,other_comment_author_id,other_comment_author_name,other_comment_id,other_comment_timestamp)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
(JOE,XC[2],EMMA,'Emma Watson',
 'Ran a free podcasting & audio workshop at Riverside Commons','Finished',
 'Skill Share',T('2026-06-10 17:00:00'),
 'I came in knowing nothing and left having recorded my first episode. Joe gives his time so generously.',
 EMMA,'Emma Watson',U('30000000-0000-0000-0000-000000000003'),T('2026-06-12 20:00:00')))

session.execute("""INSERT INTO logosphere.meaning_trail
(user_id,exchange_id,other_user_id,other_user_name,exchange_description,exchange_status,
 project_id,project_name,project_start_timestamp,
 user_comment,user_comment_id,user_comment_timestamp)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
(JOE,XC[3],STEVE,'Steve Wozniak',
 'Learned joinery and tool restoration from Steve at the Repair Café','Finished',
 PR1,'Community Tool Library',T('2026-04-18 10:00:00'),
 'Steve is endlessly patient. He taught me to sharpen a plane and to value fixing over buying. Paying it forward next week.',
 U('40000000-0000-0000-0000-000000000004'),T('2026-04-25 16:00:00')))

session.execute("""INSERT INTO logosphere.meaning_trail
(user_id,exchange_id,other_user_id,other_user_name,exchange_description,exchange_status,
 project_id,project_name,project_start_timestamp)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
(JOE,XC[4],STEVE,'Steve Wozniak',
 'Kicked off the Neighbourhood Solar Microgrid — mapping rooftops this month','Initiated',
 PR2,'Neighbourhood Solar Microgrid',T('2026-06-24 09:00:00')))

print("[OK] Seeded 5 meaning trail entries for Joe Rogan")

# ── Step 6: Value cards for Joe Rogan ─────────────────────────────────────────
VC_Q = """INSERT INTO logosphere.value_cards
(user_id,card_id,title,care_about,because,looks_like,
 drift_looks_like,in_conflict,never_do,frankl_mode,color_key,created_at)
VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""

try:
    session.execute("CREATE TABLE IF NOT EXISTS logosphere.value_cards (user_id uuid, card_id uuid, title text, care_about text, because text, looks_like list<text>, drift_looks_like text, in_conflict text, never_do text, frankl_mode text, color_key text, created_at timestamp, PRIMARY KEY (user_id, card_id)) WITH CLUSTERING ORDER BY (card_id ASC)")
    print("[OK] value_cards table ready")
except Exception as e:
    print(f"[WARN] value_cards table: {e}")

# Clear existing Joe + Elon cards
for uid, name in [(JOE, 'Joe Rogan'), (ELON, 'Elon Musk')]:
    existing = list(session.execute("SELECT card_id FROM logosphere.value_cards WHERE user_id = %s", [uid]))
    for row in existing:
        session.execute("DELETE FROM logosphere.value_cards WHERE user_id = %s AND card_id = %s", [uid, row.card_id])
    print(f"  cleared {len(existing)} existing cards for {name}")

joe_cards = [
    ('Conversations that change minds',
     'Long-form dialogue that takes ideas seriously — the kind where both people walk away different.',
     'Most public discourse is performative. Real thinking happens in the space where no one is playing to an audience.',
     ['Sitting with a guest for 3+ hours without cutting to a break',
      'Letting an idea develop fully before pushing back',
      "Saying 'I don't know' when I genuinely don't"],
     'Booking guests for their audience not their ideas. Cutting off a thread because it\'s getting uncomfortable.',
     'The quality of the conversation over the size of the audience.',
     'Fake agreement to avoid conflict.',
     'creative','honey'),
    ('Physical presence as a practice',
     'The discipline of keeping the body trained — martial arts, hunting, fitness — not for aesthetics but for clarity.',
     'A sharp body makes a sharp mind. Comfort is entropy. The people I respect most take their physical practice seriously.',
     ['Training jiu-jitsu at least 4 days a week regardless of schedule',
      'Taking a hunt seriously as a multi-day commitment',
      'Treating sleep and nutrition as inputs, not luxuries'],
     "Skipping training because the podcast got busy. Using 'I deserve rest' as a cover for avoidance.",
     'The training over the convenience.',
     'Shame someone for where they are in their physical journey.',
     'attitudinal','terracotta'),
    ('Genuine curiosity across the spectrum',
     'Finding what\'s actually interesting in every kind of person — the scientist, the comedian, the fighter, the philosopher.',
     'Everyone has a world inside them that most people never ask about. Most interviewers ask questions they already know the answer to.',
     ["Researching a guest's work before the interview even if it's outside my comfort zone",
      'Following a rabbit hole on air when something surprises me',
      'Having guests I fundamentally disagree with and treating their ideas fairly'],
     'Only booking people I already like. Staying on safe topics because controversy is exhausting.',
     'The unexpected insight over the comfortable brand.',
     "Pretend to understand something I haven't thought about.",
     'experiential','leaf'),
]

for c in joe_cards:
    session.execute(VC_Q, (JOE, uuid.uuid4()) + c + (datetime.utcnow(),))
print(f"[OK] Seeded {len(joe_cards)} value cards for Joe Rogan")

elon_cards = [
    ('Making humanity multi-planetary',
     'Ensuring the long-term survival of consciousness by making life multiplanetary before an extinction event wipes out everything we\'ve built.',
     'All civilisations that have ever existed are gone. Earth is the only backup. A single-planet species is an unacceptable risk over geological timescales.',
     ['Setting reusable rocket timelines that most engineers call impossible',
      'Treating Mars colonisation as an engineering problem, not a dream',
      'Funding SpaceX personally when it was weeks from bankruptcy'],
     'Treating space as a prestige project rather than a survival imperative. Optimising for quarterly revenue over a 10-year mission.',
     'The mission over the optics.',
     'Accept that something is impossible without doing the physics.',
     'creative','terracotta'),
    ('Accelerating the energy transition',
     'Moving civilisation off fossil fuels as fast as physically possible — not out of environmentalism but because sustainable energy is simply the correct long-term path.',
     'The atmosphere is a finite buffer. Every year of delay locks in compounding consequences. The technology exists; the bottleneck is manufacturing scale and political inertia.',
     ['Building the world\'s largest battery factories before there was demand',
      'Treating the energy problem as a manufacturing problem first',
      "Publishing Tesla's patents openly to accelerate the entire industry"],
     'Treating sustainability as a marketing angle. Optimising vehicle range for luxury buyers over energy density for affordability.',
     'Speed of transition over profit margin on any single product.',
     'Pretend that incremental improvement is enough.',
     'attitudinal','leaf'),
    ('Free flow of information',
     'The ability of any person to say what they actually think without institutional gatekeeping deciding what is and isn\'t permitted discourse.',
     'Centralised control of speech has historically been the first tool of authoritarians. An open forum — even a messy one — is preferable to a curated one.',
     ['Reinstating accounts banned for political speech rather than illegal activity',
      'Publishing moderation decisions and algorithms rather than hiding them',
      'Tolerating criticism of myself on the platform I own'],
     "Permitting any speech I personally agree with while suppressing speech I find inconvenient. Treating 'free speech' as a brand rather than a practice.",
     'The open forum over advertiser comfort.',
     'Silence someone for saying something true that I find uncomfortable.',
     'experiential','honey'),
]

for c in elon_cards:
    session.execute(VC_Q, (ELON, uuid.uuid4()) + c + (datetime.utcnow(),))
print(f"[OK] Seeded {len(elon_cards)} value cards for Elon Musk")

cluster.shutdown()
print("\n[DONE] Reseed complete — all schema changes applied, demo data fresh.")
