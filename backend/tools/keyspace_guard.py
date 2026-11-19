#!/usr/bin/env python3
"""Dump, diff and restore the logosphere keyspace row by row, so a test run on
the shared database leaves its demo data exactly as it was.

Talks to Cassandra through cqlsh in the logosphere-cassandra container (no
Python driver needed). Rows are captured with SELECT JSON and put back with
INSERT ... JSON ... DEFAULT UNSET. Blob columns (images) are not dumped - their
writetime() is, so a rewritten blob still shows in the diff - and DEFAULT UNSET
leaves them untouched on restore.

Run on the host (needs passwordless sudo for docker):
  python3 keyspace_guard.py dump    <out.json>
  python3 keyspace_guard.py diff    <before.json> <after.json>
  python3 keyspace_guard.py restore <before.json> <after.json> [--skip t1,t2] [--only key,key] [--dry-run]
  python3 keyspace_guard.py clean-sessions <before.json> <after.json> <email,email>
"""
import json
import subprocess
import sys

KS = 'logosphere'
CQLSH = ['sudo', 'docker', 'exec', '-i', 'logosphere-cassandra', 'cqlsh', '--request-timeout=300']
WT = '__wt'  # suffix of a blob column's writetime alias


def cql_json_rows(query):
    result = subprocess.run(CQLSH + ['-e', query], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'cqlsh failed for {query!r}: {result.stderr.strip()}')
    rows = []
    for line in result.stdout.splitlines():
        s = line.strip()
        if s.startswith('{') and s.endswith('}'):
            # cqlsh prints text with every backslash doubled; in JSON a backslash
            # only ever starts an escape, so halving them all is exact.
            rows.append(s.replace('\\\\', '\\'))
    return rows


def run_cql(statements):
    if not statements:
        return
    result = subprocess.run(CQLSH, input='\n'.join(statements) + '\n', capture_output=True, text=True)
    if result.returncode != 0 or 'Error' in result.stderr:
        raise RuntimeError(f'cqlsh failed: {result.stderr.strip()}')


def schema():
    cols = [json.loads(r) for r in cql_json_rows(
        "SELECT JSON table_name, column_name, kind, position, type FROM system_schema.columns "
        f"WHERE keyspace_name = '{KS}'")]
    tables = {}
    for c in cols:
        t = tables.setdefault(c['table_name'], {'pk': [], 'ck': [], 'regular': [], 'blob': []})
        if c['kind'] == 'partition_key':
            t['pk'].append((c['position'], c['column_name']))
        elif c['kind'] == 'clustering':
            t['ck'].append((c['position'], c['column_name']))
        elif c['type'] == 'blob':
            t['blob'].append(c['column_name'])
        else:
            t['regular'].append(c['column_name'])
    for t in tables.values():
        t['keys'] = [n for _, n in sorted(t['pk'])] + [n for _, n in sorted(t['ck'])]
    return dict(sorted(tables.items()))


def row_key(doc, keys):
    return json.dumps([doc.get(k) for k in keys], sort_keys=True)


def dump(path):
    out = {}
    total = 0
    for name, t in schema().items():
        selectors = [f'"{c}"' for c in t['keys'] + t['regular']]
        selectors += [f'writetime("{b}") AS "{b}{WT}"' for b in t['blob']]
        rows = {}
        for raw in cql_json_rows(f'SELECT JSON {", ".join(selectors)} FROM {KS}."{name}"'):
            rows[row_key(json.loads(raw), t['keys'])] = raw
        out[name] = {'keys': t['keys'], 'blobs': t['blob'], 'rows': rows}
        total += len(rows)
        print(f'{name:24s} {len(rows):6d} rows')
    with open(path, 'w', encoding='utf-8') as fh:
        json.dump(out, fh)
    print(f'dumped {total} rows from {len(out)} tables to {path}')


def load(path):
    with open(path, encoding='utf-8') as fh:
        return json.load(fh)


def changes(before, after):
    result = {}
    for table in sorted(set(before) | set(after)):
        b = before.get(table, {}).get('rows', {})
        a = after.get(table, {}).get('rows', {})
        added = [k for k in a if k not in b]
        removed = [k for k in b if k not in a]
        changed = [k for k in b if k in a and a[k] != b[k]]
        if added or removed or changed:
            result[table] = (added, removed, changed)
    return result


def short(s, n=90):
    return s if len(s) <= n else s[: n - 3] + '...'


def diff(before_path, after_path):
    before, after = load(before_path), load(after_path)
    found = changes(before, after)
    if not found:
        print('no differences')
        return
    for table, (added, removed, changed) in found.items():
        print(f'== {table}: +{len(added)} added, -{len(removed)} removed, ~{len(changed)} changed')
        for k in added[:10]:
            print('   + ', short(after[table]['rows'][k]))
        for k in removed[:10]:
            print('   - ', short(before[table]['rows'][k]))
        for k in changed[:10]:
            b, a = json.loads(before[table]['rows'][k]), json.loads(after[table]['rows'][k])
            fields = [f'{f}: {short(json.dumps(b.get(f)), 40)} -> {short(json.dumps(a.get(f)), 40)}'
                      for f in b if b.get(f) != a.get(f)]
            print('   ~ ', short(k, 60), '|', '; '.join(fields))


def esc(s):
    return s.replace("'", "''")


def insert_statement(table, raw):
    doc = {c: v for c, v in json.loads(raw).items() if not c.endswith(WT)}
    return f"INSERT INTO {KS}.\"{table}\" JSON '{esc(json.dumps(doc))}' DEFAULT UNSET;"


def delete_statement(table, keys, raw):
    doc = json.loads(raw)
    where = ' AND '.join(f"\"{c}\" = fromJson('{esc(json.dumps(doc[c]))}')" for c in keys)
    return f'DELETE FROM {KS}."{table}" WHERE {where};'


def restore(before_path, after_path, skip=(), dry_run=False, only=()):
    """Puts every changed row back as it was in `before`. With `only`, just the
    rows whose key contains one of those strings (e.g. an id or a timestamp)."""
    before, after = load(before_path), load(after_path)
    found = changes(before, after)
    statements = []
    for table, (added, removed, changed) in found.items():
        if table in skip:
            print(f'skip {table}')
            continue
        if only:
            pick = lambda ks: [k for k in ks if any(o in k for o in only)]
            added, removed, changed = pick(added), pick(removed), pick(changed)
            if not (added or removed or changed):
                continue
        keys = (before.get(table) or after[table])['keys']
        blobs = (before.get(table) or after[table]).get('blobs', [])
        for k in removed + changed:
            raw = before[table]['rows'][k]
            doc = json.loads(raw)
            # A blob can't be put back from this dump (only from the snapshot): say so.
            for b in blobs:
                a_doc = json.loads(after[table]['rows'][k]) if k in after[table]['rows'] else {}
                if doc.get(b + WT) is not None and doc.get(b + WT) != a_doc.get(b + WT):
                    print(f'WARNING {table} {short(k, 60)}: blob {b} changed or removed - restore it from the snapshot')
            statements.append(insert_statement(table, raw))
        for k in added:
            statements.append(delete_statement(table, keys, after[table]['rows'][k]))
        print(f'{table}: re-insert {len(removed) + len(changed)}, delete {len(added)}')
    if dry_run:
        print('\n'.join(short(s, 160) for s in statements))
        return
    run_cql(statements)
    print(f'applied {len(statements)} statements')


def clean_sessions(before_path, after_path, emails):
    """Deletes only the sessions the tests created for the given accounts."""
    before, after = load(before_path), load(after_path)
    b, a = before['sessions']['rows'], after['sessions']['rows']
    keys = after['sessions']['keys']
    statements = [delete_statement('sessions', keys, a[k]) for k in a
                  if k not in b and json.loads(a[k]).get('user_email') in emails]
    run_cql(statements)
    print(f'deleted {len(statements)} test sessions')


def selftest(path):
    """Proves the restore statements work on every table without changing data:
    re-inserts one existing row per table with its own values (blobs untouched),
    and looks the same row up through the DELETE path's key encoding."""
    before = load(path)
    for table, data in before.items():
        if not data['rows']:
            continue
        raw = next(iter(data['rows'].values()))
        doc = json.loads(raw)
        where = ' AND '.join(f"\"{c}\" = fromJson('{esc(json.dumps(doc[c]))}')" for c in data['keys'])
        found = cql_json_rows(f'SELECT JSON {", ".join(chr(34) + k + chr(34) for k in data["keys"])} '
                              f'FROM {KS}."{table}" WHERE {where}')
        assert len(found) == 1, f'{table}: key lookup found {len(found)} rows'
        run_cql([insert_statement(table, raw)])
        print(f'{table:24s} ok')


def main(argv):
    if len(argv) >= 3 and argv[1] == 'selftest':
        selftest(argv[2])
    elif len(argv) >= 3 and argv[1] == 'dump':
        dump(argv[2])
    elif len(argv) >= 4 and argv[1] == 'diff':
        diff(argv[2], argv[3])
    elif len(argv) >= 4 and argv[1] == 'restore':
        skip = tuple(argv[argv.index('--skip') + 1].split(',')) if '--skip' in argv else ()
        only = tuple(argv[argv.index('--only') + 1].split(',')) if '--only' in argv else ()
        restore(argv[2], argv[3], skip=skip, dry_run='--dry-run' in argv, only=only)
    elif len(argv) >= 5 and argv[1] == 'clean-sessions':
        clean_sessions(argv[2], argv[3], set(argv[4].split(',')))
    else:
        print(__doc__)
        return 2
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
