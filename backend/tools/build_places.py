"""Builds the offline place search (app/utils/gazetteer.py) from GeoNames' free data.

It downloads nothing. Give it the folder holding the files as GeoNames ships
them (https://download.geonames.org/export/, CC BY 4.0); zips are read without
being unpacked:

  cities500.zip              every town over 500 people (required)
  countryInfo.txt            countries (required)
  admin1CodesASCII.txt       states and regions
  admin2Codes.txt            districts, for telling namesakes apart
  <CC>.zip                   a whole country, for its suburbs and hamlets (AU.zip)
  postcodes.zip              export/zip/allCountries.zip, renamed

  python -I build_places.py <folder> <places.sqlite>

Regions and countries take the spot of their most populous town: GeoNames'
code files give them no coordinates, and that is where most of their people are.
"""
import re
import sqlite3
import sys
import unicodedata
import zipfile
from pathlib import Path

SCHEMA = """
CREATE TABLE place (
  id INTEGER PRIMARY KEY, kind TEXT NOT NULL, name TEXT NOT NULL, lowered TEXT NOT NULL, label TEXT NOT NULL,
  lat REAL NOT NULL, lon REAL NOT NULL, population INTEGER NOT NULL);
CREATE VIRTUAL TABLE place_fts USING fts5(terms, content='', tokenize='unicode61 remove_diacritics 2', prefix='2 3');
"""
COUNTRY_ZIP = re.compile(r'^[A-Z]{2}\.zip$')
WORD = re.compile(r'[^\W_]+')


def lines(path):
    """A file's data lines, from inside its zip where that's what it is."""
    if path.suffix == '.zip':
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.endswith('.txt') and n.lower() != 'readme.txt']
            if len(names) != 1:
                raise SystemExit(f'{path.name}: expected one data file, found {names}')
            with z.open(names[0]) as fh:
                for raw in fh:
                    yield from _line(raw.decode('utf-8'))
    else:
        with path.open(encoding='utf-8') as fh:
            for raw in fh:
                yield from _line(raw)


def _line(text):
    text = text.rstrip('\r\n')
    if text and not text.startswith('#'):
        yield text.split('\t')


def optional(folder, name):
    path = folder / name
    return lines(path) if path.is_file() else iter(())


def label_of(*parts):
    out = []
    for part in parts:
        if part and (not out or part != out[-1]):
            out.append(part)
    return ', '.join(out)


def lowered(name):
    """As a search is compared: words, lower case, single spaces."""
    plain = ''.join(c for c in unicodedata.normalize('NFKD', name.lower()) if not unicodedata.combining(c))
    return ' '.join(WORD.findall(plain))


class Writer:
    def __init__(self, db):
        self.db = db
        self.next_id = 0

    def add(self, kind, name, label, lat, lon, population, *also):
        self.next_id += 1
        self.db.execute('INSERT INTO place VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
                        [self.next_id, kind, name, lowered(name), label, lat, lon, population])
        self.db.execute('INSERT INTO place_fts (rowid, terms) VALUES (?, ?)',
                        [self.next_id, ' '.join(p for p in (name, label) + also if p)])


def build(folder, out):
    folder, out = Path(folder), Path(out)
    countries = {c[0]: c[4] for c in lines(folder / 'countryInfo.txt') if len(c) > 4}
    admin1 = {r[0]: r[1] for r in optional(folder, 'admin1CodesASCII.txt') if len(r) > 1}
    admin2 = {r[0]: r[1] for r in optional(folder, 'admin2Codes.txt') if len(r) > 1}

    out.parent.mkdir(parents=True, exist_ok=True)
    fresh = out.with_name(out.name + '.new')
    fresh.unlink(missing_ok=True)
    db = sqlite3.connect(fresh)
    db.executescript(SCHEMA)
    write = Writer(db)

    seen = set()
    biggest = {}            # 'AU' or 'AU.07' -> (population, lat, lon)
    extra = sorted(p for p in folder.glob('*.zip') if COUNTRY_ZIP.match(p.name))
    for path in [folder / 'cities500.zip', *extra]:
        for r in lines(path):
            if len(r) < 15 or r[6] != 'P' or r[0] in seen or r[7] in ('PPLH', 'PPLQ', 'PPLW'):
                continue        # not a populated place, or one that's gone
            seen.add(r[0])
            name, ascii_name, other_names = r[1], r[2], r[3]
            lat, lon, country, code1, code2 = float(r[4]), float(r[5]), r[8], r[10], r[11]
            people = int(r[14] or 0)
            first = admin1.get(f'{country}.{code1}', '')
            second = admin2.get(f'{country}.{code1}.{code2}', '') if code2 else ''
            write.add('town', name, label_of(name, second, first, countries.get(country, country)),
                      lat, lon, people, ascii_name, other_names.replace(',', ' ')[:600])
            for key in (country, f'{country}.{code1}'):
                if key not in biggest or people > biggest[key][0]:
                    biggest[key] = (people, lat, lon)

    for code, name in admin1.items():
        if code in biggest:
            people, lat, lon = biggest[code]
            write.add('region', name, label_of(name, countries.get(code.split('.')[0], '')), lat, lon, people)
    for code, name in countries.items():
        if code in biggest:
            people, lat, lon = biggest[code]
            write.add('country', name, name, lat, lon, people, code)

    posts = set()
    for r in optional(folder, 'postcodes.zip'):
        if len(r) < 11 or not r[9] or not r[10]:
            continue
        key = (r[0], r[1], r[2])
        if key in posts:
            continue
        posts.add(key)
        name = f'{r[1]} {r[2]}'.strip()
        write.add('postcode', name, label_of(name, r[3], countries.get(r[0], r[0])), float(r[9]), float(r[10]), 0)

    db.execute('CREATE INDEX place_spot ON place (lat, lon)')
    db.commit()
    db.execute('VACUUM')
    db.close()
    fresh.replace(out)
    return write.next_id


if __name__ == '__main__':
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    print(f'{build(sys.argv[1], sys.argv[2])} places in {sys.argv[2]}')
