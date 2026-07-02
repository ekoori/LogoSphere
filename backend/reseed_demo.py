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
for tbl in ['meaning_trail', 'comment_likes', 'likes', 'opening_likes',
            'opening_acceptances', 'audit_log']:
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
    gratitude_comment_cards text,
    user_comment_cards text,
    other_comment_cards text,
    initiator_comment text,
    initiator_comment_timestamp timestamp,
    recipient_comment text,
    recipient_comment_timestamp timestamp,
    PRIMARY KEY (user_id, exchange_id)
) WITH CLUSTERING ORDER BY (exchange_id DESC)
""")
print("[OK] Created meaning_trail (exchange_* columns)")

run("""
CREATE TABLE logosphere.likes (
    exchange_id uuid,
    comment_type text,
    user_id uuid,
    PRIMARY KEY ((exchange_id, comment_type), user_id)
) WITH CLUSTERING ORDER BY (user_id ASC)
""")
print("[OK] Created likes (per-user rows; count = COUNT(*) per partition)")

run("""
CREATE TABLE logosphere.opening_likes (
    service_id uuid,
    user_id uuid,
    PRIMARY KEY (service_id, user_id)
) WITH CLUSTERING ORDER BY (user_id ASC)
""")
print("[OK] Created opening_likes (per-user rows for openings)")

run("""
CREATE TABLE logosphere.opening_acceptances (
    service_id uuid,
    accepter_id uuid,
    accepter_name text,
    status text,
    exchange_id uuid,
    created_at timestamp,
    PRIMARY KEY (service_id, accepter_id)
) WITH CLUSTERING ORDER BY (accepter_id ASC)
""")
print("[OK] Created opening_acceptances (pending/confirmed acceptances)")

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
  '#opencompute #knowledgecommons #ai','Distributed',JOE,T('2026-02-03 12:00:00'),
  [ELON,BILL,STEPHEN,JOE],
  ['Open Compute Guild'],['Open GPU Cluster'],
  ['open source','knowledge sharing','compute as commons']))
session.execute(SPHERE_Q, (SP3,'Earthsong Gardens',
  'A regenerative growing community restoring soil and pollinators. We swap heirloom seeds, share harvests, and govern the land together through liquid democracy.',
  '#regenerative #seeds #pollinators #biodiversity','Greenvale',JOE,T('2026-03-21 08:00:00'),
  [DAVID,EMMA,MARIE,JOE],
  ['Seed Keepers Alliance'],['Pollinator Corridor'],
  ['regeneration','biodiversity','stewardship']))
print("[NOTE] Joe Rogan is admin1 of all 3 spheres")
print("[OK] Seeded 3 spheres")

# Alliances — member_roles is set explicitly so governance (and the value-graph
# management permissions) are deterministic. admin1 is 'admin'; one steward each.
ALLIANCE_Q = """INSERT INTO logosphere.alliances
(alliance_id,name,description,admin1,sphere_id,sphere_name,created_at,
 members,member_names,projects,values,meaning_graph,member_roles)
 VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
session.execute(ALLIANCE_Q, (AL1,'Repair Café Collective',
  'Neighbours who fix things together every Saturday — bikes, toasters, fences, friendships. Knowledge is shared, never sold.',
  STEVE,SP1,'Riverside Commons',T('2026-01-20 10:00:00'),
  [STEVE,JOE,MARIE],['Steve Wozniak','Joe Rogan','Marie Kondo'],
  ['Community Tool Library'],['repair culture','skill sharing'],'#repair #skillshare',
  {STEVE:'admin', MARIE:'steward', JOE:'member'}))
session.execute(ALLIANCE_Q, (AL2,'Open Compute Guild',
  'Stewards of the shared GPU cluster. We allocate compute by need and contribution, decided by the members themselves.',
  BILL,SP2,'AI Commons',T('2026-02-10 14:00:00'),
  [BILL,ELON,STEPHEN],['Bill Gates','Elon Musk','Stephen Hawking'],
  ['Open GPU Cluster'],['open compute','fair allocation'],'#compute #governance',
  {BILL:'admin', ELON:'steward', STEPHEN:'member'}))
session.execute(ALLIANCE_Q, (AL3,'Seed Keepers Alliance',
  'Guardians of heirloom seed diversity. Members save, label and swap seeds so no variety is lost.',
  EMMA,SP3,'Earthsong Gardens',T('2026-03-25 09:30:00'),
  [EMMA,DAVID],['Emma Watson','David Attenborough'],
  ['Pollinator Corridor'],['seed sovereignty','biodiversity'],'#seeds #biodiversity',
  {EMMA:'admin', DAVID:'steward'}))
print("[OK] Seeded 3 alliances (with member_roles)")

# Projects — participant_roles makes the project's named owner an actual
# 'manager' (everyone else defaults to 'contributor'), so the "post an opening
# as this project" management flow has someone to demo it with.
PROJECT_Q = """INSERT INTO logosphere.projects
(project_id,name,description,owner,owner_alliance,status,sphere_id,sphere_name,
 created_at,participants,participant_names,values,participant_roles) VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)"""
session.execute(PROJECT_Q, (PR1,'Community Tool Library',
  'A free lending library of power tools, garden equipment and know-how. Borrow what you need, return it cared-for, teach the next person.',
  'Steve Wozniak','Repair Café Collective','In Progress',SP1,'Riverside Commons',T('2026-02-01 10:00:00'),
  [STEVE,JOE,MARIE],['Steve Wozniak','Joe Rogan','Marie Kondo'],
  ['sharing over owning','repair culture'], {STEVE:'manager'}))
session.execute(PROJECT_Q, (PR2,'Neighbourhood Solar Microgrid',
  'Rooftop panels feeding a shared battery so the block keeps the lights on together. Surplus energy is gifted to households that need it most.',
  'Joe Rogan','Repair Café Collective','Initiated',SP1,'Riverside Commons',T('2026-04-05 11:00:00'),
  [JOE,STEVE],['Joe Rogan','Steve Wozniak'],['energy as commons','resilience'], {JOE:'manager'}))
session.execute(PROJECT_Q, (PR3,'Open GPU Cluster',
  'A community-run cluster of donated GPUs for open AI research. Time is allocated by the Open Compute Guild through transparent, member-led voting.',
  'Elon Musk','Open Compute Guild','In Progress',SP2,'AI Commons',T('2026-02-15 13:00:00'),
  [ELON,BILL,JOE],['Elon Musk','Bill Gates','Joe Rogan'],['open research','compute commons'], {ELON:'manager'}))
session.execute(PROJECT_Q, (PR4,'Pollinator Corridor',
  'A ribbon of wildflower meadows linking gardens across the valley so bees and butterflies can travel safely. Planted and tended by volunteers.',
  'David Attenborough','Seed Keepers Alliance','Completed',SP3,'Earthsong Gardens',T('2026-03-28 08:30:00'),
  [DAVID,EMMA],['David Attenborough','Emma Watson'],['biodiversity','stewardship'], {DAVID:'manager'}))
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

# Clear existing cards for all users and entities
for uid, name in [
    (JOE, 'Joe Rogan'), (ELON, 'Elon Musk'),
    (MARIE, 'Marie Kondo'), (STEVE, 'Steve Wozniak'),
    (DAVID, 'David Attenborough'), (EMMA, 'Emma Watson'),
    (BILL, 'Bill Gates'), (STEPHEN, 'Stephen Hawking'),
    (SP1, 'Riverside Commons'), (SP2, 'AI Commons'), (SP3, 'Earthsong Gardens'),
    (AL1, 'Repair Café Collective'), (AL2, 'Open Compute Guild'), (AL3, 'Seed Keepers Alliance'),
    (PR1, 'Community Tool Library'), (PR2, 'Neighbourhood Solar Microgrid'),
    (PR3, 'Open GPU Cluster'), (PR4, 'Pollinator Corridor'),
]:
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

# ── Step 7: Value cards for remaining users ────────────────────────────────────
marie_cards = [
    ('Intentional space',
     'Keeping only what genuinely serves the people who live or work here — and releasing everything else with gratitude.',
     'Accumulated objects carry the weight of obligation. When we clear that weight, energy moves again.',
     ['Handling every item before deciding its fate',
      'Asking "does this serve us now?" not "might we need this someday?"',
      'Thanking things before releasing them — even tools and furniture'],
     'Tidying as performance rather than practice. Reducing clutter in one area while creating it in another.',
     'The feeling of the space over the opinion of others about how much to keep.',
     'Shame someone for what they own or how they live.',
     'attitudinal', 'honey'),
    ('Systems that sustain themselves',
     'Building habits and structures so that order is the natural state, not something that must be constantly imposed.',
     'Willpower is finite. The goal is an environment where the right thing is also the easy thing.',
     ['Designing a home where every object has a designated place',
      'Teaching the system to others so they can maintain it without help',
      'Starting with category, not room — seeing everything at once'],
     'Creating rules nobody will follow. Organising other people\'s things without their buy-in.',
     'The long-term system over the short-term tidy.',
     'Impose order that doesn\'t belong to the people living with it.',
     'creative', 'leaf'),
]

steve_cards = [
    ('Engineering as play',
     'Approaching problems with a hacker\'s joy — the delight of making something work, elegantly, with whatever is at hand.',
     'The best engineering I ever did came from curiosity, not deadline. The calculator I built in a garage was play first, product second.',
     ['Prototyping before specifying',
      'Sharing designs and schematics openly so others can build on them',
      'Finding the simplest circuit that could possibly work'],
     'Optimising for impressive over elegant. Engineering that nobody can understand, let alone fix.',
     'The elegant solution over the fast one.',
     'Patent an idea that should belong to everyone.',
     'creative', 'honey'),
    ('Technology as a gift',
     'Making computing accessible to ordinary people — not just engineers — as a democratic act.',
     'The personal computer was supposed to be for everyone. That is still the point.',
     ['Writing documentation that a non-engineer can follow',
      'Teaching skills rather than selling products',
      'Contributing to open-source projects without expecting recognition'],
     'Hiding complexity to appear magical. Technology that creates dependency instead of capability.',
     'The user\'s understanding over our convenience.',
     'Make someone feel stupid for not knowing something.',
     'experiential', 'terracotta'),
]

david_cards = [
    ('Wonder as responsibility',
     'Seeing the natural world with eyes that notice what is extraordinary about the ordinary — and communicating that wonder so others act to protect it.',
     'People protect what they love. They love what they have truly seen. Most have never truly looked.',
     ['Spending time observing before explaining',
      'Finding the unexpected angle — the shot that nobody has seen before',
      'Telling hard truths about decline without abandoning hope'],
     'Catastrophising without agency. Presenting the beauty without the urgency.',
     'The story that moves people over the one that merely informs them.',
     'Pretend things are fine when they are not.',
     'experiential', 'leaf'),
    ('Every species has a role',
     'Acting from the understanding that biodiversity is not optional richness — it is the structure that keeps everything else standing.',
     'We share this planet with eight million other species. We have yet to understand most of them. To lose them before we do is to burn a library.',
     ['Advocating for habitats not just charismatic megafauna',
      'Connecting what happens to insects to what happens to our food',
      'Speaking about invertebrates with the same reverence as apex predators'],
     'Ranking species by their usefulness to humans. Conservation that saves the tiger but ignores the soil.',
     'The ecosystem over any single species, including ours.',
     'Dismiss any creature as insignificant.',
     'attitudinal', 'moss'),
]

emma_cards = [
    ('Education as liberation',
     'Every person\'s access to knowledge, literature and critical thought — not as a privilege but as a precondition of a free life.',
     'What is kept from people is always revealing. The subjects that powerful institutions most resist teaching are usually the ones most worth learning.',
     ['Reading widely outside familiar perspectives',
      'Supporting initiatives that put books and learning in places without them',
      'Using platforms to amplify voices that aren\'t usually heard there'],
     'Education as credential accumulation. Learning systems that sort people rather than open them.',
     'Access over prestige.',
     'Gatekeep knowledge based on who someone is.',
     'creative', 'honey'),
    ('Accountability without performance',
     'Doing the work — showing up, changing behaviour, listening — rather than performing allyship for an audience.',
     'The gap between what people say and what they do is where change goes to die. I include myself in this.',
     ['Admitting when I got something wrong without defending the mistake',
      'Doing the reading rather than asking marginalised people to educate me',
      'Taking on less visible work rather than gravitating toward the public gesture'],
     'Activism as brand. Turning every commitment into content before doing the actual thing.',
     'The changed behaviour over the well-written apology.',
     'Claim credit for work done by the people I was supposedly helping.',
     'attitudinal', 'terracotta'),
]

bill_cards = [
    ('Leverage at scale',
     'Targeting the interventions that create the most impact per resource — ignoring problems because they are hard is not acceptable when the tools to solve them exist.',
     'Most philanthropic giving flows to institutions that already have resources. The biggest gains come from problems that markets ignore because the people suffering cannot pay.',
     ['Funding vaccine distribution in places with no commercial incentive to invest',
      'Applying the same rigour to giving that built the resources to give',
      'Publishing what worked and what didn\'t so others don\'t repeat failures'],
     'Treating charity as reputation management. Giving where it feels good rather than where it does most.',
     'Impact per dollar over visibility per dollar.',
     'Withhold failure data that would help others learn.',
     'attitudinal', 'leaf'),
    ('Open knowledge compounds',
     'Sharing research, tools and methods freely so every generation doesn\'t have to rediscover what the last one knew.',
     'The polio vaccine was not patented. Every child alive today who has never had polio inherited that decision.',
     ['Co-funding open publication of research we support',
      'Contributing to global health databases regardless of competitive advantage',
      'Citing and crediting prior work that made our work possible'],
     'Open-washing — publishing summaries but keeping the data proprietary.',
     'The cumulative gain over the individual competitive edge.',
     'Claim ownership of knowledge that was built on public foundations.',
     'creative', 'sage'),
]

stephen_cards = [
    ('Curiosity as survival',
     'The drive to understand — even when the question seems unanswerable, even when the answer changes everything — as the highest human act.',
     'We are just an advanced breed of monkeys on a minor planet orbiting a very average star. But we can understand the universe. That makes us extraordinary.',
     ['Sitting with a question long enough that it becomes a different question',
      'Changing my position when the evidence changes, publicly and without embarrassment',
      'Taking seriously ideas that seem absurd on first contact'],
     'Treating certainty as a destination. Making a home in a theory rather than continuing to test it.',
     'The question that unsettles everything over the answer that settles nothing.',
     'Dismiss an idea because of the status of the person who proposed it.',
     'experiential', 'honey'),
    ('Knowledge without barriers',
     'Making science and ideas accessible to people who were never supposed to have access to them.',
     'I could not hold a pen or speak in the last decades of my life. Accessibility was not an abstraction. It was the difference between contributing and disappearing.',
     ['Writing for a curious teenager, not a journal reviewer',
      'Treating the public lecture as seriously as the academic paper',
      'Advocating for tools that let people with disabilities do science'],
     'Science that speaks only to scientists. Knowledge locked behind jargon and paywalls.',
     'The person who understood it over the one who already knew it.',
     'Make someone feel unwelcome in a scientific conversation.',
     'creative', 'terracotta'),
]

for name, uid, cards in [
    ('Marie Kondo', MARIE, marie_cards),
    ('Steve Wozniak', STEVE, steve_cards),
    ('David Attenborough', DAVID, david_cards),
    ('Emma Watson', EMMA, emma_cards),
    ('Bill Gates', BILL, bill_cards),
    ('Stephen Hawking', STEPHEN, stephen_cards),
]:
    for c in cards:
        session.execute(VC_Q, (uid, uuid.uuid4()) + c + (datetime.utcnow(),))
    print(f"[OK] Seeded {len(cards)} value cards for {name}")

# ── Step 8: Value cards for spheres ───────────────────────────────────────────
sphere_cards = {
    SP1: [  # Riverside Commons
        ('Nothing wasted, everything shared',
         'Making the default assumption that what one household doesn\'t need, another does — and building the infrastructure for that exchange.',
         'Every skip full of usable things is a failure of connection between neighbours. We have more than enough; we have not yet learned to circulate it.',
         ['Posting what you\'re done with before buying new',
          'Borrowing before purchasing for any task that comes up fewer than ten times a year',
          'Fixing the broken thing before the new one arrives'],
         'Hoarding under the name of "preparedness". Sharing only the things nobody would want anyway.',
         'The collective sufficiency over the individual stockpile.',
         'Discard something that a neighbour could use.',
         'attitudinal', 'moss'),
        ('Soil and food as commons',
         'Treating the capacity to grow food as a shared infrastructure — not a lifestyle hobby but a serious community foundation.',
         'The supermarket is three supply-chain disruptions away from empty shelves. Knowing how to grow is knowing how to survive.',
         ['Maintaining at least one communal bed per street',
          'Sharing surplus harvest through the common drop-off rather than letting it rot',
          'Teaching children to grow before they learn to buy'],
         'Community gardens that only the already-confident use. "Local food" as a premium product rather than a shared right.',
         'The person who has never grown anything over the one who knows how.',
         'Let knowledge about growing stay locked in one generation.',
         'creative', 'leaf'),
    ],
    SP2: [  # AI Commons
        ('Compute as public infrastructure',
         'Treating access to AI processing power the way we treat roads and water — something managed for collective benefit, not private advantage.',
         'The most powerful AI systems will shape the century. If only a handful of companies control the compute, they control the future. That is not acceptable.',
         ['Allocating GPU time by research value, not ability to pay',
          'Publishing utilisation data so the community can hold allocators accountable',
          'Rejecting uses that would close rather than open knowledge'],
         'Open compute that serves open-washing — free access for friendly researchers, closed for anyone who might compete.',
         'The researcher with the best question over the one with the biggest budget.',
         'Accept a use that benefits one member at the cost of the commons.',
         'attitudinal', 'honey'),
        ('AI research as a gift to humanity',
         'Conducting and sharing research in AI not for competitive advantage but because the knowledge belongs to everyone.',
         'Every major AI breakthrough built on decades of public funding and publicly shared research. Privatising the next layer is theft from the commons.',
         ['Publishing findings before seeking commercial applications',
          'Refusing research that cannot be published',
          'Actively citing and compensating the open-source work we build on'],
         'Research published just enough to appear open while keeping the important bits proprietary.',
         'The open result over the closed product.',
         'Build on someone\'s open work without acknowledging it.',
         'creative', 'leaf'),
    ],
    SP3: [  # Earthsong Gardens
        ('Soil health as the foundation of everything',
         'Treating the living complexity of healthy soil as the most valuable asset a community can steward — more important than any yield it produces.',
         'Industrial agriculture has depleted topsoil that took ten thousand years to build in a few decades. We are the generation that either reverses this or doesn\'t.',
         ['Testing soil before adding anything to it',
          'Composting all organic waste back into the beds',
          'Leaving roots in the ground to feed the fungal web rather than pulling them'],
         'Optimising for visible yield at the cost of invisible soil health. Treating compost as a chore rather than a practice.',
         'The soil community over this season\'s harvest.',
         'Add a chemical to the soil without understanding what it does to the organisms in it.',
         'attitudinal', 'moss'),
        ('Wild and cultivated in conversation',
         'Designing growing spaces where the cultivated and the wild support each other — not a garden that holds nature at bay but one that invites it in.',
         'A monoculture requires constant defence. A diverse system defends itself. The garden that thrives with least intervention is the garden that works with nature, not against it.',
         ['Leaving areas deliberately unmown and uncultivated',
          'Choosing companion planting over pesticides',
          'Planting for pollinators and birds as deliberately as planting for the table'],
         'Aesthetics that eliminate wildness. Neatness as a value that crowds out biodiversity.',
         'The insect over the weed-free path.',
         'Remove a plant without first asking what depends on it.',
         'creative', 'sage'),
    ],
}

for sid, cards in sphere_cards.items():
    sphere_name = {SP1: 'Riverside Commons', SP2: 'AI Commons', SP3: 'Earthsong Gardens'}[sid]
    for c in cards:
        session.execute(VC_Q, (sid, uuid.uuid4()) + c + (datetime.utcnow(),))
    print(f"[OK] Seeded {len(cards)} value cards for sphere: {sphere_name}")

# ── Step 9: Value cards for alliances ─────────────────────────────────────────
alliance_cards = {
    AL1: [  # Repair Café Collective
        ('Repair over replace',
         'Making the first response to any broken thing a serious attempt to fix it — and building the skills and tools to make that possible.',
         'Every object that gets repaired rather than replaced is a material extracted from the earth, a worker paid to make it, and a landfill site it never fills.',
         ['Bringing the broken thing to the café before looking for a replacement',
          'Documenting the repair so the next person can do it themselves',
          'Teaching repair skills explicitly, not just doing the repair for someone'],
         'Repair Café as a feel-good event where the same five people fix things for admiring spectators.',
         'The person who leaves knowing how over the person who leaves with a working thing.',
         'Fix something without explaining what was broken and why.',
         'creative', 'terracotta'),
        ('Knowledge belongs to whoever needs it',
         'Treating technical skill as something to give away, not hoard — the highest act of skill is creating the conditions where you are no longer needed.',
         'Expertise has been used as gatekeeping for too long. The person who teaches ten people to fix bikes has done more than the person who fixed a hundred.',
         ['Welcoming complete beginners and giving them the first tool to try',
          'Never making someone feel stupid for not knowing something technical',
          'Writing guides in plain language and leaving them where others will find them'],
         'Expert capture — repairs that only one person can do, creating permanent dependency.',
         'The learner over the efficiency of the fix.',
         'Take over a repair from someone who is learning, just because it\'s faster.',
         'experiential', 'honey'),
    ],
    AL2: [  # Open Compute Guild
        ('Transparent allocation',
         'Making every decision about who gets compute time visible, documented and contestable by any member.',
         'Centralised control of scarce resources without accountability always drifts toward serving the powerful. Transparency is not optional; it is the mechanism.',
         ['Publishing the allocation queue and the criteria in full',
          'Holding open monthly reviews where any member can challenge a decision',
          'Recording the reasoning behind each allocation, not just the outcome'],
         'Transparency theatre — publishing decisions after they are made without any genuine input mechanism.',
         'The documented process over the trusted judgment of any individual.',
         'Make an allocation decision in a private channel.',
         'attitudinal', 'honey'),
        ('Compute time by need and contribution',
         'Allocating the shared resource to those with the most valuable questions — not the most resources, the loudest voices, or the longest tenure.',
         'A commons that drifts toward rewarding the already-powerful is not a commons. The allocation method is the values made concrete.',
         ['Scoring proposals on research quality, not applicant reputation',
          'Weighting contribution history but never letting it dominate over question quality',
          'Maintaining a reserve for unfunded researchers with no existing track record'],
         'Allocation that consistently rewards the same institutions. A waiting list that only moves for people with connections.',
         'The first-time researcher with an excellent question over the repeat user with a mediocre one.',
         'Allow social relationships to influence allocation without documenting that they did.',
         'creative', 'leaf'),
    ],
    AL3: [  # Seed Keepers Alliance
        ('Every variety is irreplaceable',
         'Treating each seed variety as a unique living library — carrying adaptations, stories and potential that cannot be reconstructed once lost.',
         'The Irish potato famine killed a million people because one crop variety fed a nation. Biodiversity is not aesthetic richness; it is civilisational insurance.',
         ['Maintaining at least three independent copies of every variety in the network',
          'Growing-out rare varieties every three years so viability is tested and refreshed',
          'Recording the story and origin of every variety alongside the seeds themselves'],
         'Seed banks that store seeds nobody is growing. Diversity on paper rather than in the soil.',
         'The variety at risk of loss over the one already well-represented.',
         'Allow a variety to go below minimum viable population without raising the alarm.',
         'attitudinal', 'sage'),
        ('Traditional knowledge alongside the seed',
         'Keeping the accumulated understanding of how to grow each variety — what soil it loves, when it bolts, how it has been used — as inseparable from the seed itself.',
         'A seed without the knowledge of how to grow it is an archive without a reading room. The wisdom lives in growers, not databases, and it is equally at risk.',
         ['Recording grower interviews and stories alongside germination data',
          'Visiting elder growers to learn what hasn\'t been written down',
          'Returning seeds to communities of origin with the knowledge attached'],
         'Extracting seeds without reciprocity. Treating traditional knowledge as raw material for our records.',
         'The source community\'s access and agency over our archival completeness.',
         'Take seeds from a community without asking what they need in return.',
         'experiential', 'moss'),
    ],
}

for aid, cards in alliance_cards.items():
    alliance_name = {AL1: 'Repair Café Collective', AL2: 'Open Compute Guild', AL3: 'Seed Keepers Alliance'}[aid]
    for c in cards:
        session.execute(VC_Q, (aid, uuid.uuid4()) + c + (datetime.utcnow(),))
    print(f"[OK] Seeded {len(cards)} value cards for alliance: {alliance_name}")

# ── Step 10: Value cards for projects ─────────────────────────────────────────
project_cards = {
    PR1: [  # Community Tool Library
        ('Tools are for using, not owning',
         'Maintaining a shared library of tools so that no household needs to own equipment it uses a few times a year.',
         'The average drill is used for twelve minutes in its entire lifetime. Meanwhile the materials to make it were extracted, the worker who made it was paid, and a shelf holds it for decades. This is a solved problem.',
         ['Adding any tool used fewer than twice a year to the shared pool',
          'Tracking lending through the simplest possible system — a notebook is fine',
          'Teaching basic use as part of every loan'],
         'A tool library that fills with items nobody wants to borrow. Gatekeeping through complex lending rules.',
         'The neighbour who needs the tool next over the one who has it now.',
         'Refuse a loan because the borrower "might not know how to use it."',
         'creative', 'terracotta'),
        ('Care is part of the transaction',
         'Returning tools in better condition than they were borrowed — cleaned, sharpened, with what was used replaced.',
         'Common resources degrade unless everyone takes responsibility for them as if they were their own. The tool library works because every member acts as a steward, not just a user.',
         ['Cleaning and oiling before return, not after the next borrower complains',
          'Noting wear or damage on the return so it can be addressed',
          'Contributing one maintenance session per season to the collective stock'],
         'Returning things technically in one piece. Letting the collective absorb the cost of individual carelessness.',
         'The condition for the next borrower over the inconvenience of the current one.',
         'Return something without saying if it developed a problem during use.',
         'attitudinal', 'honey'),
    ],
    PR2: [  # Neighbourhood Solar Microgrid
        ('Energy resilience as mutual aid',
         'Building grid capacity so that the households most vulnerable to outages — elderly, medical equipment, young children — are the last to go dark.',
         'Energy is not a commodity in this grid; it is a form of care. The point of community infrastructure is to make the floor higher, not the ceiling.',
         ['Prioritising battery allocation to highest-need households in a shortage',
          'Designing the system so the most vulnerable are protected without having to ask',
          'Publishing real-time generation and allocation data for all members'],
         'Grid that distributes evenly regardless of need. Solar as a cost-saving measure that benefits those who can already afford panels.',
         'The household that would lose heat or refrigerated medication over average distribution.',
         'Design the system in a way that benefits contributors more than the most vulnerable.',
         'attitudinal', 'honey'),
        ('Surplus energy as a gift',
         'Routing any generation above collective needs to households experiencing hardship — not selling it back to the grid, giving it to neighbours.',
         'We built this together. The surplus belongs to whoever needs it most, not to whoever has the biggest array.',
         ['Establishing a "gift pool" for surplus rather than grid export by default',
          'Reviewing allocation quarterly with the whole grid community',
          'Making it easy to signal need without stigma'],
         'Treating surplus as a personal financial return. Exporting to the grid while a neighbour can\'t afford to heat their home.',
         'The neighbour in difficulty over our own credit balance.',
         'Sell surplus while a member is rationing their own use.',
         'creative', 'leaf'),
    ],
    PR3: [  # Open GPU Cluster
        ('Compute time for the best questions',
         'Allocating cluster resources to the research most likely to produce open, shareable knowledge — regardless of who is asking.',
         'The history of science is a history of outsiders with better questions being kept out by insiders with credentials. This cluster exists to make that less true.',
         ['Blind-reviewing proposals before learning who submitted them',
          'Actively recruiting researchers from institutions with no existing cluster access',
          'Refusing applications that would result in proprietary outputs'],
         'Cluster that serves the established because they already know how to apply. Open compute that produces closed papers.',
         'The proposal that will produce public knowledge over the one from the better-known lab.',
         'Award time to a project whose outputs will be locked behind a paywall.',
         'creative', 'honey'),
        ('Open by default, always',
         'Producing all research, code, datasets and models under open licences — this is not a preference but a condition of access.',
         'The cluster exists because of community contributions. The outputs belong to the community. This is not complicated.',
         ['Checking licence status before any result is published or deployed',
          'Actively depositing code and models to public repositories, not just making them "available on request"',
          'Refusing extensions for teams that haven\'t met open-release commitments from prior allocations'],
         'Technically open licences that make the work practically unusable. "Open access" papers with datasets that are not released.',
         'The community\'s access to the output over the researcher\'s comfort with sharing.',
         'Approve a renewal for a team that hasn\'t delivered on prior open commitments.',
         'attitudinal', 'leaf'),
    ],
    PR4: [  # Pollinator Corridor
        ('Continuity across boundaries',
         'Creating connected habitat so that pollinators can travel between areas without encountering lethal gaps — thinking in corridors, not patches.',
         'An isolated meadow helps the pollinators that can reach it. A connected corridor helps the whole landscape. The difference is not effort; it is coordination.',
         ['Mapping the corridor from the insect\'s perspective, not the land-owner\'s',
          'Negotiating right-of-way planting across property lines',
          'Measuring connectivity annually and targeting the gaps'],
         'Meadows that are local pride projects rather than linked habitat. Planting that maximises visible beauty over ecological function.',
         'The corridor gap over the patch that is already good.',
         'Plant a species that looks beautiful but provides nothing for pollinators.',
         'creative', 'sage'),
        ('Native plants as the baseline',
         'Treating native plant species as the default choice for all corridor planting — not because exotics are always wrong but because natives are always right.',
         'Millions of years of co-evolution produced insects that can extract nutrition from local plants and plants that need those insects to reproduce. That system is not improvable; it can only be disrupted or supported.',
         ['Sourcing all planting stock from native seed provenance',
          'Removing invasive exotics before adding new plantings',
          'Educating corridor landowners on the distinction between native and naturalised'],
         'Native plant sections next to exotic borders, cancelling each other\'s work. Rewilding with species that look wild but aren\'t local.',
         'The native plant that feeds the local insect over the exotic that looks more impressive.',
         'Plant an ornamental that will outcompete the natives around it.',
         'attitudinal', 'moss'),
    ],
}

for pid, cards in project_cards.items():
    project_name = {PR1: 'Community Tool Library', PR2: 'Neighbourhood Solar Microgrid',
                    PR3: 'Open GPU Cluster', PR4: 'Pollinator Corridor'}[pid]
    for c in cards:
        session.execute(VC_Q, (pid, uuid.uuid4()) + c + (datetime.utcnow(),))
    print(f"[OK] Seeded {len(cards)} value cards for project: {project_name}")

cluster.shutdown()
print("\n[DONE] Reseed complete — all schema changes applied, demo data fresh.")
