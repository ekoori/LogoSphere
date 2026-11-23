# Is Cassandra used as intended? (audit, 2026-11-23)

Asked by Igor on 2026-11-23: "we need a lazy load where long lists of entities are loaded … that was the whole
point of using Cassandra - we even might need to do a little audit whether Cassandra is used as intended (doesn't
need to be perfect yet … but architectural issues better to solve early on)".

## Short answer

Not yet. Most of the app reads Cassandra the way one would read a small SQL database: whole tables, filtered in
Python. That is fast today only because the tables are tiny (the largest has 162 rows), and it gets slower with every
member, opening and exchange, on every request. Cassandra is fast when each screen's question is answered by
**reading one partition, already in the order the screen needs, a page at a time**. That means a table per question,
written when the data changes ("query tables"), instead of filtering one table many ways.

## What production holds today

One node, keyspace `logosphere` with `SimpleStrategy`, replication factor 1, 1.1 MB on disk. Largest tables: sessions
162 rows, services 131, value_cards 51, notifications 43, users 23.

## What is done well

- **Messages**: one partition per conversation, newest first, paged with `message_id < ?`. The right shape.
- **Notifications**: one partition per member, clustered by time, read with `LIMIT`.
- **Acknowledgements, likes, opening acceptances**: one partition per thing they belong to.
- **Counters for limits** (`mail_counts`): a partition per limit, rows expire by TTL.
- **Pictures** moved out of rows into object storage; rows keep a key and a flag.
- No `ALLOW FILTERING` in hand-written CQL; one-time links use lightweight transactions (`IF EXISTS`).

## Problems, worst first

| # | Problem | Where | Runs | Effect as it grows | Fix |
|---|---|---|---|---|---|
| 1 | **The openings list reads every opening, every acceptance and every like**, then filters and sorts in Python, and sends all of it | `GET /api/openings` (`Service.get_all`, `all_acceptances`, `all_likes`) | every visit to Openings, every 15 s on some screens | grows with all openings ever posted; the page can't be lazy | **Fixed now**: `openings_feed` (below) and pages of 30 |
| 2 | **An exchange is found by scanning every partition** (`exchange_id` is a clustering column; cqlengine `allow_filtering()`) | `MeaningTrail.get_for_view`, status, comments, likes (8 call sites) | every exchange page, receipt, like | a full-cluster scan per click | `exchanges_by_id ((exchange_id))` lookup table, or make the exchange its own partition |
| 3 | **Who is in which sphere is found by reading every sphere**, on every request (`Sight()` → `member_sphere_ids`) | `app/utils/access.py`, `models/spheres.py` | every signed-in request | grows with spheres × members | `memberships_by_member ((user_id), sphere_id)`, written on join/leave |
| 4 | **The other side's trail uses a secondary index** (`meaning_trail.other_user_id`), and `exchange_status` has a low-cardinality index | `get_meaning_trail`, `MeaningTrail` | every trail | indexes on non-unique, low-cardinality columns touch every node | `trail_by_member ((user_id), started_at, exchange_id)` written for both sides; drop the status index |
| 5 | **Whole-table reads on hot paths** besides those: blocks (`safety.hidden_from`), follows (followers), events (`everything()`), invitations (`made_by`), acknowledgements (`everything()`), AI pictures (fingerprint match) | various | per request, or per upload | each grows unbounded | a query table per question: `blocks_by_member`, `followers ((followee_id))`, `events_by_group ((group_id), starts)`, `invites_by_maker`, `ai_pictures_by_fingerprint` |
| 6 | **Sessions never leave the table**: rows have an `expire_at` but no TTL | `sessions` | every sign-in | the table only grows (July's are still there) | write with `USING TTL` 30 days and refresh it when the expiry slides |
| 7 | **Sign-in by email uses a secondary index** on `user_credentials.email` | login, password reset | every sign-in | acceptable while small; uniqueness isn't enforced | `credentials_by_email ((email))`, written with `IF NOT EXISTS` (also stops two accounts sharing an address in a race) |
| 8 | **Group and name lookups read whole tables** with short in-memory caches: names map, kind map, sphere names, demo spheres, the Meaning Graph, the search index | `meaning_trail._name_map`, `demo.py`, `meaning_graph.py`, `search_vectors.py` | cached for seconds to minutes | each rebuild reads everything | fine at this size; move to per-id reads, or rebuild in the background, when they show up in timings |
| 9 | **One node, replication factor 1** | infrastructure | — | no copy if the disk fails; no availability during restarts | at the production cut-off: three nodes, `NetworkTopologyStrategy`, RF 3, `LOCAL_QUORUM`; until then the nightly dumps are the only copy |

Not problems: admin pages and data export read whole tables on purpose and rarely; `count(*)` is used only within a
single partition.

## The openings fix (done 2026-11-23)

- `openings_feed ((place), created_at DESC, service_id DESC)`: one partition per sphere, plus one for openings posted
  to everyone. An opening has a row in its own sphere's partition and in each sphere it is shared with, while it is
  listed (current, not withdrawn, not a single one already under way). `opening_feed_rows ((service_id), place)`
  says where its rows are, so a change can take them out.
- Every change to an opening goes through one function (`openings_feed.sync`), called from the model's own writes
  (create, edit into a new version, status changes, sharing, admin deletion). At start-up the feed is checked against
  `services` and repaired (cheap at this size; to become a background job later).
- `GET /api/openings?limit=30&before=<cursor>` merges the viewer's partitions newest first, reading only as far as
  one page needs, and builds only that page (likes and acceptances per opening, not for all). Filters (offers,
  needs, loans, a sphere, demo or real, distance, words) are applied while merging; a request reads at most a few
  hundred rows and says where to carry on.
- Without `limit`, the old whole list is still served for the AI personas' director and older apps.
- The site and the app load the next page as the list nears its end.

## Order for the rest

2 and 3 next (they run on almost every request), then 4 and 6, then 5 one table at a time when its screen gets paged.
7 at the latest when sign-up opens widely; 9 at the production cut-off. Each is the same pattern as the openings fix:
a query table, written in the model's own write path, backfilled once, and checked by a test against the old query.
