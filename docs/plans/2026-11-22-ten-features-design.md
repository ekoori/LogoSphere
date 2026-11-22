# Ten features: design and plan (2026-11-22)

Requested by Igor on 2026-11-22. Each stage ships on its own: backend + spec + tests, site, app, deploy,
commit. Tick the boxes as they land.

## The request, as understood

1. Trail / Openings / People tabs open on **Openings** everywhere; Trail stays first.
2. **Simple and Advanced** modes. Simple shows the gift economy (value cards included) with fewer options, for
   older people and beginners.
3. **AI help drafting value cards.**
4. **AI pictures** wherever something is created (openings, groups, events). **Never for receipts or evidence.**
5. **Real places** wherever a location is chosen, to the precision the person wants; show who is nearby.
   Free service, offline preferred.
6. **Meaning Graph** visualisation like Obsidian's graph, a very important part of the platform, with a fair and
   transparent closeness algorithm.
7. **Camera** for receipt photos in the app.
8. **Initials centred** in avatar circles.
9. **Acknowledgements on every Meaning Trail**: text plus value cards; anyone may add one, except in spheres
   they aren't in; they can be liked; the trail's owner can highlight; consecutive ones are combined, with at
   most two highlighted in a group.
10. **What Kindista offers**, without copying it.

## Stages

- [x] S0 Close the access holes found while reading (below)
- [x] S1 Openings default, centred initials, camera
- [ ] S2 Acknowledgements
- [ ] S3 Meaning Graph
- [ ] S4 Simple / Advanced
- [ ] S5 AI help and pictures
- [ ] S6 Places and nearby
- [ ] S7 Kindista gaps
- [ ] S8 Privacy, Terms, How it works, app info text; end-to-end pass

## S0 Access holes (they contradict the Privacy page, and item 9 relies on them)

| Hole | Rule |
|---|---|
| `POST /api/meaning_trail {userId}` returns exchanges from spheres the viewer isn't in | filter like `GET /api/exchange/<id>` |
| an opening can be posted into, accepted or liked in any sphere by id | sphere members only; sphere name, status and type come from the server |
| `/api/value_cards/<id>` needs no session | signed in; signed-out only for a public sphere's charter |
| a private sphere's member list goes to every signed-in person | `member_count` only for non-members; demo and public spheres stay listed; none to signed-out visitors |
| clients supply the value-card snapshot stored with a receipt | the server resolves cards by id |
| receipt photos can be replaced after the exchange is finished | once finished: one upload, within an hour of the receipt |

One module, `app/utils/access.py`, answers "may this person see / write here".

## S1

- Web Home, person and group pages; app Trail, person and group screens; the app starts on the Openings tab.
  `?tab=` still wins; both clients accept `trail|openings|people|governance`.
- Server initials SVG: position by baseline arithmetic (AndroidSVG ignores `dominant-baseline`). App placeholder:
  line height = font size, no font padding. The header shows the member's avatar.
- `TakePicture` + FileProvider (cache only, no CAMERA permission); site: a `capture` input on touch devices.

## S2 Acknowledgements

- `trail_acknowledgements ((trail_id), created_at, ack_id)`; `trail_id` is a person, group or exchange.
  Likes reuse `likes` with type `ack`.
- Write: person's trail, any member; group, members of its sphere; exchange, who can see it and is in its
  sphere or a party. Highlight: that person; the group's own managers; either side of an exchange.
  Remove: author, trail owner, platform admin.
- `GET /api/trails/<id>` is the one timeline both clients draw. Consecutive acknowledgements form a run; runs
  of three or more collapse to the highlighted ones (else the newest). The server refuses a third highlight in
  a run; if two runs later merge, only the two most recent highlights show.
- The old single slot on exchanges still reads; further ones go to the new table.

## S3 Meaning Graph and "closeness" (method v1)

What exists: the Meaning Alignment Institute's moral graph (Klingefjord, Lowe, Edelman 2024, arXiv:2404.10636)
treats a value as a bundle of attentional policies and links cards by participants' judgement that one is
*wiser* than another. It defines no undirected closeness. X's Community Notes ranks notes by cross-viewpoint
agreement, gives no item-to-item distance, and needs far more raters than we have. Embeddings recover broad
value structure (arXiv:2509.24906) but can't be explained edge by edge and would send members' cards to a third
party. So: our own method, taking "what you attend to" and "people judge, not just the machine" from the first.

For two cards:

- **Words** = cosine over what is attended to: care_about .35, looks_like .30, title .20, because .15. Each
  field is normalised first (writing more doesn't help). A word's rarity counts *owners*, not cards (writing
  more cards doesn't help). Light stemming and a published list of word families. What-you-would-never-do,
  drift and conflict fields are left out: negations read as agreement.
- **Lived** = m/(m+3), m = different people who put both cards on one receipt, note or acknowledgement. Counts
  from m = 2, so no edge reveals one person's act.
- **Lineage** = .5 when one was made from the other.
- base = 1 - (1-words)(1-lived)(1-lineage).
- **Judgement**: from two voters, closeness = (4 x base + n x share saying close) / (4 + n).

Never inputs: likes, follows, roles, wealth of activity, who the owner is. AI personas never vote or supply
evidence. The same pair has the same score for every viewer; nodes are filtered by what the viewer may see.
Every edge shows its parts; `GET /api/meaning_graph/method` publishes weights, stop words and families.
Node = a card's version chain. Size = connections. Colour = card colour. List view for screen readers.

## S4 Simple / Advanced

`users.ui_mode`; new accounts start Simple, existing ones stay Advanced; switch in the menu and Settings / Me.
Simple hides: governance and policies, join policy, acting as a group, project choice, alliance/project top
navigation, kind-of-meaning and context on receipts, endorse/review states, cloning, the optional card fields,
version history, ids, "near my values", graph tuning. Presentation only: never a permission.

## S5 AI

- Card: the member's notes in, an editable draft and a reflective question out. Never auto-saved. Sends only
  what they typed, no name or id.
- Pictures: preview, then the ordinary upload. The server keeps each generated picture's hash and fingerprint;
  receipt photos and exchange pictures refuse those and files that declare AI generation in their metadata.
  AI pictures are labelled wherever they show. Detection can't catch every outside AI picture: say so.
- Per-member and platform daily caps; off cleanly without keys.

## S6 Places

- `place` (JSON) beside the old text on people, groups, openings, events: label, point, precision
  (country, region, town, postcode, about 5 km, about 1 km, exact). The point is coarsened before storing.
- Other members never get a person's point; distances use cells of 1 km or more and come back in bands.
- Search: self-hosted GeoNames (CC BY 4.0) in SQLite FTS5 on the host. Needs Igor's OK to download.
- Pin: device location, or a map (OpenStreetMap tiles with attribution, loaded only when opened).
- Nominatim rejected: autocomplete forbidden. Photon self-host rejected: ~95 GB, 64 GB RAM.

## S7 Kindista, clean room

Licence: AGPL-3.0. **No source file was opened or cloned, and no wording, layout or art is reused.**
Sources: the repository's description and README; B. Crandall's 2015 article (ic.org/?p=108775); search-engine
excerpts of its public FAQ and pages. kindista.org's domain has expired; archives refused automated reading.
So this covers what is publicly documented, which may not be everything it had.

| Publicly documented | Here before | To build |
|---|---|---|
| offers and requests | Openings | - |
| lending | - | "to borrow" openings |
| gratitude on profiles | receipts | acknowledgements (S2) |
| contacts and their activity | follow | activity of people you follow |
| mutual connections | shared spheres | "you both know" |
| groups, approval, group-only posts | spheres, alliances, projects | - |
| sharing with other groups | - | share an opening with more spheres |
| messages, also to all respondents | - | conversations |
| events | - | events, repeats, attendance |
| announcements | - | group announcements |
| sharing near you, by radius | free-text place | S6 |
| joining by invitation | reset links only | invitation links (no email service) |
| no selling or barter | Terms | - |

Messaging requires block and report, with an admin queue.

## Rules that hold throughout

Schema before restart; check CQL reserved words. Every route in LogoSphereAPI.yaml. Tests on production under
keyspace_guard. Never print keys. Personas act only in demo spheres.
