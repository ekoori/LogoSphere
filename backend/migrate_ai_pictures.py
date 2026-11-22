"""Remember the AI pictures made before pictures were remembered (2026-11-22).

The five 1080x720 banners drawn with agents/images.py on 2026-11-19: one
persona's post and four redrawn demo pictures. Remembering them is what
labels them, and keeps them out of evidence in real spheres (demo spheres'
evidence may be AI-made, so nothing disappears).

Idempotent; changes no picture and no row that points at one.

  cd backend && set -a && . ./prod.env && set +a
  .venv/bin/python migrate_ai_pictures.py            # says what it would do
  .venv/bin/python migrate_ai_pictures.py --apply
"""
import os
import sys

import reactor  # noqa: F401 - picks the driver's event loop before it loads

from app.utils import ai_pictures, image_store  # noqa: E402

DRAWN = {
    'banners/5316ecbe1c8a2468851c453cdc38c2bc.jpg': "a persona's offer to sort sheds",
    'banners/e80bee5a9ed3346075123644b3972a77.jpg': 'podcast workshop (an opening and its exchange)',
    'banners/fe01e54f1a3e375fc476b196c29136e3.jpg': 'fence rebuild (an exchange)',
    'banners/3e258d82ca1df1bf18acb00554db7c9e.jpg': 'Repair Cafe (an alliance)',
    'banners/f40817414d5897e442570126b0ed8f4c.jpg': 'Solar Microgrid (a project)',
}


def main(apply):
    if apply:
        ai_pictures.ensure_tables()
    for key, what in DRAWN.items():
        data = image_store.load(key)
        if not data:
            print(f'  missing     {key}  {what}')
            continue
        if apply:
            if ai_pictures.is_ai_key(key):
                print(f'  known       {key}  {what}')
                continue
            ai_pictures.remember(data, 'backfill', key)
        print(f"  {'remembered' if apply else 'would add ':10}  {key}  {what}")


if __name__ == '__main__':
    main('--apply' in sys.argv[1:])
    sys.stdout.flush()
    os._exit(0)
