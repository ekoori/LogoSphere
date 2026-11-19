# Demo spheres and AI personas — design

Date: 2026-11-19. Status: agreed, being built.

## Why

LogoSphere runs one production platform where real communities (Banyule
Commons) and the demonstration (Riverside Commons, AI Commons, Earthsong
Gardens) live side by side. The demonstration should feel alive when people
try it, must never be mistaken for real people or real communities, and should
cost nothing when nobody is looking. Its text should read like a real
community, not like generator output.

## Decisions

| Question | Decision |
|---|---|
| How demo and real coexist | Side by side, clearly labelled. Not hidden behind a switch, not a separate site. |
| New members | Invited to all three demo spheres (notification + a home card); not auto-enrolled. |
| Who the personas are | The 20 famous-name demo accounts, Joe Rogan included. Joe stops being a platform admin. Igor K, Bruce (AI) and Mimi stay real. |
| What drives them | Real activity. A scheduled director reacts to what real members do; personas may also react to each other, within "ripple" credits that real activity creates and that fade within the hour. Quiet when nobody is around. |
| Model for words | Claude Opus 5.5, effort `low`, structured JSON output. |
| Model for pictures | OpenAI `gpt-image-1-mini`, low quality, resized to a ~150 KB JPEG. |

## 1. Marking demo content

- `spheres.is_demo` (boolean). Alliances, projects, openings and exchanges are
  demo when their sphere is. `users.is_agent` (boolean) marks persona accounts.
- The API adds `is_demo` to spheres, alliances, projects, openings and
  exchanges, and `is_agent` wherever it names a person with an id.
- Web and app:
  - the Spheres list shows real spheres first, then a **Demo spheres** section;
  - a demo sphere's page carries a strip: *Demo sphere. The members here are AI
    personas, famous names playing everyday neighbours. Try anything; nothing
    here is real.*;
  - openings, exchanges and groups from demo spheres carry a **Demo** tag;
  - persona accounts carry an **AI persona** tag on their profile and next to
    their name;
  - the Openings sphere filter offers **Real spheres only**.
- Joining: registration sends a `demo_invite` notification; the home page
  (web) and Trail (app) show a dismissible *Try the demo spheres* card with
  **Join all three** while the member is in none. `POST /api/demo/join` joins
  them all.
- Admin console: *demo* toggle per sphere, *AI persona* toggle per user.

## 2. The personas

Each persona has a short sheet (in `backend/agents/personas.json`): an
everyday-neighbour version of the account drawn from its value cards and
posts, plus its voice. Every prompt carries the same guardrails: a fictional
neighbour who shares a famous name; never claims to be or speak for the real
person; no real-world events, politics, products or endorsements; short, warm,
specific and everyday. Generated images show places and things, never people.

### Reactions

Triggered only inside demo spheres, after a randomised delay of a few minutes:

| Someone… | …and a persona |
|---|---|
| accepts a persona's opening | confirms it, or kindly declines if already promised |
| has an acceptance confirmed by a persona, or confirms a persona's | moves the exchange along as the other side does |
| finishes an exchange or writes a receipt | writes its own side (receipt or note) |
| posts an opening in a demo sphere | the best-matching persona (value-graph vicinity) offers or accepts; another may appreciate it |
| follows a persona | follows back |
| appreciates a persona's opening | appreciates something of theirs in return |
| joins a demo sphere | welcomes them: a follow, and an appreciation of their first opening |

A real member's action always gets its reactions. A persona's action gets a
persona reaction only while the sphere has ripple credits: each real action
adds 3 credits to its sphere, a persona-to-persona reaction spends one, and
credits fade after an hour.

## 3. Running it

- `logosphere-agents.service` on the host runs `backend/agents/run.py`.
  Every ~30 seconds it reads each persona's unread notifications through the
  platform API (logged in as the persona) and looks for new openings and
  exchange changes in demo spheres; plans reactions into the `agent_queue`
  table with a due time; and runs the due ones: Claude writes the words, the
  persona acts through the API like any member.
- Limits (settings in `agents.env`): 150 Claude calls and 20 images a day,
  at most 3 reactions per member per hour; every call's usage is logged with a
  daily summary.
- `AGENTS_ENABLED=false` stops all action; `AGENTS_DRY_RUN=true` logs what
  would happen instead. The test suite pauses the personas while it runs
  (`agent_settings.paused_until`).
- Failures retry later; a refusal or unusable output skips the reaction.
- Images are stored as blobs until object storage exists.

## 4. Cleaning the demo text

A one-off script (dry run first) rewrites the 68 openings that carry generator
text and the exchanges with template text, in the provider's persona voice,
keeping ids, dates, likes, acceptances and exchanges. Self-likes go. Banners
with text baked into the picture are regenerated text-free and small.

## Testing

- Reaction planning is pure functions with unit tests: demo spheres only,
  caps, ripple credits, delays, no duplicate replies.
- Claude and OpenAI sit behind small interfaces with fakes; one manual live
  smoke test.
- The new API fields, invitation and admin toggles join the production suite,
  which uses a throwaway platform admin instead of Joe.
- The service runs in dry-run mode on production before it is switched on.

## Afterwards

The Android app catches up: labels, the demo card, admin labels, no
appreciate button on one's own openings, Meaning Graph wording, 503 handling.
