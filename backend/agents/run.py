"""Entry point for logosphere-agents.service.

  cd backend && set -a && . ./prod.env && . ./agents.env && set +a
  .venv/bin/python -m agents.run            # the loop
  .venv/bin/python -m agents.run --once     # one cycle, then exit
  .venv/bin/python -m agents.run --status   # queue, today's usage, recent log
"""
import logging
import os
import sys
import time
from datetime import datetime

import reactor  # noqa: F401 - picks the driver's event loop before it loads

from agents import config, store  # noqa: E402


def status():
    used = store.usage_today()
    print(f"enabled={config.ENABLED} dry_run={config.DRY_RUN} paused={store.paused()}")
    print(f"queued: {store.pending_count()}")
    print(f"today: {used['actions']} actions, {used['claude_calls']} Claude calls "
          f"({used['claude_in']} in / {used['claude_out']} out tokens), {used['images']} images")
    day = datetime.utcnow().strftime('%Y-%m-%d')
    rows = list(store.db.execute('SELECT at, action, detail FROM agent_log WHERE day = %s', [day]))
    for r in rows[-15:]:
        print(f'  {r.at:%H:%M} {r.action}: {r.detail}')


def main():
    logging.basicConfig(level=os.environ.get('AGENTS_LOG_LEVEL', 'INFO'),
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')
    for noisy in ('cassandra', 'httpx', 'httpx2', 'anthropic', 'openai'):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    store.ensure_tables()
    if '--status' in sys.argv:
        status()
        return
    if not config.ENABLED:
        logging.getLogger('agents').info('AGENTS_ENABLED is off; nothing to do')
        return
    from agents.director import Director
    director = Director()
    logging.getLogger('agents').info('Director started: %d personas, dry_run=%s', len(director.personas), config.DRY_RUN)
    while True:
        try:
            director.cycle()
        except Exception:
            logging.getLogger('agents').exception('Cycle failed')
        if '--once' in sys.argv:
            return
        time.sleep(config.POLL_SECONDS)


if __name__ == '__main__':
    main()
    sys.stdout.flush()
    os._exit(0)
