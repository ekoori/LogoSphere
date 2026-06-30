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


@validate_session
def get_transaction(transaction_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        tx_dict, is_initiator = TrustTrail.get_by_id(transaction_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Transaction not found or not authorized'}), 404
        return jsonify({'transaction': tx_dict, 'is_initiator': is_initiator}), 200
    except Exception as e:
        logger.error(f"Error in get_transaction: {e}")
        return jsonify({'message': 'Internal server error'}), 500


_VALID_STATUSES = {'Initiated', 'In Progress', 'Finished', 'Trustifacted',
                   'Additional Comments Added', 'Cancelled'}


@validate_session
def update_tx_status(transaction_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        new_status = data.get('status', '')
        if new_status not in _VALID_STATUSES:
            return jsonify({'message': 'Invalid status'}), 400

        tx_dict, _ = TrustTrail.get_by_id(transaction_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Transaction not found or not authorized'}), 404

        TrustTrail.set_status_for(tx_dict['user_id'], transaction_id, new_status)
        return jsonify({'message': 'Status updated'}), 200
    except Exception as e:
        logger.error(f"Error in update_tx_status: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def add_tx_comment(transaction_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        comment_type = data.get('type', '')
        text = (data.get('text') or '').strip()
        if not text or comment_type not in ('gratitude', 'user', 'other'):
            return jsonify({'message': 'Invalid comment data'}), 400

        tx_dict, is_initiator = TrustTrail.get_by_id(transaction_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Transaction not found or not authorized'}), 404

        # Enforce who can add what
        if comment_type == 'gratitude' and is_initiator:
            return jsonify({'message': 'Only the other participant can add a trustifact'}), 403
        if comment_type == 'user' and not is_initiator:
            return jsonify({'message': 'Only the initiator can add a personal note'}), 403

        author_name = None
        if comment_type == 'other':
            from app.models.user import User
            u = User.get(str(user_id))
            if u:
                author_name = f"{u.name or ''} {u.surname or ''}".strip() or u.email

        ok = TrustTrail.add_comment_for(
            tx_dict['user_id'], transaction_id, comment_type, text,
            author_id=str(user_id), author_name=author_name,
        )
        if ok:
            return jsonify({'message': 'Comment added'}), 200
        return jsonify({'message': 'Failed to add comment'}), 500
    except Exception as e:
        logger.error(f"Error in add_tx_comment: {e}")
        return jsonify({'message': 'Internal server error'}), 500
