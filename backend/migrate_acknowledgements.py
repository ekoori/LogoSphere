"""Move the single acknowledgement slot on exchanges (meaning_trail.other_comment)
into trail_acknowledgements, with its likes, and empty the slot. Safe to re-run.

  cd backend && set -a && . ./prod.env && set +a
  .venv/bin/python migrate_acknowledgements.py [--dry-run]
"""
import json
import os
import sys
import uuid
from datetime import datetime

import reactor  # noqa: F401 - picks the driver's event loop before it loads

from app.db import session  # noqa: E402
from app.models.acknowledgement import LIKE, Acknowledgement, ensure_tables  # noqa: E402

CLEAR = ('UPDATE meaning_trail SET other_comment = null, other_comment_id = null, '
         'other_comment_author_id = null, other_comment_author_name = null, '
         'other_comment_timestamp = null, other_comment_cards = null '
         'WHERE user_id = %s AND exchange_id = %s')


def main(dry_run):
    ensure_tables()
    moved = 0
    rows = session.execute(
        'SELECT user_id, exchange_id, other_comment, other_comment_id, other_comment_author_id, '
        'other_comment_author_name, other_comment_timestamp, other_comment_cards, project_start_timestamp '
        'FROM meaning_trail')
    for r in list(rows):
        if not r.other_comment:
            continue
        ack_id = r.other_comment_id or uuid.uuid5(r.exchange_id, 'acknowledgement')
        at = r.other_comment_timestamp or r.project_start_timestamp or datetime(2026, 1, 1)
        try:
            cards = json.loads(r.other_comment_cards) if r.other_comment_cards else []
        except ValueError:
            cards = []
        likers = [x.user_id for x in session.execute(
            "SELECT user_id FROM likes WHERE exchange_id = %s AND comment_type = 'other'", [r.exchange_id])]
        print(f"{'would move' if dry_run else 'moving'} one on exchange {r.exchange_id} ({len(likers)} likes)")
        moved += 1
        if dry_run:
            continue
        if not Acknowledgement.find(r.exchange_id, ack_id):
            Acknowledgement.create(r.exchange_id, r.other_comment_author_id, r.other_comment_author_name,
                                   r.other_comment, cards, ack_id=ack_id, created_at=at)
        for person in likers:
            session.execute('INSERT INTO likes (exchange_id, comment_type, user_id) VALUES (%s, %s, %s)',
                            [ack_id, LIKE, person])
        session.execute("DELETE FROM likes WHERE exchange_id = %s AND comment_type = 'other'", [r.exchange_id])
        session.execute(CLEAR, [r.user_id, r.exchange_id])
    print(f'{moved} acknowledgement(s)')


if __name__ == '__main__':
    main('--dry-run' in sys.argv)
    sys.stdout.flush()
    os._exit(0)
