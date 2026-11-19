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
