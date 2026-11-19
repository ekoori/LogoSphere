# Production setup

Copies of what runs on the production host (ts.krbavcic.com), kept here so the
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
