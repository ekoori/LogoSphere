# LogoSphere for Android — design

Date: 2026-11-18 · Status: agreed scope, in implementation

A native Android client for LogoSphere that talks to the existing Flask API
(`https://ts.krbavcic.com`). It covers the everyday member loop; everything
administrative stays on the web.

## Decisions

| Question | Decision | Why |
|---|---|---|
| Technology | Kotlin + Jetpack Compose + Material 3 | "Native" was the brief; it is also the stack of every other Android app on this machine (BushLines, Pentalingo, YNABB, Wonky). |
| Scope (v1) | The core member loop (below) | Chosen over full parity and over a read-only companion. |
| Where it lives | `android/` in this repository | The client tracks the API it consumes; one PR can change both. |
| Backend during development | Production, `ts.krbavcic.com` | Asked for explicitly; no local stack needed. A debug-only server field allows a local backend later. |
| Testing | JVM unit tests plus the debug build on a USB-connected phone | No emulator image is installed; the phone was chosen. |

Alternatives considered: a Trusted Web Activity around the mobile web build
(cheapest, but not native and no better than the browser), and Kotlin
Multiplatform (only pays off if an iOS client follows; it can be adopted later
because the API layer below is already plain Kotlin/JVM).

## Scope

In:

- **Account** — sign in, create an account, sign out; the session survives restarts.
- **Trail (home)** — your Meaning Trail, your own openings, and the people you follow.
- **Openings** — browse (offers/needs, by sphere), post a new one, like, accept
  (as yourself or as an alliance/project you manage), take your acceptance back
  before it is confirmed, confirm or decline acceptances on your own openings,
  withdraw an opening.
- **Exchange** — status timeline, advance status, cancel, receipts (with Frankl
  mode, value cards and context), the initiator's note, follow-up comments,
  acknowledgements, likes, receipt photos (view only).
- **Communities** — spheres, alliances and projects: list, detail, join (or
  request to join), their trail, openings, people and charter (value cards).
- **People** — a member's profile, values, trail and openings; follow/unfollow.
- **Inbox** — notifications with unread badge, open the linked item, mark read.
- **Search** — text search and "near my values" (TF-IDF vicinity).

Out (stays on the web; the Me tab links there): entity management and roles,
governance proposals and voting, value-card authoring/editing/cloning, profile
editing, all image uploads, the admin console, About/How it works.

## Architecture

Two Gradle modules:

- **`:core`** — plain Kotlin/JVM. API models (kotlinx.serialization), the HTTP
  client (`LogoSphereApi`, OkHttp), and the lifecycle rules that decide which
  actions a screen offers (`OpeningRules`, `ExchangeRules`, `Membership`,
  `Links`, `Dates`). No Android dependency, so it is tested on the JVM against
  real API responses and MockWebServer.
- **`:app`** — Android. Compose UI, ViewModels, navigation, session storage
  (DataStore), image loading (Coil), theme.

Versions follow BushLines' proven stack: AGP 8.10.1, Kotlin 2.1.0, Gradle 8.11.1,
Compose BOM 2024.12.01, lifecycle 2.8.7, coroutines 1.9.0, serialization 1.7.3,
DataStore 1.1.1, OkHttp 4.12.0, Coil 2.7.0 (+ SVG, for the server's initials
avatars), Navigation Compose 2.8.5 with type-safe routes. minSdk 26, target 36.
No DI framework: one `AppContainer` built in the `Application`.

### Auth and transport

`POST /api/login` returns `session_id`; the app stores it in app-private
DataStore and sends `Authorization: Bearer <session_id>` on every request — the
documented contract for non-browser clients. Cookies are ignored. Backups are
disabled so the token never leaves the device. On start the app calls
`/api/check_session`; inactive → sign-in screen. Any `401` clears the session
and returns to sign-in with a note. Sign-out calls `/api/logout` (best effort)
and clears local state. Image requests go through the same OkHttp client, so
authenticated images (exchange banner, receipt photos) load too.

### Navigation

Bottom bar: **Trail · Openings · Communities · Inbox · Me**. Search is a
top-bar action. Pushed screens: Opening, New opening, Exchange, Entity
(sphere/alliance/project), Person, Search; a value card opens as a bottom
sheet. Server links such as `/opening?id=…` (notifications, search results)
map to these routes in `core/Links`; anything unknown opens in the browser.

### Data flow

ViewModels call `LogoSphereApi` and expose one `StateFlow<UiState>` per screen
(loading / error-with-retry / content). Lists the app needs in several places
(spheres, alliances, projects, openings) sit behind a small in-memory
repository with a 30-second freshness window — the same role TanStack Query
plays in the web client. Mutations re-fetch the affected screen; failures show
the server's `message` in a snackbar.

### Rules that differ from the web on purpose

The app mirrors the backend's guards rather than the web's, where the two
disagree, so it never offers an action the server will reject:

- An exchange only offers *Initiated → In Progress → Finished*; *Receipted* is
  reached by adding the receipt (the web shows a "Mark as Receipted" button the
  server answers with 409).
- *Cancel exchange* only while Initiated or In Progress.
- *Accept* is offered unless the opening is Completed, Cancelled, a past
  version, or a one-time opening already In Progress.
- *Withdraw* follows the same guard as the server's `cancel_service`; on
  someone else's opening it reads "Withdraw (platform admin)", because it
  withdraws the opening for everyone.
- *Take back my acceptance* is offered while your acceptance is pending (the
  server's `reject_service`, called from the accepting side).

### Look

The web's "solarpunk / organic trust" tokens become the Material 3 colour
scheme: linen paper background, moss primary, terracotta accent, honey
secondary; Fraunces for display type and Hanken Grotesk for body, bundled as
variable fonts (SIL OFL, licences included). A dark scheme is derived from the
same palette. Entities without a banner get the web's per-kind gradient and
glyph (✦ sphere, ◈ alliance, ◻ project, ◍ opening).

## Error handling

- Network failure → inline error state with Retry; pull-to-refresh everywhere.
- `401` → session cleared, sign-in screen, "Your session ended" note.
- `4xx` with `{"message"}` → shown verbatim (the API's messages are written for people).
- Dates arrive as ISO-8601 without zone (UTC) or RFC 1123; `Dates` parses both.

## Testing

- `:core` unit tests: every fixture recorded from the real API decodes; the
  opening/exchange rules; link routing; date parsing; the client against
  MockWebServer (bearer header, error envelope, 401).
- `:app`: `assembleDebug` and lint; then the debug build on a phone, driven
  over adb, signed in by the phone's owner (the assistant does not enter
  passwords on the production site).
