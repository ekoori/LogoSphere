# LogoSphere run-through — 19 November 2026

A pass over every feature of the platform after the Android client landed: the
app on a phone (Samsung Galaxy Note 9, Android 10) and the web, both against
production (ts.krbavcic.com) as the demo platform admin, Joe Rogan.

## Test suites

| Suite | Where it runs | Result |
|---|---|---|
| Backend API (pytest) | on production, between two data dumps | 95 passed, data unchanged |
| Web unit tests (Vitest) | locally | 28 passed |
| Android `:core` (JUnit) | locally | 54 passed |

New this pass: openings and trails come back newest first, an accepter can take
an acceptance back, and the web reads API datetimes as UTC.

## Fixed

**Earlier in the Android work (already deployed)**

- Security:
  - session tokens were logged, and the login response could carry another live token;
  - any member could read every member's email from public profiles;
  - a platform admin counted as "the other side" of every exchange and opening, so an admin could write a person's receipt or value cards, or confirm their own acceptance;
  - an `add_exchange` endpoint created exchanges without the other party's consent;
  - alliances and projects could be founded in spheres the founder hadn't joined;
  - marking a notification read could create a phantom one.
- Stability: reading multi-MB image blobs through the gevent driver stalled the connection until the heartbeat killed it. This is the likely cause of the September outage. Trails, openings and users are now read without blobs, using `has_image`/`has_picture` flags.
- Payloads: user data embedded the profile picture as base64, so every session check carried megabytes.

**In this pass (all deployed)**

| What was wrong | Fix |
|---|---|
| Once you accepted someone else's opening, you could not take it back. The only button a platform admin saw was "Withdraw", which withdraws the whole opening for everyone; this happened on the phone. | Added **Take back my acceptance** to the server, web and app. On someone else's opening, the admin button now reads "Withdraw … (platform admin)". |
| The web read the API's zone-less UTC datetimes as local time. In UTC+11, a notification from a minute ago read "11h ago", and dates near midnight showed the wrong day. | Added a single parser (`frontend/src/utils/dates.js`, with tests), used everywhere the web shows a date. |
| nginx sent `index.html` without `Cache-Control`. Browsers kept running an old bundle for days after a deploy; Joe's profile showed initials instead of his photo. | `index.html` is now `no-cache`. Hashed `/assets/` are cached for a year as immutable; `/static/` images for 7 days (that rule was left over from Create React App). |
| Openings and Meaning Trails came back in storage order, so dates jumped about. | Both are now newest first on the server (marketplace, own trail, a person's trail, a project's trail). |
| App search showed "0 members" on people. | Member counts appear only for groups, and value-card counts appear as on the web. |
| The app's "New opening" button had no accessible name (TalkBack said "Button"). | Labelled. |
| On photo banners, the status badge, "Manage …" link and "Led by …" link were unreadable. | Photo banners get a full-height scrim and light chips. |
| The new-opening form was headed "New Service". | Now "New Opening". |
| One test depended on list order. | It now selects by who provides the opening. |

## Demo data

Every test leaves the data as it found it: rows are dumped before and after, and
restored with `keyspace_guard.py` (`~/backups/`). The snapshots are in
`~/backups/logosphere-20261119/`, and a full Cassandra snapshot is
named `demo-before-android-tests-20261119`.

Leftovers from my own testing were removed:

- a test note on the podcasting exchange;
- a test opening;
- two notifications.

Barack Obama's "Community Tool Library" offer was withdrawn during a phone
session. It is back in Openings, and the two notifications that withdrawal
created are gone.

**Still as made on the phone**:

- Joe's note "Thanks Marie, it was my pleasure!" on the receipted fence exchange;
- Joe following the owner's account;
- Joe's pending acceptance of Emma Watson's opening `c13ac77d…`, plus the two notifications these created.

These can be reverted the same way.

## Suggestions

### Worth doing next

1. **Move images out of Cassandra and serve thumbnails.**
   - Joe's avatar is a 2.35 MB PNG, fetched wherever his face appears; some sphere banners are 2.2 MB.
   - Images stored in rows are what stalled the driver.
   - Store files (disk or object storage) with long-cached URLs, and generate small sizes at upload.
2. **Leave the gevent reactor.** cassandra-driver has deprecated it, and it caused the stall. Use gunicorn's `gthread` workers with the default reactor.
3. **Deploy from git.**
   - The host's checkout has uncommitted changes, because deploys were tar copies.
   - After pushing, run `git reset --hard origin/main` on the host.
   - Add the nginx vhost to the repo, e.g. `deploy/nginx/logosphere.conf`, so the caching rules aren't lost.
4. **Remove the N+1 queries from `/api/openings` (~1.2 s).** Fetch likes and acceptances for all openings in one pass instead of per opening.
5. **Stop rewriting the session row on every request.** `creation_time` changes on every call. Touch `last_access_time` at most every few minutes, and never `creation_time`.

### Correctness and consistency

6. **Normalise emails to lower case** when registering and signing in. One production account is stored in mixed case.
7. **Report database errors as errors.** Some failures surface as 404 or "invalid credentials"; return 503.
8. **Let `/api/updateuser` clear a field.** An empty surname or location is currently ignored.
9. **Make the admin override visible.** Admins also see "Edit" and "Set image" on everyone's openings, unmarked. A visible "moderating" state, or separate admin controls, would prevent mistakes like the withdrawal above.
10. **Clear the provider's stale "X wants to accept" notification** when an acceptance is taken back, or send a short follow-up.
11. **Check the OpenAPI spec against the routes in CI.** It drifts.
12. **Pick one term: "Value Graph" or "Meaning Graph".** The web uses both about equally.

### Polish and demo readiness

13. **Stop the "Log in" flash.** The nav shows "Log in" for a moment on every full page load while the session check runs.
14. **Tidy the bulk seed openings.** Newest first, the "[Bruce bulk 2026-07-05] …" seed openings fill the top of the marketplace. Give them real titles or hide them for demos.
15. **Replace banners with baked-in text.** Some generated banners contain text that clashes with the page title.
16. **Decide whether members may like their own openings.** It's currently allowed.

### Android app

17. **Notifications:** push through FCM instead of opening the Inbox to find out.
18. **Offline and links:** an offline cache for trail and openings, and App Links so `ts.krbavcic.com/opening?id=…` opens in the app.
19. **Release:** a release signing setup and a Play internal-testing track.
20. **Upkeep and testing:**
    - dependency updates (Compose BOM, Kotlin, AGP);
    - Compose UI tests against a fake API;
    - keep the exchange composer above the keyboard;
    - a TalkBack pass.

## Not verified on the phone

The phone was unplugged before the last install. Not yet seen on the device:

- the app's **Take back my acceptance** button;
- the newest-first lists.

The button's rule is unit-tested and the app builds. The lists need no app
change, because the server sorts them.
