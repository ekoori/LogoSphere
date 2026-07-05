#registration.py

from flask import Blueprint, request, jsonify

#from flask import current_app as app
import logging
from app.models.user import User
from app.models.spheres import Sphere

registration = Blueprint('registration', __name__)


def register():
    # Get the posted data
    data = request.get_json()

    # Attempt to register the user
    user = User.register(data)

    if user:
        # Auto-enroll every new user into all sandbox spheres so they land in a
        # community immediately (Phase 5). Best-effort — a failure here must not
        # block a successful registration.
        try:
            for sid in Sphere.sandbox_ids():
                Sphere.join(sid, user.user_id)
        except Exception as e:
            logging.error(f'Sandbox auto-join failed for new user {user.user_id}: {e}')
        return jsonify({'reg_success':True,'message': 'User registered successfully.', 'user_id': user.user_id}), 200
    else:
        return jsonify({'message': 'Registration failed.'}), 400


