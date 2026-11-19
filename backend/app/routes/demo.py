# The demonstration: spheres flagged is_demo, whose members are AI personas
# (see app/utils/demo.py and backend/agents). New members are invited to them,
# not enrolled; this joins them all at once.
#
#   GET  /api/demo        the demo spheres and whether you're in each
#   POST /api/demo/join   join every demo sphere (open join policy) at once
import logging
import uuid

from flask import jsonify, request, current_app as app

from app.middleware.session_middleware import validate_session
from app.models.notification import Notification
from app.models.spheres import Sphere

logger = logging.getLogger(__name__)

INVITE_TYPE = 'demo_invite'


def _demo_spheres():
    return sorted((s for s in Sphere.get_all() if s.is_demo), key=lambda s: (s.name or '').lower())


def _summary(sphere, uid):
    return {
        'id': str(sphere.sphere_id), 'name': sphere.name, 'description': sphere.description,
        'joined': uid in (sphere.participants or []),
        'member_count': len(set(sphere.participants or [])),
    }


@validate_session
def get_demo(user_id=None):
    """The demo spheres, and whether the viewer has joined each."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    uid = uuid.UUID(str(user_id))
    spheres = [_summary(s, uid) for s in _demo_spheres()]
    return jsonify({'spheres': spheres,
                    'joined_any': any(s['joined'] for s in spheres),
                    'joined_all': bool(spheres) and all(s['joined'] for s in spheres)}), 200


@validate_session
def join_demo(user_id=None):
    """Join every demo sphere that anyone may join, in one go."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    uid = uuid.UUID(str(user_id))
    joined = []
    for sphere in _demo_spheres():
        if (sphere.join_policy or 'open') != 'open':
            continue
        if not Sphere.join(sphere.sphere_id, uid):
            joined.append(str(sphere.sphere_id))
    # The invitation has done its job.
    Notification.withdraw(uid, INVITE_TYPE, '/spheres#demo')
    spheres = [_summary(s, uid) for s in _demo_spheres()]
    return jsonify({'joined': joined, 'spheres': spheres}), 200


def invite_to_demo(user_id):
    """Invite a new member to the demo spheres. Best-effort: a failure must
    never break the registration that triggered it."""
    try:
        names = [s.name for s in _demo_spheres()]
        if not names:
            return
        listed = ', '.join(names[:-1]) + (f' and {names[-1]}' if len(names) > 1 else names[0])
        Notification.create(
            user_id=user_id, actor_id=None, actor_name='LogoSphere', type_=INVITE_TYPE,
            message=(f'Welcome! Try the demo spheres - {listed} - where AI personas play '
                     'everyday neighbours. Join them all in one tap and try anything.'),
            link='/spheres#demo',
        )
    except Exception as e:
        logger.error(f'Demo invitation failed for {user_id}: {e}')
