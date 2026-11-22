# Looking places up by name, offline: a SQLite file that backend/tools/build_places.py
# makes from GeoNames' free data (CC BY 4.0). Without the file there's no search
# and everything else about places still works (a pin, or the phone's location).
import os
import re
import sqlite3
import unicodedata
from contextlib import closing
from pathlib import Path

ATTRIBUTION = {'text': 'Place names: GeoNames, CC BY 4.0', 'url': 'https://www.geonames.org/'}
KINDS = ('town', 'postcode', 'region', 'country')       # each is also its precision
MOST = 12

_TOKEN = re.compile(r'[^\W_]+')


def plain(text):
    """As names are compared (the build tool does the same): no accents, no case."""
    return ''.join(c for c in unicodedata.normalize('NFKD', text.lower()) if not unicodedata.combining(c))


def path():
    return Path(os.environ.get('PLACES_DB') or Path(__file__).resolve().parents[2] / 'data' / 'places.sqlite')


def available():
    return path().is_file()


def _connect():
    db = sqlite3.connect(f'{path().as_uri()}?mode=ro', uri=True)
    db.row_factory = sqlite3.Row
    return closing(db)


def _out(row):
    return {'id': row['id'], 'name': row['name'], 'label': row['label'], 'precision': row['kind'],
            'lat': row['lat'], 'lon': row['lon']}


def get(place_id):
    if isinstance(place_id, bool) or not isinstance(place_id, int) or not available():
        return None
    with _connect() as db:
        row = db.execute('SELECT * FROM place WHERE id = ?', [place_id]).fetchone()
    return _out(row) if row else None


def search(text, near=None):
    """Best matches first: the name or whole postcode, then names starting so, then
    the bigger place, then the one nearer `near` (lat, lon): half the world has a 3000."""
    words = _TOKEN.findall(plain(str(text or '')))[:6]
    if not words or len(''.join(words)) < 2 or not available():
        return []
    match = ' '.join(f'"{word}"*' for word in words)        # quoted: never read as FTS syntax
    whole = ' '.join(words)
    order = ("(p.lowered = ? OR (p.kind = 'postcode' AND substr(p.lowered, 1, ?) = ?)) DESC, "
             '(substr(p.lowered, 1, ?) = ?) DESC, (substr(p.lowered, 1, ?) = ?) DESC, p.population DESC, ')
    values = [match, whole, len(whole) + 1, f'{whole} ', len(whole), whole, len(words[0]), words[0]]
    if near:
        order += '(p.lat - ?) * (p.lat - ?) + (p.lon - ?) * (p.lon - ?), '
        values += [near[0], near[0], near[1], near[1]]
    with _connect() as db:
        rows = db.execute(
            'SELECT p.* FROM place_fts JOIN place p ON p.id = place_fts.rowid '
            f'WHERE place_fts MATCH ? ORDER BY {order}p.id LIMIT ?',
            values + [MOST]).fetchall()
    return [_out(row) for row in rows]


def nearest(lat, lon, limit=3):
    """The towns about a point, nearest first: a name to offer for a pin."""
    if not available():
        return []
    with _connect() as db:
        rows = db.execute(
            'SELECT * FROM place WHERE lat BETWEEN ? AND ? AND lon BETWEEN ? AND ? AND kind = \'town\' '
            'ORDER BY (lat - ?) * (lat - ?) + (lon - ?) * (lon - ?), population DESC LIMIT ?',
            [lat - 0.3, lat + 0.3, lon - 0.4, lon + 0.4, lat, lat, lon, lon, limit]).fetchall()
    return [_out(row) for row in rows]
