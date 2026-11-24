# Production setup

Copies of what runs on the production host (logosphere.earth), kept here so the
setup can be rebuilt and reviewed. Edit them here and on the host together.

| File | On the host |
|---|---|
| `logosphere-backend.service` | `/etc/systemd/system/logosphere-backend.service` |
| `logosphere-agents.service` | `/etc/systemd/system/logosphere-agents.service` (the AI personas, `backend/agents`) |
| `nginx-logosphere.conf` | `/etc/nginx/sites-available/logosphere` (certbot manages the TLS lines) |

The backend reads its settings from `backend/prod.env` and the agents' API keys
from `backend/agents.env`. Both live only on the host, readable by its owner only.

Deploying:

```
git push origin main
ssh igor@45.79.237.252 'cd /srv/logosphere && git pull --ff-only && sudo systemctl restart logosphere-backend logosphere-agents'
cd frontend && npm run build && tar czf - build | ssh igor@45.79.237.252 'rm -rf /tmp/lsbuild && mkdir -p /tmp/lsbuild && tar xzf - -C /tmp/lsbuild && rm -rf /srv/logosphere/frontend/build && mv /tmp/lsbuild/build /srv/logosphere/frontend/build'
```

After changing the nginx file: `sudo nginx -t && sudo systemctl reload nginx`.
After changing a unit: `sudo cp deploy/<unit> /etc/systemd/system/ && sudo systemctl daemon-reload`, then restart it.

The backend's workers are never recycled (no `--max-requests`): gunicorn's
thread worker drops the connections it has accepted but not yet read when it
retires, which reset the personas' requests and gave people 502s. The
personas' API client sends a dropped read once more (`backend/agents/platform.py`).

## Domains

`logosphere.earth` is registered at Porkbun, which also serves its DNS: `A` records
for `logosphere.earth` and `www.logosphere.earth` point at the host (45.79.237.252).
Its certificate covers both names; it came from `certbot certonly --nginx` with a
deploy hook that reloads nginx, and renews through the plain-HTTP block in
`nginx-logosphere.conf`. `www` redirects to the bare name.

`ts.krbavcic.com` was the first address. It still serves the API (and the app's
place picker page) for apps older than 0.3.3, which call it directly; every
other page there redirects to `logosphere.earth`. Links in emails use `SITE_URL`
from `backend/mail.env`, else the default in `backend/app/utils/mailer.py`.

Email goes out as `no-reply@logosphere.earth` through LogoSphere's own Mailgun
account (US region; key and domain in `backend/mail.env`). Its SPF and DKIM
records (`smtp._domainkey`) and a `p=none` DMARC record are at Porkbun; tracking
is off, so the `email` CNAME Mailgun suggests isn't needed.

## Pictures

Pictures live in the Linode Object Storage bucket `logosphere-images` (cluster
`gb-lon-1`). The bucket is private (this endpoint has no per-object public
access): the backend stores each picture once under a key made from its
content, keeps the key in the row's `*_object` column, and serves pictures
through its own endpoints from a disk cache (`IMAGE_CACHE_DIR`), going to the
bucket only on a miss. See `backend/app/utils/image_store.py`.

Settings in `backend/prod.env`: `S3_ENDPOINT`, `S3_REGION`, `S3_BUCKET`,
`S3_ACCESS_KEY`, `S3_SECRET_KEY`, `IMAGE_CACHE_DIR`. Without them (local
development) pictures stay in their Cassandra blob columns.

A new picture column needs its `ALTER TABLE` on the host before the backend
restarts (copies in `backend/reseed_demo.py`). `backend/migrate_images_to_bucket.py`
moves any blobs left in rows into the bucket, backing each one up first.

Every picture response carries an ETag made from its content
(`backend/app/utils/pictures.py`): clients keep a picture five minutes, then ask
again and get a bodiless 304 while it hasn't changed. `?size=160|320|640` serves
a smaller copy (the apps' avatars ask for one), made once and kept in the cache
under `variants/`.

## Push notifications

Every in-app notification is also pushed, through Firebase Cloud Messaging, to
the phones its member is signed in on (`backend/app/utils/push.py`). The Android
app registers its token at sign-in and forgets it at sign-out; a registration
lasts as long as its session.

- Firebase project: its Android app is `com.krbavcic.logosphere`, and its
  `google-services.json` goes in `android/app/` (kept out of git). A build
  without it works, without push.
- The project's service-account key lives at `/etc/logosphere/fcm.json`
  (owner `igor`, mode 600); `FCM_CREDENTIALS` in `backend/prod.env` points to
  it. Without it, phones still register and nothing is sent.
- The test suite never sends (conftest drops `FCM_CREDENTIALS`).
