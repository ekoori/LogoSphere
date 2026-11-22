"""Real places (app/utils/places.py):

  POST /api/places/search        places by name; what is searched stays out of URLs
  POST /api/places/nearest       names to offer for a pin
  GET  /api/places/<kind>/<id>   one place, whole: only for whoever may change it
  POST /api/places/<kind>/<id>   set or clear it
  GET  /api/nearby               members who chose to be findable, and spheres, near you
"""
from datetime import datetime

from flask import current_app as app, jsonify, request

from app.db import session
from app.middleware.session_middleware import validate_session
from app.models.alliance import Alliance
from app.models.openings import Service
from app.models.project import Project
from app.models.spheres import Sphere
from app.routes.openings import _is_provider_or_manager
from app.utils import events, gazetteer, geo, places, safety
from app.utils.access import Sight, as_uuid
from app.utils.permissions import can_manage_entity
from app.utils.search_vectors import invalidate_index

MODELS = {'spheres': Sphere, 'alliances': Alliance, 'projects': Project}
RADII_KM = (5, 10, 25, 50, 100, 250)
MOST = 50


def _options():
    return app.make_default_options_response(), 200


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _refusal(kind, owner_id, viewer):
    """Why this viewer may neither read nor set that place, as (message, status); or None."""
    if kind not in places.KINDS or as_uuid(owner_id) is None:
        return 'Not found', 404
    owner, me = as_uuid(owner_id), as_uuid(viewer)
    if kind == 'users':
        # A person's point is theirs alone: not even an administrator's.
        return None if owner == me else ("That isn't your place.", 403)
    if kind == 'openings':
        opening = Service.get_by_id(owner)
        if not opening:
            return 'Not found', 404
        if not _is_provider_or_manager(opening, viewer):
            return 'Only whoever posted it can say where it is.', 403
        if not opening.is_current:
            return 'This is a past version and can no longer be edited', 409
        return None
    if kind == 'events':
        event = events.get(owner)
        if not event or not event.visible(Sight(viewer)):
            return 'Not found', 404
        return None if event.managed(viewer) else ("Only whoever put it on, or the group's managers, can say where it is.", 403)
    if not MODELS[kind].get_by_id(owner):
        return 'Not found', 404
    return None if can_manage_entity(owner, viewer) else ('Only its managers can say where it is.', 403)


def _version_to_change(opening_id, place):
    """Where an exchange was agreed stays with that version: a new place makes
    a new one, as new words do (edit_opening)."""
    opening = Service.get_by_id(as_uuid(opening_id))
    if places.load(opening.place) == place or not Service.has_related_exchange(opening.service_id):
        return opening_id
    return Service.create_version(opening, {}).service_id


@validate_session
def search_places(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    own = places.of_person(user_id)
    found = gazetteer.search(str(_body().get('q') or '')[:120], near=(own['lat'], own['lon']) if own else None)
    return jsonify({'available': gazetteer.available(), 'attribution': gazetteer.ATTRIBUTION, 'results': found}), 200


@validate_session
def nearest_places(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    data = _body()
    point = geo.coordinates(data.get('lat'), data.get('lon'))
    if point is None:
        return jsonify({'message': "That spot isn't on the map."}), 400
    return jsonify({'available': gazetteer.available(), 'results': gazetteer.nearest(*point)}), 200


@validate_session
def get_place(kind, owner_id, user_id=None):
    refused = _refusal(kind, owner_id, user_id)
    if refused:
        return jsonify({'message': refused[0]}), refused[1]
    place, findable = places.for_editor(kind, owner_id)
    out = {'place': place, 'search_available': gazetteer.available()}
    if kind == 'users':
        out['findable'] = findable
    return jsonify(out), 200


@validate_session
def set_place(kind, owner_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    refused = _refusal(kind, owner_id, user_id)
    if refused:
        return jsonify({'message': refused[0]}), refused[1]
    data = _body()
    if 'place' in data:
        try:
            place = places.clean(data['place'])
        except places.BadPlace as e:
            return jsonify({'message': str(e)}), 400
        if kind == 'openings':
            owner_id = _version_to_change(owner_id, place)
        moved = None
        if kind == 'events':
            event = events.get(owner_id)
            was = places.load(event.place)
            moved = event if was and was != place and event.upcoming(datetime.utcnow()) else None
        places.save(kind, owner_id, place, findable=data.get('findable') is True)
        if moved:       # it was somewhere, and now is somewhere else
            from app.routes.events import tell_expecting
            tell_expecting(moved, user_id, f'The place changed: "{moved.title}"')
    elif kind == 'users' and isinstance(data.get('findable'), bool):
        if not places.set_findable(owner_id, data['findable']):
            return jsonify({'message': 'Put yourself on the map first, then others can find you.'}), 400
    else:
        return jsonify({'message': 'Say which place, or null for none.'}), 400
    invalidate_index()          # search shows where people are, in their words
    place, findable = places.for_editor(kind, owner_id)
    # `id` is another when an agreed opening got a new version.
    out = {'id': str(owner_id), 'place': place}
    if kind == 'users':
        out['findable'] = findable
    return jsonify(out), 200


@validate_session
def nearby(user_id=None):
    me = as_uuid(user_id)
    km = request.args.get('km', default=25, type=int)
    if km not in RADII_KM:
        return jsonify({'message': f'km is one of {", ".join(map(str, RADII_KM))}.'}), 400
    place, findable = places.for_editor('users', me)
    # A country is a point on the map too, but says nothing about nearness.
    out = {'has_place': geo.distance(place, place) is not None, 'findable': findable, 'km': km, 'people': [], 'spheres': []}
    if not out['has_place']:
        return jsonify(out), 200

    people, hidden = [], safety.hidden_from(me)
    for r in session.execute('SELECT user_id, name, surname, location, is_agent, place FROM users'):
        theirs = places.load(r.place)
        if r.user_id == me or r.user_id in hidden or not theirs or theirs.get('findable') is not True:
            continue
        away = geo.distance(place, theirs)
        if away and away['km'] <= km:
            people.append({'id': str(r.user_id), 'name': f"{r.name or ''} {r.surname or ''}".strip() or 'A member',
                           'location': r.location, 'is_agent': bool(r.is_agent), 'distance': away})
    spheres = []
    for r in session.execute('SELECT sphere_id, name, location, is_demo, has_image, participants, place FROM spheres'):
        away = places.how_far(place, r.place)
        if away and away['km'] <= km:
            spheres.append({'id': str(r.sphere_id), 'name': r.name, 'location': r.location, 'is_demo': bool(r.is_demo),
                            'has_image': bool(r.has_image), 'is_member': me in (r.participants or []),
                            'member_count': len(set(r.participants or [])), 'distance': away})
    # By band, then name: an order by true distance would give away more than the band.
    for key, found in (('people', people), ('spheres', spheres)):
        found.sort(key=lambda x: (x['distance']['km'], (x['name'] or '').lower(), x['id']))
        out[key] = found[:MOST]
    return jsonify(out), 200


def register(app_):
    places.ensure_tables()
    app_.add_url_rule('/api/places/search', view_func=search_places, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/places/nearest', view_func=nearest_places, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/places/<kind>/<owner_id>', view_func=get_place, methods=['GET'])
    app_.add_url_rule('/api/places/<kind>/<owner_id>', view_func=set_place, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/nearby', view_func=nearby, methods=['GET'])
