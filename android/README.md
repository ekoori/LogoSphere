# LogoSphere for Android

A native Android client for LogoSphere — Kotlin, Jetpack Compose and Material 3 — that talks to the
same API as the web app (`https://ts.krbavcic.com` by default). Design notes:
[`docs/plans/2026-11-18-android-client-design.md`](../docs/plans/2026-11-18-android-client-design.md)
(the first version) and
[`docs/plans/2026-11-20-android-parity.md`](../docs/plans/2026-11-20-android-parity.md) (everything
else the web does).

## What it does

Everything the website does, apart from the public sphere page for signed-out visitors:

- **Trail** — your Meaning Trail, your own openings, the people you follow.
- **Openings** — browse offers and needs (by type and sphere), post one (as yourself or for a group
  you manage), like, accept (as yourself or as an alliance/project you manage), confirm or decline
  acceptances, withdraw; edit one (a new version once an exchange links to it) and set its picture.
- **Exchange** — status timeline and actions, receipts (Frankl mode, value cards, context, up to
  three photos), the initiator's note, follow-ups, acknowledgements, likes; edit its title,
  description and banner until it's finished.
- **Communities** — spheres, alliances and projects: start one, join, their trail, openings,
  people, charter; **governance** (policies, lending your vote, proposals and voting); and for
  managers a console — settings and policies, banner, the group's Meaning Graph, approving
  requests and setting roles.
- **People** — profiles, values, trails; follow and unfollow; copy someone's value card onto your
  graph or a group's.
- **Me** — your Meaning Graph (write, edit, endorse, review, remove cards), your profile and photo,
  the information pages (About, How it works, Contribute, Donate, Privacy, Terms).
- **Inbox** — notifications with an unread badge; tapping one opens what it's about.
- **Search** — text search and "near my values".
- **Platform administration** — for platform admins: overview, users, spheres, alliances,
  projects and openings.

## Layout

| Module | What |
|---|---|
| `core` | Plain Kotlin/JVM: API models, the HTTP client (`LogoSphereApi`, OkHttp + kotlinx.serialization), and the rules screens ask (`OpeningRules`, `ExchangeRules`, `Membership`, `Roles`, `Policies`, `Links`, `Dates`). |
| `app` | The Android app: Compose screens and ViewModels, navigation, session storage (DataStore), images (Coil). |

The rules in `core` follow the backend's guards (`backend/app/routes/openings.py`,
`meaning_trail.py`), so the app only offers actions the server will accept.

## Build and run

Needs JDK 17+ (21 works) and the Android SDK (platform 36). From this folder:

```
./gradlew :core:test            # JVM tests: models against recorded API responses, rules, client
./gradlew :app:assembleDebug    # app/build/outputs/apk/debug/app-debug.apk
./gradlew :app:installDebug     # onto a connected phone (USB debugging on)
```

`core/src/test/resources/fixtures` holds real API responses (demo seed data) recorded from the
backend; when the API changes, re-record them so the decode tests keep the app honest.

For a manual pass on a USB-connected phone, `tools/droid.py` taps, types and reads the screen by
label over adb (`python tools/droid.py` lists its commands). Writes made while testing against a
shared server can be undone with the backend's `tools/keyspace_guard.py` (dump before, diff and
restore after).

### Pointing a debug build at another server

Debug builds show a **Server** field on the sign-in screen — e.g. `http://10.0.2.2:5000` for a local
backend from an emulator, or `http://127.0.0.1:5000` on a phone after `adb reverse tcp:5000 tcp:5000`.
Debug builds allow plain HTTP for this; release builds are HTTPS-only and always use
`DEFAULT_SERVER_URL` (in `app/build.gradle.kts`).

### Release signing

A release build is signed with the key named by the Gradle properties `logosphereKeystore` and
`logosphereKeystorePassword` (in `~/.gradle/gradle.properties`, never in the repository) or the
`LOGOSPHERE_KEYSTORE*` environment variables; without them it falls back to the debug key.

## Auth

`POST /api/login` returns a session token; the app keeps it in app-private storage (backups are
off) and sends `Authorization: Bearer <token>` — the API's documented contract for non-browser
clients. A `401` on any request returns to sign-in.

## Fonts

Fraunces and Hanken Grotesk, the web app's typefaces, are bundled as variable fonts under the SIL
Open Font License 1.1 (texts in `app/src/main/assets/licenses`).
