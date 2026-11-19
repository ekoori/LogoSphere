"""Take off the likes people gave their own things. The like endpoints refuse
new ones; this clears the ones from before.

    cd backend && set -a && . ./prod.env && set +a && .venv/bin/python remove_self_likes.py [--dry-run]

An opening is its party's own (app/routes/openings._is_party: the provider,
whoever posted it for a group, the group's managers); an exchange's parts are
its sides' and authors' (app/models/meaning_trail.own_like_targets). Running it
again finds nothing.
"""
import os
import sys

import reactor  # noqa: F401  - the driver's event loop, before anything touches Cassandra
from app.db import session as db
from app.models.meaning_trail import MeaningTrail, own_like_targets
from app.models.openings import Service
from app.routes.openings import _is_party


def main(dry_run):
    names = MeaningTrail._name_map()
    removed = 0
    for r in list(db.execute('SELECT service_id, user_id FROM opening_likes')):
        service = Service.get_by_id(r.service_id)
        if service is None or not _is_party(service, r.user_id):
            continue
        print(f"opening {service.title!r}: {names.get(r.user_id, r.user_id)}")
        removed += 1
        if not dry_run:
            db.execute('DELETE FROM opening_likes WHERE service_id = %s AND user_id = %s', [r.service_id, r.user_id])
    for r in list(db.execute('SELECT exchange_id, comment_type, user_id FROM likes')):
        tx, is_initiator, is_other = MeaningTrail.get_for_view(r.exchange_id, r.user_id)
        if tx is None or r.comment_type not in own_like_targets(tx, r.user_id, is_initiator, is_other):
            continue
        print(f"exchange {tx.get('exchange_description')!r} ({r.comment_type}): {names.get(r.user_id, r.user_id)}")
        removed += 1
        if not dry_run:
            db.execute('DELETE FROM likes WHERE exchange_id = %s AND comment_type = %s AND user_id = %s',
                       [r.exchange_id, r.comment_type, r.user_id])
    print(f"{'Would take off' if dry_run else 'Took off'} {removed} likes of people's own things")


if __name__ == '__main__':
    main('--dry-run' in sys.argv)
    sys.stdout.flush()
    os._exit(0)     # the driver's threads would otherwise keep the process alive
