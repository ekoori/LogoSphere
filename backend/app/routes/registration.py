#registration.py
"""POST /api/register.

With email working this only starts it: a link is mailed, and the account is
made when it's used (app/routes/email.py, finish_sign_up). Without email the
account is made here and now.
"""
import logging

from flask import request, jsonify

from app.models.user import User
from app.models.spheres import Sphere
from app.routes.demo import invite_to_demo
from app.utils import mailer


def welcome(user_id):
    """What every new account gets. Best-effort: never blocks joining."""
    # Auto-enroll every new user into all sandbox spheres so they land in a
    # community immediately (Phase 5).
    try:
        for sid in Sphere.sandbox_ids():
            Sphere.join(sid, user_id)
    except Exception as e:
        logging.error(f'Sandbox auto-join failed for new user {user_id}: {e}')
    invite_to_demo(user_id)


def register():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({'message': 'Registration failed.'}), 400
    if mailer.enabled():
        from app.routes.email import begin_sign_up     # that module imports this one
        return begin_sign_up(data)
    if not all(isinstance(data.get(k), str) for k in ('name', 'email', 'password')):
        return jsonify({'message': 'Registration failed.'}), 400

    user = User.register(data)
    if not user:
        return jsonify({'message': 'Registration failed.'}), 400
    welcome(user.user_id)
    return jsonify({'reg_success': True, 'message': 'User registered successfully.', 'user_id': user.user_id}), 200
