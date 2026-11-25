"""One-off (2026-11-26): every AI persona gets a random password that nobody keeps. Their old ones
were each one's first name, written in the repo's seeds and tests, so anyone could sign in as a
persona on production, read the conversations members had with it and act for it in the demo
spheres. Personas never sign in by password: the director mints their sessions (agents/store.py)
and so does the test suite (conftest.py). Sessions are left as they are. Dry run unless --apply.

  cd backend && set -a && . ./prod.env && set +a
  .venv/bin/python -m agents.lock_persona_logins [--apply]
"""
import secrets
import sys
import uuid

import reactor  # noqa: F401 - picks the driver's event loop before it loads

from werkzeug.security import check_password_hash, generate_password_hash  # noqa: E402

from app.db import session as db  # noqa: E402
from agents.personas import load  # noqa: E402

APPLY = '--apply' in sys.argv
OLD_FIRST_NAMES = {'Jo Rodan': 'Joe'}   # the seeds' passwords kept the first names from before the renames


def main():
    locked = 0
    for persona in load():
        uid = uuid.UUID(str(persona.user_id))
        row = db.execute('SELECT password FROM user_credentials WHERE user_id = %s', [uid]).one()
        if not row:
            print(f'{persona.name}: no password at all')
            continue
        first = persona.name.split()[0]
        guesses = {first, first.lower(), OLD_FIRST_NAMES.get(persona.name, first)}
        guessable = any(check_password_hash(row.password, guess) for guess in guesses)
        if APPLY:
            db.execute('UPDATE user_credentials SET password = %s WHERE user_id = %s',
                       [generate_password_hash(secrets.token_urlsafe(32)), uid])
            locked += 1
        print(f'{persona.name}: {"was its first name" if guessable else "not a first name"}'
              f'{" -> locked" if APPLY else ""}')
    print('locked', locked, 'of', len(load()) if APPLY else '(dry run)')


if __name__ == '__main__':
    main()
