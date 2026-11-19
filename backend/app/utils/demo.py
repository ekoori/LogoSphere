# What belongs to the demonstration, and who is an AI persona.
#
# Demo spheres (spheres.is_demo) live alongside real ones; everything inside a
# demo sphere - its alliances, projects, openings and exchanges - is demo too.
# Persona accounts (users.is_agent) are driven by backend/agents. Responses
# carry is_demo / is_agent so every client can label them; these sets are read
# on most requests, so they're cached for a few seconds.
import time
import uuid

from app.db import session

_TTL = 20.0
_cache = {}


def _cached(key, load):
    now = time.time()
    hit = _cache.get(key)
    if hit and now - hit[1] < _TTL:
        return hit[0]
    value = load()
    _cache[key] = (value, now)
    return value


def forget():
    """Drop the cache (after a flag changes, so it shows at once)."""
    _cache.clear()


def _uuid(value):
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return value
    try:
        return uuid.UUID(str(value))
    except (ValueError, TypeError):
        return None


def demo_sphere_ids():
    return _cached('spheres', lambda: {
        r.sphere_id for r in session.execute('SELECT sphere_id, is_demo FROM spheres')
        if getattr(r, 'is_demo', False)})


def agent_ids():
    return _cached('agents', lambda: {
        r.user_id for r in session.execute('SELECT user_id, is_agent FROM users')
        if getattr(r, 'is_agent', False)})


def _service_spheres():
    return _cached('services', lambda: {
        r.service_id: r.sphere_id for r in session.execute('SELECT service_id, sphere_id FROM services')})


def _project_spheres():
    return _cached('projects', lambda: {
        r.project_id: r.sphere_id for r in session.execute('SELECT project_id, sphere_id FROM projects')})


def _alliance_spheres():
    return _cached('alliances', lambda: {
        r.alliance_id: r.sphere_id for r in session.execute('SELECT alliance_id, sphere_id FROM alliances')})


def is_demo_sphere(sphere_id):
    sid = _uuid(sphere_id)
    return sid is not None and sid in demo_sphere_ids()


def is_agent(user_id):
    uid = _uuid(user_id)
    return uid is not None and uid in agent_ids()


def entity_is_demo(entity_id):
    """A sphere, alliance or project id: does it belong to a demo sphere?"""
    eid = _uuid(entity_id)
    if eid is None:
        return False
    if eid in demo_sphere_ids():
        return True
    sphere = _alliance_spheres().get(eid) or _project_spheres().get(eid)
    return is_demo_sphere(sphere)


def exchange_sphere_id(row):
    """The sphere an exchange (a meaning_trail row or its dict) happened in:
    that of the opening it came from, else of its project."""
    get = row.get if isinstance(row, dict) else (lambda k: getattr(row, k, None))
    sphere = _service_spheres().get(_uuid(get('source_service_id')))
    if sphere is None:
        sphere = _project_spheres().get(_uuid(get('project_id')))
    return sphere


def exchange_is_demo(row):
    sphere = exchange_sphere_id(row)
    if sphere is not None:
        return is_demo_sphere(sphere)
    # No opening or project to go by: demo when nobody real is in it.
    get = row.get if isinstance(row, dict) else (lambda k: getattr(row, k, None))
    sides = [get('user_id'), get('other_user_id')]
    return all(is_agent(s) or entity_is_demo(s) for s in sides if s)
