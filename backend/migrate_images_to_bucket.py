"""Move every stored picture out of its Cassandra blob into the bucket.

    cd backend && set -a && . ./prod.env && set +a && .venv/bin/python migrate_images_to_bucket.py [--dry-run]

Each blob is backed up to IMAGE_BACKUP_DIR (once; default
~/backups/images-<today>), stored through app/utils/image_store
(turned upright, scaled down and re-encoded when large), its key written to
the row's *_object column, and the blob cleared. A row already moved has no
blob, so running it again does nothing. Run after the ALTER TABLEs that add
the *_object columns (see reseed_demo.py).
"""
import os
import sys
from datetime import date

import reactor  # noqa: F401  - the driver's event loop, before anything touches Cassandra
from app.db import session as db
from app.utils import image_store

BACKUP_DIR = os.environ.get('IMAGE_BACKUP_DIR') or os.path.expanduser(f'~/backups/images-{date.today():%Y%m%d}')
TABLES = [
    # table, key columns, blob column, object column, kind
    ('services', ('service_id',), 'image', 'image_object', 'banner'),
    ('spheres', ('sphere_id',), 'image', 'image_object', 'banner'),
    ('alliances', ('alliance_id',), 'image', 'image_object', 'banner'),
    ('projects', ('project_id',), 'image', 'image_object', 'banner'),
    ('meaning_trail', ('user_id', 'exchange_id'), 'exchange_image', 'exchange_image_object', 'banner'),
    ('receipt_photos', ('exchange_id', 'idx'), 'image', 'image_object', 'photo'),
    ('users', ('user_id',), 'profile_picture', 'picture_object', 'avatar'),
]


def _ext(data):
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        return 'png'
    if data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        return 'webp'
    if data[:6] in (b'GIF87a', b'GIF89a'):
        return 'gif'
    return 'jpg'


def main(dry_run):
    if not image_store.enabled():
        sys.exit('No bucket configured: set the S3_* settings first.')
    os.makedirs(BACKUP_DIR, exist_ok=True)
    moved = before = after = 0
    for table, keys, blob_col, obj_col, kind in TABLES:
        where = ' AND '.join(f'{k} = %s' for k in keys)
        for r in list(db.execute(f'SELECT {", ".join(keys)}, writetime({blob_col}) AS wt FROM {table}')):
            if r.wt is None:
                continue
            ids = [getattr(r, k) for k in keys]
            row = db.execute(f'SELECT {blob_col} FROM {table} WHERE {where}', ids).one()
            blob = getattr(row, blob_col, None) if row else None
            if not blob:
                continue
            body, ctype = image_store.normalise(blob, kind)
            name = f"{table}-{'-'.join(str(i) for i in ids)}"
            print(f'{name}: {len(blob) // 1024} KB -> {len(body) // 1024} KB ({ctype})')
            moved, before, after = moved + 1, before + len(blob), after + len(body)
            if dry_run:
                continue
            if not any(f.startswith(name + '.') for f in os.listdir(BACKUP_DIR)):
                with open(os.path.join(BACKUP_DIR, f'{name}.{_ext(blob)}'), 'wb') as fh:
                    fh.write(blob)
            obj, _ = image_store.store(blob, kind)
            db.execute(f'UPDATE {table} SET {obj_col} = %s, {blob_col} = null WHERE {where}', [obj] + ids)
    print(f"{'Would move' if dry_run else 'Moved'} {moved} pictures: {before // 1024} KB -> {after // 1024} KB")


if __name__ == '__main__':
    main('--dry-run' in sys.argv)
    sys.stdout.flush()
    os._exit(0)     # the driver's threads would otherwise keep the process alive
