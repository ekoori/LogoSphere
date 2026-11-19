# LogoSphere for Android

A native Android client for LogoSphere — Kotlin, Jetpack Compose and Material 3 — that talks to the
same API as the web app (`https://ts.krbavcic.com` by default). Design notes:
[`docs/plans/2026-11-18-android-client-design.md`](../docs/plans/2026-11-18-android-client-design.md).

## What it does

- **Trail** — your Meaning Trail, your own openings, the people you follow.
- **Openings** — browse offers and needs (by type and sphere), post one, like, accept (as yourself
  or as an alliance/project you manage), confirm or decline acceptances, withdraw.
- **Exchange** — status timeline and actions, receipts (Frankl mode, value cards, context, photos),
  the initiator's note, follow-ups, acknowledgements, likes.
- **Communities** — spheres, alliances and projects: join, their trail, openings, people, charter.
- **People** — profiles, values, trails; follow and unfollow.
- **Inbox** — notifications with an unread badge; tapping one opens what it's about.
- **Search** — text search and "near my values".

Management, governance, value-card editing, image uploads and the admin console stay on the web;
the app links there.

## Layout

| Module | What |
|---|---|
| `core` | Plain Kotlin/JVM: API models, the HTTP client (`LogoSphereApi`, OkHttp + kotlinx.serialization), and the lifecycle rules (`OpeningRules`, `ExchangeRules`, `Membership`, `Links`, `Dates`). |
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
