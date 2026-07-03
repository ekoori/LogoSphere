"""
File: ./backend/app/routes/meaning_trail.py
Description: Flask route file handling MeaningTrail operations. Auth is provided by
the Cassandra-backed @validate_session decorator (consistent with the other
routes), which injects the authenticated user_id.
Methods:
    [x] get_meaning_trail() : GET/POST '/meaning_trail' — fetch a user's trust trail.
    [x] add_exchange() : POST '/meaning_trail/add_exchange' — add a exchange.
"""

import logging
from flask import request, jsonify, current_app as app
from app.models.meaning_trail import MeaningTrail, Likes, LIKE_TYPES
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


@validate_session
def get_meaning_trail(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200

    # A user_id may be supplied (e.g. viewing another profile); default to self.
    target_id = str(user_id)
    if request.method == 'POST':
        data = request.get_json() or {}
        target_id = data.get('userId') or data.get('user_id') or target_id

    # viewer (user_id) drives the "liked by me" flag on each target.
    trust_trail = MeaningTrail.get_meaning_trail(target_id, viewer_id=user_id)
    # get_meaning_trail returns [] for an empty trail and None on error.
    if trust_trail is None:
        return jsonify({'error': 'MeaningTrail not found'}), 404
    return jsonify(trust_trail), 200


@validate_session
def get_meaning_trail_by_project(project_id, user_id=None):
    """A project's own aggregate Meaning Trail — every exchange tagged with
    this project, from any of its contributors. Used by ProjectPage's main
    feed (and by Alliance/Sphere pages, which merge several projects' worth)."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    return jsonify(MeaningTrail.get_by_project_id(project_id, viewer_id=user_id)), 200


@validate_session
def add_exchange(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        other_user_id = data['other_user_id']
        project_id = data['project_id']
        MeaningTrail.add_exchange(str(user_id), other_user_id, project_id)
        return jsonify({'message': 'Exchange added successfully'}), 200
    except KeyError as e:
        return jsonify({'message': f'Missing field: {e}'}), 400
    except Exception as e:
        logger.error(f"Error in add_exchange: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def get_exchange(exchange_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        # Anyone may view an exchange (so they can acknowledge it); the flags tell
        # the client what this viewer is allowed to change.
        tx_dict, is_initiator, is_other = MeaningTrail.get_for_view(exchange_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Exchange not found'}), 404
        return jsonify({
            'exchange': tx_dict,
            'is_initiator': is_initiator,
            'is_other': is_other,
            'is_participant': is_initiator or is_other,
        }), 200
    except Exception as e:
        logger.error(f"Error in get_exchange: {e}")
        return jsonify({'message': 'Internal server error'}), 500


_VALID_STATUSES = {'Initiated', 'In Progress', 'Finished', 'Receipted',
                   'Additional Comments Added', 'Cancelled'}


@validate_session
def update_xc_status(exchange_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        new_status = data.get('status', '')
        if new_status not in _VALID_STATUSES:
            return jsonify({'message': 'Invalid status'}), 400

        tx_dict, is_initiator, is_other = MeaningTrail.get_for_view(exchange_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Exchange not found'}), 404
        if not (is_initiator or is_other):
            return jsonify({'message': 'Only participants can change the status'}), 403

        MeaningTrail.set_status_for(tx_dict['user_id'], exchange_id, new_status)
        return jsonify({'message': 'Status updated'}), 200
    except Exception as e:
        logger.error(f"Error in update_xc_status: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def add_xc_comment(exchange_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        comment_type = data.get('type', '')
        text = (data.get('text') or '').strip()
        cards = data.get('cards') or []
        if not text or comment_type not in ('gratitude', 'user', 'other', 'comment'):
            return jsonify({'message': 'Invalid comment data'}), 400

        tx_dict, is_initiator, is_other = MeaningTrail.get_for_view(exchange_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Exchange not found'}), 404

        # Post-receipt follow-up note: one per side, participants only, and only
        # once both sides have receipted.
        if comment_type == 'comment':
            if not (is_initiator or is_other):
                return jsonify({'message': 'Only participants can comment'}), 403
            side = 'initiator' if is_initiator else 'recipient'
            result = MeaningTrail.add_followup_for(tx_dict['user_id'], exchange_id, side, text)
            if result == 'ok':
                return jsonify({'message': 'Comment added'}), 200
            if result == 'not_ready':
                return jsonify({'message': 'Both sides must receipt first'}), 409
            if result == 'exists':
                return jsonify({'message': 'You have already commented'}), 409
            return jsonify({'message': 'Failed to add comment'}), 500

        # Receipts and the initiator note are participant-only; acknowledgements
        # ('other') may be added by anyone.
        if comment_type == 'gratitude' and not is_other:
            return jsonify({'message': 'Only the recipient can add a receipt'}), 403
        if comment_type == 'user' and not is_initiator:
            return jsonify({'message': 'Only the initiator can add a personal note'}), 403

        # Exactly one receipt per side — reject a second submission rather than
        # silently overwriting the first (the column holds a single value).
        if comment_type == 'gratitude' and tx_dict.get('gratitude_comment'):
            return jsonify({'message': 'A receipt has already been added for this side'}), 409
        if comment_type == 'user' and tx_dict.get('user_comment'):
            return jsonify({'message': 'A note has already been added for this side'}), 409

        author_name = None
        if comment_type == 'other':
            from app.models.user import User
            u = User.get(str(user_id))
            if u:
                author_name = f"{u.name or ''} {u.surname or ''}".strip() or u.email

        ok = MeaningTrail.add_comment_for(
            tx_dict['user_id'], exchange_id, comment_type, text,
            author_id=str(user_id), author_name=author_name,
            cards=cards if cards else None,
        )
        if ok:
            return jsonify({'message': 'Comment added'}), 200
        return jsonify({'message': 'Failed to add comment'}), 500
    except Exception as e:
        logger.error(f"Error in add_xc_comment: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def like_exchange(exchange_id, user_id=None):
    """Toggle the current user's like on an exchange or one of its comments.
    Body: { "comment_type": "exchange" | "gratitude" | "user" | "other" }."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        comment_type = data.get('comment_type', 'exchange')
        if comment_type not in LIKE_TYPES:
            return jsonify({'message': 'Invalid comment_type'}), 400

        # Any authenticated member can like an exchange they can see, but the
        # exchange must actually exist (avoids orphan like rows).
        if not MeaningTrail.exists(exchange_id):
            return jsonify({'message': 'Exchange not found'}), 404

        liked, count = Likes.toggle(exchange_id, comment_type, user_id)
        return jsonify({'liked': liked, 'count': count, 'comment_type': comment_type}), 200
    except Exception as e:
        logger.error(f"Error in like_exchange: {e}")
        return jsonify({'message': 'Internal server error'}), 500
