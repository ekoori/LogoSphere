# Developing LogoSphere

How LogoSphere is built, how to run it on your own computer, and how changes are tested and
released. For what LogoSphere is, see the [README](README.md).

## What it's built with

| Part | Stack | Where |
|---|---|---|
| Server | Python, Flask 3, cassandra-driver; gunicorn in production | [`backend/`](backend/) |
| Database | Apache Cassandra **5.0** (the schema uses 5.0-only options) | [`database/schema.cql`](database/schema.cql) |
| Website | React 18, built with Vite 5, TanStack Query | [`frontend/`](frontend/) |
| Android app | Kotlin, Jetpack Compose, Material 3 | [`android/`](android/README.md) |
| API | OpenAPI description of every route | [`LogoSphereAPI.yaml`](LogoSphereAPI.yaml) |
| AI personas | The demo spheres' director, writing with Claude | [`backend/agents/`](backend/agents/) |
| Production | nginx, systemd units, how to deploy | [`deploy/`](deploy/README.md) |

The vocabulary (value cards, receipts, the Meaning Trail…) is defined in
[MANIFESTO.md](MANIFESTO.md); design notes and plans are in [`docs/`](docs/).

## Requirements

- **Python** 3.12 or newer (production runs 3.12).
- **Node.js** 18 or newer.
- **Cassandra 5.0**, most easily in Docker or Podman.
- **For the Android app:** JDK 17 and the Android SDK (Android Studio brings both).

## Run it locally

1. **Cassandra.** Start Cassandra 5.0 and load the schema:

   ```
   docker run -d --name cassandra -p 9042:9042 cassandra:5.0
   docker cp database/schema.cql cassandra:/schema.cql
   docker exec cassandra cqlsh -f /schema.cql
   ```

   Give it a minute to accept connections first. The schema's one materialized view fails where
   materialized views are off (Cassandra's default); nothing uses it, so that error can be
   ignored. For demo data, see `backend/reseed_demo.py`: use it on a local database only, as it
   drops and refills the demo tables.
2. **Server.** From `backend/`:

   ```
   python -m venv .venv
   .venv/Scripts/pip install -r requirements.txt      # .venv/bin/pip on Linux and macOS
   CASSANDRA_HOST=127.0.0.1 PYTHONPATH=. .venv/Scripts/python run_local.py
   ```

   It listens on port 5000. `backend/reactor.py` picks the Cassandra driver's event loop: libev
   where it is built (Linux), else gevent (Windows, where the driver's default loop is missing
   on Python 3.12+).
3. **Website.** From `frontend/`:

   ```
   npm install
   npm start
   ```

   Vite serves it on port 3000 and passes `/api` to the server on 5000, so the session cookie
   stays first-party. `npm run build` writes `build/`, which nginx serves in production.
4. **Android app.** From `android/`: `./gradlew :app:installDebug` on a phone or emulator. Debug
   builds have a **Server** field on the sign-in screen for a local backend (see
   [android/README.md](android/README.md)).

## Tests

| Part | Command | Notes |
|---|---|---|
| Server | `cd backend && python -m pytest app/tests agents/tests` | Needs a Cassandra; the fixtures make and remove their own accounts. |
| Website | `cd frontend && npm test` | Vitest. `npm run lint` runs ESLint. |
| Android | `cd android && ./gradlew :core:test` | JUnit, including fixtures decoded from real API responses. |

Every route belongs in `LogoSphereAPI.yaml`; a test keeps the two in step.

## Releases

- **Version.** One place: `appVersion` in `android/app/build.gradle.kts`. The version code is
  derived from it (`MAJOR*10000 + MINOR*100 + PATCH`: 0.4.1 is 401), so it always rises.
- **Signing.** Release builds are signed with the upload key, which never enters the repository:
  the Gradle properties `logosphereKeystore` and `logosphereKeystorePassword` (in
  `~/.gradle/gradle.properties`) point at it. Without them a release build falls back to the debug
  key, which Google Play refuses, and Gradle says so.
- **GitHub.** `./gradlew :app:assembleRelease`, then a release tagged `vX.Y.Z` on `main` with the
  APK attached as `LogoSphere-X.Y.Z.apk`.
- **Google Play.** `./gradlew :app:bundleRelease` writes the bundle to upload. Everything the Play
  Console asks for is in [docs/play/README.md](docs/play/README.md).
- **Server and website.** Production runs committed `main`; see [deploy/README.md](deploy/README.md).

## Sending a change

Fork the repository, make your change on a branch with its tests, and open a pull request that
says what it changes and why. Small, careful changes are easiest to review. Words in the interface
are for people: say what happened and what to do next, in plain language.

LogoSphere is open source under the [MIT licence](LICENSE).
