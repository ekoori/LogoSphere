"""
File: ./backend/app/routes/trusttrail.py
Description: Flask route file handling TrustTrail operations. Auth is provided by
the Cassandra-backed @validate_session decorator (consistent with the other
routes), which injects the authenticated user_id.
Methods:
    [x] get_trusttrail() : GET/POST '/trusttrail' — fetch a user's trust trail.
    [x] add_transaction() : POST '/trusttrail/add_transaction' — add a transaction.
"""

import logging
from flask import request, jsonify, current_app as app
from app.models.trusttrail import TrustTrail
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


@validate_session
def get_trusttrail(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200

    # A user_id may be supplied (e.g. viewing another profile); default to self.
    target_id = str(user_id)
    if request.method == 'POST':
        data = request.get_json() or {}
        target_id = data.get('userId') or data.get('user_id') or target_id

    trust_trail = TrustTrail.get_trusttrail(target_id)
    # get_trusttrail returns [] for an empty trail and None on error.
    if trust_trail is None:
        return jsonify({'error': 'TrustTrail not found'}), 404
    return jsonify(trust_trail), 200


@validate_session
def add_transaction(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        other_user_id = data['other_user_id']
        project_id = data['project_id']
        TrustTrail.add_transaction(str(user_id), other_user_id, project_id)
        return jsonify({'message': 'Transaction added successfully'}), 200
    except KeyError as e:
        return jsonify({'message': f'Missing field: {e}'}), 400
    except Exception as e:
        logger.error(f"Error in add_transaction: {e}")
        return jsonify({'message': 'Internal server error'}), 500
