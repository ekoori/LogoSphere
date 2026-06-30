# Seed governance roles for alliances/projects, update Joe Rogan's roles,
# and seed entity value cards (spheres, alliances, projects all get value cards).

from gevent import monkey; monkey.patch_all()
import os, sys, uuid
from datetime import datetime

os.environ.setdefault('CASSANDRA_HOST', '127.0.0.1')
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from cassandra.cluster import Cluster

HOSTS = os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(',')
cluster = Cluster(HOSTS)
session = cluster.connect('trustsphere')

# -- Known IDs ----------------------------------------------------------------─
JOE          = uuid.UUID('fe878ccf-aba7-4b16-8b5f-847f7db6e0ad')
WOZNIAK      = uuid.UUID('16f033ca-2b2c-4745-a537-82999209774c')
KONDO        = uuid.UUID('9c89c702-6c61-49c8-9f0c-47b8e4e84e4b')
GATES        = uuid.UUID('86eb2b6c-1771-4533-9bd8-fca4f83fe61a')
ELON         = uuid.UUID('b4dfd93d-a9e0-4bf8-8685-735dbde17ff7')
HAWKING      = uuid.UUID('7d6e67f2-5c64-4175-8330-a0d1b2b9c45f')
EMMA         = uuid.UUID('ff52c318-95e0-4f1f-89cc-62551c814a83')
ATTENBOROUGH = uuid.UUID('aeeb7c42-d2d5-4e4e-8ed3-af313f5d6358')

REPAIR_CAFE  = uuid.UUID('aaaaaaaa-0000-0000-0000-000000000001')
COMPUTE_GUILD= uuid.UUID('aaaaaaaa-0000-0000-0000-000000000002')
SEED_KEEPERS = uuid.UUID('aaaaaaaa-0000-0000-0000-000000000003')

TOOL_LIBRARY = uuid.UUID('bbbbbbbb-0000-0000-0000-000000000001')
SOLAR_GRID   = uuid.UUID('bbbbbbbb-0000-0000-0000-000000000002')
GPU_CLUSTER  = uuid.UUID('bbbbbbbb-0000-0000-0000-000000000003')
POLLINATORS  = uuid.UUID('bbbbbbbb-0000-0000-0000-000000000004')

RIVERSIDE    = uuid.UUID('11111111-1111-1111-1111-111111111111')
AI_COMMONS   = uuid.UUID('22222222-2222-2222-2222-222222222222')
EARTHSONG    = uuid.UUID('33333333-3333-3333-3333-333333333333')

# -- 1. Schema migrations ------------------------------------------------------─
print('-- Schema migrations --')
for cql in [
    "ALTER TABLE alliances ADD member_roles map<uuid, text>",
    "ALTER TABLE projects ADD participant_roles map<uuid, text>",
]:
    try:
        session.execute(cql)
        print(f'  [OK] {cql[:60]}')
    except Exception as e:
        if 'already exists' in str(e).lower() or 'duplicate' in str(e).lower():
            print(f'  [skip] column already exists')
        else:
            print(f'  [WARN] {e}')

# -- 2. Update alliance governance ---------------------------------------------─
print('\n-- Alliance governance --')

alliance_roles = [
    (REPAIR_CAFE,   JOE,    # admin1 = Joe Rogan now
     {JOE: 'admin', WOZNIAK: 'steward', KONDO: 'member'}),
    (COMPUTE_GUILD, GATES,
     {GATES: 'admin', ELON: 'steward', HAWKING: 'member'}),
    (SEED_KEEPERS,  EMMA,
     {EMMA: 'admin', ATTENBOROUGH: 'steward'}),
]

for alliance_id, admin, roles in alliance_roles:
    session.execute(
        "UPDATE alliances SET admin1 = %s, member_roles = %s WHERE alliance_id = %s",
        [admin, roles, alliance_id]
    )
    print(f'  [OK] alliance {alliance_id} → admin={admin}, roles set')

# -- 3. Update project governance ----------------------------------------------
print('\n-- Project governance --')

project_roles = [
    (TOOL_LIBRARY, {WOZNIAK: 'manager', JOE: 'contributor', KONDO: 'contributor'}),
    (SOLAR_GRID,   {JOE: 'manager', WOZNIAK: 'contributor'}),
    (GPU_CLUSTER,  {ELON: 'manager', GATES: 'contributor', JOE: 'contributor'}),
    (POLLINATORS,  {ATTENBOROUGH: 'manager', EMMA: 'contributor'}),
]

for project_id, roles in project_roles:
    session.execute(
        "UPDATE projects SET participant_roles = %s WHERE project_id = %s",
        [roles, project_id]
    )
    print(f'  [OK] project {project_id} → roles set')

# -- 4. Entity value cards ------------------------------------------------------
print('\n-- Entity value cards --')

# Clear existing entity cards
entity_ids = [
    REPAIR_CAFE, COMPUTE_GUILD, SEED_KEEPERS,
    TOOL_LIBRARY, SOLAR_GRID, GPU_CLUSTER, POLLINATORS,
    RIVERSIDE, AI_COMMONS, EARTHSONG,
]
for eid in entity_ids:
    existing = list(session.execute("SELECT card_id FROM value_cards WHERE user_id = %s", [eid]))
    for row in existing:
        session.execute("DELETE FROM value_cards WHERE user_id = %s AND card_id = %s", [eid, row.card_id])
print(f'  cleared existing entity cards')

ENTITY_CARDS = [
    # Repair Café Collective
    (REPAIR_CAFE, 'Repair over replacement',
     'Broken things deserve a second life, not a landfill.',
     'Because every repaired object is a small act of defiance against disposability.',
     ['Turn up on Saturdays with whatever is broken', 'Never buy new if the old one can be fixed'],
     'Starting to recommend replacement before trying the repair.',
     'The repair over the revenue.',
     'Charging for skills we freely have.',
     'creative', 'honey'),
    (REPAIR_CAFE, 'Skill flows freely',
     'Knowledge gained here is shared here — the collective only grows if everyone teaches.',
     'Hoarded expertise creates dependency; shared expertise creates resilience.',
     ['Pair an experienced fixer with a first-timer every session', 'Document fixes in the shared repair log'],
     'Doing the repair for someone without explaining what you did.',
     'Teaching over doing.',
     'Gatekeeping techniques or tools behind seniority.',
     'experiential', 'leaf'),

    # Open Compute Guild
    (COMPUTE_GUILD, 'Compute as commons',
     'GPU cycles are a public good — allocated by need, not by budget.',
     'Concentration of compute power reproduces the same inequalities we are trying to escape.',
     ['Publish allocation decisions on the shared board', 'Prioritise under-resourced researchers in each cycle'],
     'Quietly favouring guild members we know over open applications.',
     'The most impactful research over the most familiar applicant.',
     'Grant compute to any project with private or proprietary goals.',
     'creative', 'moss'),
    (COMPUTE_GUILD, 'Transparent allocation',
     'Every allocation decision is visible and contestable by every guild member.',
     'Opaque gatekeeping is just hierarchy with better PR.',
     ['Publish the voting record after each cycle', 'Post the criteria before, not after, decisions are made'],
     'Making allocation decisions in side-channels before the formal vote.',
     'The process over the outcome.',
     'Override a guild vote on efficiency grounds without a re-vote.',
     'attitudinal', 'sage'),

    # Seed Keepers Alliance
    (SEED_KEEPERS, 'No variety lost on our watch',
     'Every heirloom variety represents centuries of selective memory. Extinction is irreversible.',
     'Monocultures are fragile. Diversity is the hedge against everything we cannot predict.',
     ['Maintain active grow-outs of at least 30 varieties per season', 'Backup every seed library in two separate locations'],
     'Narrowing the seed library to only popular or high-yield varieties.',
     'Biodiversity over convenience.',
     'Patent, license, or sell seeds entrusted to our care.',
     'attitudinal', 'leaf'),
    (SEED_KEEPERS, 'Seeds are not property',
     'We hold seeds in trust for the commons — they were not ours to begin with.',
     'Intellectual property applied to seeds is violence against food sovereignty.',
     ['All seeds traded freely with no conditions beyond growing them on', 'Reject any application to trademark or patent shared varieties'],
     'Restricting access to seeds based on membership status.',
     'Openness over control.',
     'Enforce exclusivity over any seed that passes through our hands.',
     'creative', 'sage'),

    # Community Tool Library
    (TOOL_LIBRARY, 'Share before buying',
     'If we already have it collectively, buying another is waste.',
     'Most tools sit idle 95% of the time — pooling them is the obvious move.',
     ['Check the library before any personal tool purchase', 'Add any new personally-owned tool to the shared catalogue'],
     'Treating the library as a last resort rather than the first option.',
     'Access over ownership.',
     'Let a tool leave the library without a return date.',
     'creative', 'honey'),
    (TOOL_LIBRARY, 'Return it better than you found it',
     'The care we give borrowed tools is the care we show the community.',
     'Neglect is contagious. One well-maintained tool inspires the next borrower.',
     ['Clean and oil tools before returning', 'Report damage immediately — hiding it breaks the system'],
     'Returning tools dirty or damaged without flagging it.',
     'The state of the commons over convenience.',
     'Replace a damaged tool with a cheaper version without telling the library.',
     'attitudinal', 'terracotta'),

    # Neighbourhood Solar Microgrid
    (SOLAR_GRID, 'Energy as community resilience',
     'When the grid fails, we should still have lights — especially on the households that need it most.',
     'Centralised energy infrastructure is a single point of failure and a lever of control.',
     ['Size battery storage for the whole block, not just contributors', 'Wire surplus first to households flagged as most vulnerable'],
     'Prioritising contributors\' comfort over the neediest households.',
     'Resilience for everyone over reward for contributors.',
     'Disconnect a household from surplus because they can\'t afford a panel.',
     'creative', 'honey'),
    (SOLAR_GRID, 'Surplus goes where it is needed',
     'Excess generation is a gift, not a credit — it flows to whoever needs it most that day.',
     'Energy surplus is the most concrete form of mutual aid we can build into infrastructure.',
     ['Surplus algorithm weights by energy poverty index, not contribution history', 'Review allocation monthly at a public meeting'],
     'Accumulating surplus credits and trading them privately.',
     'Need over desert.',
     'Sell surplus back to the grid before offering it to neighbours.',
     'attitudinal', 'leaf'),

    # Open GPU Cluster
    (GPU_CLUSTER, 'Knowledge as a public good',
     'Research funded by the commons must return to the commons — no exceptions.',
     'Privatising publicly-generated knowledge is expropriation wearing a patent.',
     ['All outputs must be published open-access within 90 days', 'Source code for models trained on cluster time is released under AGPL'],
     'Allowing "pending publication" to become indefinite embargo.',
     'The open record over convenience for the researcher.',
     'Grant cluster time to any project with publication restrictions.',
     'creative', 'moss'),
    (GPU_CLUSTER, 'Compute by need, not by wealth',
     'Who gets the GPUs is decided by what will help the most people, not by who has the largest grant.',
     'Wealth-based allocation of compute reproduces the same power structure in every domain it touches.',
     ['Blind review of applications: no institution names, no team sizes', 'Weight scoring towards under-resourced applicants and Global South teams'],
     'Fast-tracking applications from prestigious institutions.',
     'Impact over prestige.',
     'Charge for cluster time, even cost-recovery, to any member team.',
     'attitudinal', 'sage'),

    # Pollinator Corridor
    (POLLINATORS, 'Corridors over islands',
     'A garden is only as good as its connections — pollinators cannot thrive in isolated patches.',
     'Fragmentation is the quiet killer. Connectivity is the intervention.',
     ['Map and plug every gap in the corridor at least once a season', 'No permanent structures within the wildflower strips'],
     'Treating our own patch as sufficient and ignoring adjacent gaps.',
     'The corridor over any single garden.',
     'Apply pesticides anywhere within 50m of the corridor.',
     'creative', 'leaf'),
    (POLLINATORS, 'Plant for generations you will never meet',
     'A hedgerow planted today will shelter insects for a century. We are caretakers, not owners.',
     'Short-termism destroyed most habitats. The remedy requires thinking in decades.',
     ['Choose native perennials over annuals wherever possible', 'Document what we plant and why so future stewards understand the intent'],
     'Choosing plants for visual impact over ecological function.',
     'The long arc over the immediate result.',
     'Remove established plants for aesthetic reasons.',
     'attitudinal', 'sage'),

    # Riverside Commons (sphere)
    (RIVERSIDE, 'Tools travel, not money',
     'Everything a neighbour needs to build, fix, or grow should be accessible without spending anything.',
     'Money is not the only currency of exchange. Trust, time and skill are at least as real.',
     ['Keep the tool library stocked and repaired before any purchase', 'Celebrate borrowing — it is not charity, it is the system working'],
     'Defaulting to cash transactions when a tool-share would serve.',
     'Access over ownership.',
     'Let any community resource sit idle when a neighbour has a need.',
     'creative', 'honey'),
    (RIVERSIDE, 'Repair is radical',
     'In a disposable economy, choosing to fix something is a political act.',
     'Every toaster that gets repaired is a small withdrawal from the extractive economy.',
     ['Host Repair Café every Saturday, rain or shine', 'Celebrate the repaired thing as loudly as the new one'],
     'Quietly accepting disposal when repair was possible.',
     'The repaired over the replaced.',
     'Recommend replacement for economic reasons without attempting repair first.',
     'attitudinal', 'terracotta'),

    # AI Commons (sphere)
    (AI_COMMONS, 'Intelligence must be held in common',
     'AI systems shaped by concentrated interests will serve concentrated interests.',
     'The most powerful tool of the 21st century cannot be a private moat.',
     ['Pool compute for any open, non-commercial research request', 'Refuse to support closed-weight models with our infrastructure'],
     'Treating AI capabilities as a competitive advantage.',
     'The open field over the closed lab.',
     'Provide infrastructure to any project with proprietary licensing terms.',
     'creative', 'moss'),
    (AI_COMMONS, 'No moat, no monopoly',
     'Openness is not a strategy — it is a requirement for AI to serve humanity rather than extract from it.',
     'Every capability kept behind a paywall or API narrows who benefits and who decides.',
     ['Publish weights, datasets, and training code for all AI work done on commons infrastructure', 'Actively document and share what we learn, even when it fails'],
     'Open-washing: releasing a limited version while keeping the useful parts private.',
     'The reproducible experiment over the impressive demo.',
     'Contribute to or validate benchmarks that primarily serve corporate positioning.',
     'attitudinal', 'sage'),

    # Earthsong Gardens (sphere)
    (EARTHSONG, 'The soil remembers',
     'Healthy soil is the foundation of everything. What we put in it today will feed or haunt us for decades.',
     'Industrial agriculture treats soil as a substrate. We treat it as a living community.',
     ['Test soil health every season and publish the results', 'Never apply synthetic inputs without a full member vote'],
     'Prioritising yield this season over soil health next decade.',
     'The soil over the harvest.',
     'Apply any substance to shared soil without member consent.',
     'experiential', 'leaf'),
    (EARTHSONG, 'Stewardship over ownership',
     'We are tenants of this land with responsibilities to the species that cannot speak for themselves.',
     'Land ownership is a legal fiction. Stewardship is the actual relationship.',
     ['Make all land-use decisions by consensus at the monthly moot', 'Maintain at least 40% of the site as undisturbed habitat'],
     'Treating the garden as a backdrop for human activity.',
     'The ecosystem over the aesthetic.',
     'Make any irreversible change to the land without full community consent.',
     'attitudinal', 'sage'),
]

for (owner_id, title, care_about, because, looks_like, drift, conflict, never, frankl, color) in ENTITY_CARDS:
    card_id = uuid.uuid4()
    now = datetime.utcnow()
    session.execute(
        """INSERT INTO value_cards
           (user_id, card_id, title, care_about, because, looks_like,
            drift_looks_like, in_conflict, never_do, frankl_mode, color_key, created_at)
           VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
        (owner_id, card_id, title, care_about, because, looks_like,
         drift, conflict, never, frankl, color, now)
    )
    print(f'  [OK] {owner_id} → "{title}"')

print('\n[DONE] Governance and entity value cards seeded.')
