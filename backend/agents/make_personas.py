"""One-off: draft personas.json - an everyday-neighbour sheet and a voice for
every persona account (users.is_agent), from their value cards, posts and
spheres. Review the file before committing it.

  cd backend && set -a && . ./prod.env && . ./agents.env && set +a
  .venv/bin/python -m agents.make_personas
"""
import os
import re
import sys

import reactor  # noqa: F401 - picks the driver's event loop before it loads

from app.db import session as db  # noqa: E402
from agents.personas import Persona, load, save  # noqa: E402
from agents.writer import Writer  # noqa: E402

PLACEHOLDER = re.compile(r'\[Bruce bulk|Generated seed|seed opening', re.I)


def main():
    known = {p.user_id: p for p in load()}
    spheres = list(db.execute('SELECT name, participants FROM spheres'))
    services = list(db.execute('SELECT provider_id, title, is_current FROM services'))
    writer = Writer()
    out = []
    for u in db.execute('SELECT user_id, name, surname, email, is_agent FROM users'):
        if not u.is_agent:
            continue
        uid = str(u.user_id)
        name = f"{u.name or ''} {u.surname or ''}".strip()
        if uid in known and known[uid].sheet and '--refresh' not in sys.argv:
            out.append(known[uid])
            continue
        cards = [{'card_id': str(c.card_id), 'title': c.title, 'care_about': c.care_about}
                 for c in db.execute('SELECT card_id, title, care_about, is_current FROM value_cards WHERE user_id = %s',
                                     [u.user_id]) if c.is_current is not False]
        posts = [s.title for s in services
                 if s.provider_id == u.user_id and s.is_current is not False and not PLACEHOLDER.search(s.title or '')]
        member_of = [s.name for s in spheres if s.participants and u.user_id in s.participants]
        drafted = writer.persona_sheet(name, cards, posts, member_of)
        if drafted is None:
            print(f'!! declined for {name}; skipped')
            continue
        persona = Persona(user_id=uid, name=name, email=u.email, sheet=drafted.sheet, voice=drafted.voice)
        out.append(persona)
        print(f'{name}\n  {persona.sheet}\n  voice: {persona.voice}\n', flush=True)
    save(out)
    print(f'wrote {len(out)} personas to agents/personas.json')


if __name__ == '__main__':
    main()
    sys.stdout.flush()
    os._exit(0)
