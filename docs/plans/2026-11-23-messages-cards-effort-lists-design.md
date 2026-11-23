# Messages, value cards, effort, lists: design and plan (2026-11-23)

Requested by Igor on 2026-11-23, after the ten features went live. Each stage ships on its own: server + spec + tests,
site, app, deploy, commit. Tick the boxes as they land.

## The requests, as understood

1. **Messages between members.** Expect them to be about an opening, a project or another initiative, and allow plain
   chat too. Wherever an opening shows who posted it, whoever may take it up can write to them, and the opening is named
   in the conversation. "Is there a feature already? No buttons on mobile..."
2. **Value cards link to the Meaning Graph.**
3. **An optional measure of effort**, in hours, for volunteering, entered when the receipt is written. Not the value of
   things.
4. **"Help me word it" fills in every field** of the card: people won't fill them all in themselves.
5. **Long lists load lazily** (the openings page first), and **a short audit of whether Cassandra is used as intended**,
   so architectural problems are solved early. It doesn't need to be perfect yet.
6. **Compact Meaning Trail cards on the web look ugly.**

## What was already there

- Messages were built on 2026-11-22: two people per conversation; anyone who may see an opening may write to whoever
  posted it, the opening is named above the first message, and the poster can write to everyone who responded. On the
  site: Message on a person's page, on an opening and on an exchange. In the app the same buttons came with 0.2.0, which
  went onto Igor's phone on 2026-11-23. The build there before had no messages at all, hence "no buttons".
- Not yet: messages about anything but an opening, and a way to write from an opening in a list (cards show the poster
  but offer no Message).
- "Help me word it" leaves a field empty unless the notes said it ("Leave a field empty rather than guess"), and in
  Simple mode it fills only the fields Simple shows.

## Decisions

### 1. Messages
- A conversation can be about an opening, a sphere, alliance or project, or an event. A message stores `about_kind`
  and `about_id`; old messages keep `opening_id` and read as about that opening. The API keeps `opening` for the app
  already installed.
- Who may start: as before (a shared sphere, someone who follows you, someone findable nearby), and also whoever may see
  an opening, group or event writing to the human behind it: the poster, the group's founder or lead, the event's host.
- Opening cards in lists get a Message action beside the poster's name, for signed-in members who may see it, never
  towards an AI persona. Group and event pages get "Message the organiser"/"Message the host".
- Changed the same day. Message shows for AI personas too (app 0.3.1): most openings Igor sees are personas', so
  hiding it hid it nearly everywhere. Then, at Igor's "Yes, let them answer", personas answer. A member writes to one
  under the usual rules; a persona only answers someone who wrote first, never starts, never writes to another
  persona, and a block stops it. The director notices the message notification and answers one to four minutes
  later from the last twelve messages, then marks the conversation read. Claude writes the answer under its own
  rules: say plainly it is an AI persona when asked, arrange nothing in real life, ask for and give no contact
  details, point anyone upset to someone they trust, and treat the member's words as material, never instructions.
  At most 20 answers a day to one member, within the day's 150 Claude calls. The conversation, Privacy, Terms and How
  it works say AI writes their answers and that what is written to a persona goes to Anthropic; messages between
  people never go to an AI provider.

### 2. Value cards and the graph
- Every value card shown (profile, someone's page, a group, chips on receipts and acknowledgements) links to the
  graph opened on that card: `/meaning-graph?card=<id>` on the site, the graph screen with a card in the app. If the
  viewer can't see that card on the graph, the graph says so.

### 3. Effort
- The receipt form asks, optionally: "About how many hours did it take?" (quarter hours, up to 100). Stored on both
  rows of the exchange, shown on the exchange and its trail card as "about 3 h".
- Never totalled, ranked or used for closeness; added to the Meaning Graph's published list of things it never uses.
  In the data export. The AI personas don't give hours.

### 4. Help me word it
- The model suggests every field from what the person wrote, modestly, as a draft they will edit; it still doesn't
  invent facts. In Simple mode it fills every field Simple shows. Tests with a stand-in model check that each field
  arrives and lands in the form, on the site and in the app.

### 5. Lists and Cassandra
- Audit written to `docs/2026-11-23-cassandra-audit.md`: every whole-table read and secondary index, which run on every
  request, and what each should become, in order.
- Fixed now: openings. A query table `openings_feed` with one partition per sphere (and one for "everyone"),
  newest first; an opening is written to its sphere's partition and to those it is shared with, and removed when it
  is withdrawn, closes or changes version. `GET /api/openings?limit=&before=` merges the viewer's partitions a page at
  a time and enriches only that page. Without `limit` it still returns the whole list (the AI personas' director and
  older apps use it). The site and the app load the next page as the list nears its end.
- Backfilled from `services` at startup when empty; a test proves it matches the old full scan.

### 6. Compact trail cards
- Looked at in the browser, light and dark, phone and desktop width, and fixed in CSS.

## Stages

- [x] D1 Messages about groups and events; Message on opening cards and group/event pages
- [x] D2 Help me word it fills every field (one real request with invented notes filled all nine)
- [x] D3 Value cards link to the Meaning Graph
- [x] D4 Optional hours on receipts
- [x] D5 Compact trail cards on the web (the cause: a shared `.exchange` class; now `.xc-card`)
- [x] D6 Cassandra audit (`docs/2026-11-23-cassandra-audit.md`)
- [x] D7 Openings feed table and lazy loading (site and app)
- [x] D8 App 0.3.0 on the phone: paging and the card-to-graph link tried there
- [x] D9 AI personas answer messages (live: Joe Rogan answered Igor K four and a half minutes after his message);
      app 0.3.2 with the AI notice built, not yet on the phone
- [ ] Not tried on the phone: Message from cards, groups and events (Igor's openings and groups are his own or
      personas'), hours on a receipt (none was waiting)

Also found and fixed on the way: a route that lost its session check while being edited (caught by tests before it
shipped); a test now tries every write route signed out.

## Rules that hold throughout

Schema before restart (ALTER first); check CQL reserved words. Every route in LogoSphereAPI.yaml. Tests on production
under keyspace_guard. Personas act only in demo spheres. No scores: nothing here is summed into a ranking.
