"""One-off (2026-11-25): the demo personas get their near-miss names (agents/renames.py) all
through the database. Every text value in the keyspace, collections too, that holds an old full
name or sign-in address is rewritten: the users rows themselves, and every copy made since (names
kept beside notifications, words in openings, messages, acknowledgements, the personas' memory).
A cell keeps the time to live it had; a row whose key changes is copied under the new key and the
old one deleted. Dry run unless --apply. Pause the personas first and back the keyspace up.

  cd backend && set -a && . ./prod.env && set +a
  .venv/bin/python -m agents.rename_personas [--apply]
"""
import sys
from collections import Counter

import reactor  # noqa: F401 - picks the driver's event loop before it loads

from app.db import session as db  # noqa: E402
from agents.renames import renamed  # noqa: E402

KEYSPACE = 'logosphere'
APPLY = '--apply' in sys.argv
TEXT = ('text', 'varchar', 'ascii')


def changed(value):
    """The value with the new names, or None when nothing in it changes."""
    if isinstance(value, str):
        new = renamed(value)
    elif isinstance(value, (list, tuple)):
        new = [renamed(v) for v in value]
        new = new if new != list(value) else None
        return new
    elif isinstance(value, (set, frozenset)):
        new = {renamed(v) for v in value}
        return new if new != set(value) else None
    elif isinstance(value, dict):
        new = {renamed(k): renamed(v) for k, v in value.items()}
        return new if new != dict(value) else None
    else:
        return None
    return new if new != value else None


def text_like(cql_type):
    return cql_type in TEXT or any(cql_type.startswith(f'{c}<') and 'text' in cql_type for c in ('list', 'set', 'map'))


def main():
    tables = sorted(r.table_name for r in db.execute(
        'SELECT table_name FROM system_schema.tables WHERE keyspace_name = %s', [KEYSPACE]))
    total = Counter()
    for table in tables:
        cols = list(db.execute('SELECT column_name, kind, type FROM system_schema.columns '
                               'WHERE keyspace_name = %s AND table_name = %s', [KEYSPACE, table]))
        if any(c.type == 'counter' for c in cols):
            continue
        watched = [c.column_name for c in cols if text_like(c.type)]
        if not watched:
            continue
        keys = [c.column_name for c in cols if c.kind in ('partition_key', 'clustering')]
        partition = [c.column_name for c in cols if c.kind == 'partition_key']
        static = {c.column_name for c in cols if c.kind == 'static'}
        # A cell's time to live, for plain columns only: TTL() of a collection gives a list per
        # element, which this driver can't decode when they have none (the case here).
        regular = [c.column_name for c in cols if c.kind == 'regular' and c.type in TEXT]
        for row in db.execute(f'SELECT * FROM {KEYSPACE}.{table}'):
            row = row._asdict()
            new = {c: changed(row[c]) for c in watched}
            new = {c: v for c, v in new.items() if v is not None}
            if not new:
                continue
            total[table] += 1
            sample = next(iter(new.items()))
            print(f'{table}: {", ".join(new)}  e.g. {sample[0]} -> {str(sample[1])[:90]!r}')
            if not APPLY:
                continue
            where = ' AND '.join(f'{k} = %s' for k in keys)
            if any(c in keys for c in new):
                # A key changes (an address used as a key): the row moves.
                full = {**row, **new}
                names = list(full)
                db.execute(f'INSERT INTO {KEYSPACE}.{table} ({", ".join(names)}) VALUES ({", ".join(["%s"] * len(names))})',
                           [full[n] for n in names])
                db.execute(f'DELETE FROM {KEYSPACE}.{table} WHERE {where}', [row[k] for k in keys])
                continue
            for column, value in new.items():
                ttl = None
                if column in regular:
                    ttl = db.execute(f'SELECT TTL({column}) AS t FROM {KEYSPACE}.{table} WHERE {where}',
                                     [row[k] for k in keys]).one().t
                using = f' USING TTL {int(ttl)}' if ttl else ''
                # A static column belongs to the whole partition, so only its key may be named.
                by = partition if column in static else keys
                db.execute(f'UPDATE {KEYSPACE}.{table}{using} SET {column} = %s WHERE '
                           + ' AND '.join(f'{k} = %s' for k in by), [value] + [row[k] for k in by])
    print('\nrows', 'rewritten' if APPLY else 'to rewrite (dry run)', dict(total), 'in all', sum(total.values()))


if __name__ == '__main__':
    main()
