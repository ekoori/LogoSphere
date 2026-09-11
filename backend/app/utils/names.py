# Resolve user ids to display names in one IN query, with a short cache.
# Entity rows used to store parallel `*_names` lists next to their id lists;
# those drift the moment someone renames and are positionally fragile. Names
# now come from `users` at read time.
import time
import uuid
import logging
from app.db import session

_TTL = 30.0
_cache = {}   # user_id -> (name, ts)


def resolve_user_names(ids):
    """{user_id: display name} for an iterable of user UUIDs."""
    now = time.time()
    want, out = [], {}
    for i in ids or []:
        try:
            uid = i if isinstance(i, uuid.UUID) else uuid.UUID(str(i))
        except (ValueError, TypeError):
            continue
        hit = _cache.get(uid)
        if hit and now - hit[1] < _TTL:
            out[uid] = hit[0]
        else:
            want.append(uid)
    if want:
        try:
            uniq = list(set(want))
            placeholders = ', '.join(['%s'] * len(uniq))
            for r in session.execute(
                    f"SELECT user_id, name, surname FROM users WHERE user_id IN ({placeholders})", uniq):
                name = f"{r.name or ''} {getattr(r, 'surname', '') or ''}".strip() or 'Member'
                out[r.user_id] = name
                _cache[r.user_id] = (name, now)
        except Exception as e:
            logging.getLogger(__name__).error('resolve_user_names failed: %s', e)
    return out


def dedupe(ids):
    """Stable de-duplication of an id list (list columns can double up on a
    retried append)."""
    seen, out = set(), []
    for i in ids or []:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def forget_user_name(user_id):
    _cache.pop(uuid.UUID(str(user_id)), None)
