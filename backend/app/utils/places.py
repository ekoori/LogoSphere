# Real places, beside the words people use for them.
#
# `place` (JSON) on people, spheres, alliances, projects and openings holds
# {label, lat, lon, precision}. For people and spheres the words stay in their
# `location` column, as before; a person's place also has `findable`: "members
# nearby can find me", off until they switch it on.
#
# Who learns what:
#   a person's point     only that person, ever
#   a group's, opening's only who manages it, unless they chose "exact": then
#                        whoever may see the group or opening sees the spot
#   everyone else        the words, and a distance in bands (app/utils/geo.py)
import json

from app.db import session
from app.utils import gazetteer, geo
from app.utils.access import as_uuid

# kind in the API -> (table, id column, whether the words live in `location`)
KINDS = {
    'users': ('users', 'user_id', True),
    'spheres': ('spheres', 'sphere_id', True),
    'alliances': ('alliances', 'alliance_id', False),
    'projects': ('projects', 'project_id', False),
    'openings': ('services', 'service_id', False),
    'events': ('events', 'event_id', False),
}
# (events is newer than places: its table is made with the column.)
DDL = [f'ALTER TABLE {table} ADD IF NOT EXISTS place text' for table, _, _ in KINDS.values() if table != 'events']
LABEL_MAX = 120


class BadPlace(ValueError):
    """Said to the member as it is."""


def ensure_tables():
    for statement in DDL:
        session.execute(statement)


def load(stored):
    if not stored:
        return None
    try:
        place = json.loads(stored)
    except (TypeError, ValueError):
        return None
    return place if isinstance(place, dict) else None


def has_point(place):
    return bool(place) and geo.coordinates(place.get('lat'), place.get('lon')) is not None


def label_of(stored):
    return (load(stored) or {}).get('label') or None


def clean(given):
    """A place as a client sends it -> as it may be stored, or None for none.

    {id, label?}                  one from the search: the point is the gazetteer's
    {lat, lon, precision, label}  a pin: rounded here, before it is stored
    {label}                       only words
    """
    if given is None:
        return None
    if not isinstance(given, dict):
        raise BadPlace("That isn't a place.")
    label = ' '.join(str(given.get('label') or '').split())[:LABEL_MAX].strip()
    if given.get('id') is not None:
        found = gazetteer.get(given['id'])
        if not found:
            raise BadPlace('That place is no longer in the list. Search again.')
        return {'label': label or found['label'][:LABEL_MAX], 'lat': found['lat'], 'lon': found['lon'],
                'precision': found['precision']}
    if given.get('lat') is None and given.get('lon') is None:
        return {'label': label} if label else None
    point = geo.coordinates(given.get('lat'), given.get('lon'))
    if point is None:
        raise BadPlace("That spot isn't on the map.")
    precision = given.get('precision', '1km')
    if precision not in tuple(geo.PIN_SQUARES):
        raise BadPlace('Choose how exact it should be.')
    if not label:
        raise BadPlace('Say in a few words where this is: that is what people see.')
    lat, lon = geo.rounded(*point, precision)
    return {'label': label, 'lat': lat, 'lon': lon, 'precision': precision}


def save(kind, owner_id, place, findable=False):
    table, key, words_in_location = KINDS[kind]
    label = place['label'] if place else None
    kept = dict(place) if place else None
    if kind == 'users' and kept is not None:
        kept['findable'] = bool(findable) and has_point(kept)
    if words_in_location:
        stored = json.dumps(kept) if has_point(kept) else None      # words alone need no place
        session.execute(f'UPDATE {table} SET place = %s, location = %s WHERE {key} = %s',
                        [stored, label, as_uuid(owner_id)])
    else:
        session.execute(f'UPDATE {table} SET place = %s WHERE {key} = %s',
                        [json.dumps(kept) if kept else None, as_uuid(owner_id)])


def set_findable(user_id, findable):
    """Only the switch: the place stays as it is (one from the search has no pin to send again)."""
    who = as_uuid(user_id)
    row = session.execute('SELECT place FROM users WHERE user_id = %s', [who]).one()
    place = load(row.place) if row else None
    if not has_point(place):
        return not findable     # with no point there's nothing to be found by
    place['findable'] = bool(findable)
    session.execute('UPDATE users SET place = %s WHERE user_id = %s', [json.dumps(place), who])
    return True


def for_editor(kind, owner_id):
    """All of it, for whoever may change it."""
    table, key, words_in_location = KINDS[kind]
    cols = 'place, location' if words_in_location else 'place'
    row = session.execute(f'SELECT {cols} FROM {table} WHERE {key} = %s', [as_uuid(owner_id)]).one()
    if not row:
        return None, False
    place = load(row.place) or {}
    findable = bool(place.pop('findable', False))
    if words_in_location:
        if row.location:
            place['label'] = row.location
        else:
            place.pop('label', None)
    return (place or None), findable


def of_person(user_id):
    """Their place, for working out distances. Never for showing."""
    who = as_uuid(user_id)
    row = session.execute('SELECT place FROM users WHERE user_id = %s', [who]).one() if who else None
    place = load(row.place) if row else None
    return place if has_point(place) else None


def words_changed(user_id, location):
    """Someone typed other words for where they are: the old point no longer says it."""
    row = session.execute('SELECT location FROM users WHERE user_id = %s', [as_uuid(user_id)]).one()
    return bool(row) and (row.location or '').strip() != (location or '').strip()


def sphere_places():
    out = {}
    for r in session.execute('SELECT sphere_id, place FROM spheres'):
        place = load(r.place)
        if has_point(place):
            out[r.sphere_id] = place
    return out


def exact_spot(stored):
    """The point of a group or opening whose people chose to show it exactly."""
    place = load(stored)
    if has_point(place) and place.get('precision') == 'exact':
        return {'lat': place['lat'], 'lon': place['lon']}
    return None


def how_far(origin, stored, fallback=None):
    """From the viewer's place to a stored one, or to `fallback` (an opening's
    sphere) when that has no point."""
    if not origin:
        return None
    place = load(stored)
    return geo.distance(origin, place if has_point(place) else fallback)
