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
import uuid
from flask import request, jsonify, current_app as app, Response
from app.models.meaning_trail import MeaningTrail, Likes, LIKE_TYPES
from app.models.notification import Notification
from app.utils.validation import is_supported_image
from app.middleware.session_middleware import validate_session
from app.models.spheres import Sphere
from app.utils.permissions import is_platform_admin

logger = logging.getLogger(__name__)


# ── Visibility ──────────────────────────────────────────────────────────────
# An exchange has no sphere column of its own; it inherits one from the opening
# it came from, or from its project. Participants (and platform admins) always
# see it; anyone else must belong to that sphere. Exchanges with no resolvable
# sphere (legacy/direct ones) stay visible to any signed-in member.
def _exchange_sphere_id(tx_dict):
    from app.models.openings import Service
    from app.models.project import Project
    sid = tx_dict.get('source_service_id')
    if sid:
        svc = Service.get_by_id(uuid.UUID(str(sid)))
        if svc and svc.sphere_id:
            return svc.sphere_id
    pid = tx_dict.get('project_id')
    if pid:
        prj = Project.get_by_id(pid)
        if prj and prj.sphere_id:
            return prj.sphere_id
    return None


def _can_view_exchange(tx_dict, is_participant, viewer_id):
    if is_participant or is_platform_admin(viewer_id):
        return True
    sphere_id = _exchange_sphere_id(tx_dict)
    if sphere_id is None:
        return True
    return sphere_id in Sphere.member_sphere_ids(viewer_id)


def _load_visible_exchange(exchange_id, viewer_id):
    """(tx_dict, is_initiator, is_other) if the viewer may see the exchange,
    else (None, ..) - callers return 404 rather than reveal existence."""
    tx_dict, is_initiator, is_other = MeaningTrail.get_for_view(exchange_id, viewer_id)
    if tx_dict is None or not _can_view_exchange(tx_dict, is_initiator or is_other, viewer_id):
        return None, False, False
    return tx_dict, is_initiator, is_other


# Serving images for <img src>: the browser sends the session cookie, so these
# can be gated like the exchange itself.
def _image_response(data):
    if not data:
        return ('', 404)
    if data[:8] == b'\x89PNG\r\n\x1a\n':
        ctype = 'image/png'
    elif data[:6] in (b'GIF87a', b'GIF89a'):
        ctype = 'image/gif'
    elif data[:4] == b'RIFF' and data[8:12] == b'WEBP':
        ctype = 'image/webp'
    else:
        ctype = 'image/jpeg'
    resp = Response(data, mimetype=ctype)
    resp.headers['Cache-Control'] = 'private, no-cache'
    return resp


@validate_session
def edit_exchange(exchange_id, user_id=None):
    """Edit an exchange's title / description / banner image. Participants only,
    and only until the exchange is finished (both sides have receipted)."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        tx_dict, is_initiator, is_other = MeaningTrail.get_for_view(exchange_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Exchange not found'}), 404
        if not (is_initiator or is_other):
            return jsonify({'message': 'Only participants can edit this exchange'}), 403
        if MeaningTrail.is_finished(exchange_id):
            return jsonify({'message': 'This exchange is finished and can no longer be changed'}), 409

        image = None
        if request.content_type and 'multipart/form-data' in request.content_type:
            data = request.form
            image_file = request.files.get('image')
            if image_file:
                image = image_file.read()
                if not is_supported_image(image):
                    return jsonify({'message': 'Unsupported image format (use JPEG, PNG, GIF or WebP)'}), 400
        else:
            data = request.get_json() or {}

        title = data.get('title')
        long_description = data.get('description')
        ok = MeaningTrail.edit_details(
            tx_dict['user_id'], exchange_id,
            title=title if title else None,
            long_description=long_description if long_description is not None else None,
            image=image,
        )
        if ok:
            return jsonify({'message': 'Exchange updated'}), 200
        return jsonify({'message': 'Failed to update exchange'}), 500
    except Exception as e:
        logger.error(f"Error in edit_exchange: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def get_exchange_image(exchange_id, user_id=None):
    """Serve an exchange's banner image for <img src> - visible to whoever can
    see the exchange (participants, sphere members, platform admins)."""
    try:
        tx_dict, _, _ = _load_visible_exchange(exchange_id, user_id)
        if tx_dict is None:
            return ('', 404)
        return _image_response(MeaningTrail.get_image(exchange_id))
    except Exception as e:
        logger.error(f"Error in get_exchange_image: {e}")
        return ('', 404)


@validate_session
def upload_receipt_photos(exchange_id, user_id=None):
    """Attach up to 3 photos to the receipt. Only the recipient (who gives the
    receipt) may upload them."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        tx_dict, is_initiator, is_other = _load_visible_exchange(exchange_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Exchange not found'}), 404
        if not is_other:
            return jsonify({'message': 'Only the recipient can add receipt photos'}), 403
        images = []
        for f in request.files.getlist('photos')[:3]:
            b = f.read()
            if b and is_supported_image(b):
                images.append(b)
        MeaningTrail.set_receipt_photos(exchange_id, images)
        return jsonify({'count': len(images)}), 200
    except Exception as e:
        logger.error(f"Error in upload_receipt_photos: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def get_receipt_photo(exchange_id, idx, user_id=None):
    """Serve one receipt photo for <img src> - same visibility as the exchange."""
    try:
        tx_dict, _, _ = _load_visible_exchange(exchange_id, user_id)
        if tx_dict is None:
            return ('', 404)
        return _image_response(MeaningTrail.get_receipt_photo(exchange_id, idx))
    except Exception as e:
        logger.error(f"Error in get_receipt_photo: {e}")
        return ('', 404)


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
        return jsonify({'message': 'Meaning trail not found'}), 404
    return jsonify(trust_trail), 200


@validate_session
def get_meaning_trail_by_project(project_id, user_id=None):
    """A project's own aggregate Meaning Trail — every exchange tagged with
    this project, from any of its contributors. Used by ProjectPage's main
    feed (and by Alliance/Sphere pages, which merge several projects' worth)."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    from app.models.project import Project
    project = Project.get_by_id(project_id)
    if not project:
        return jsonify({'message': 'Project not found'}), 404
    viewer = uuid.UUID(str(user_id))
    if project.sphere_id and project.sphere_id not in Sphere.member_sphere_ids(viewer) \
            and viewer not in (project.participants or []) and not is_platform_admin(viewer):
        return jsonify({'message': 'Project not found'}), 404
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
        # Viewable by participants and members of the exchange's sphere; the
        # flags tell the client what this viewer is allowed to change.
        tx_dict, is_initiator, is_other = _load_visible_exchange(exchange_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Exchange not found'}), 404
        tx_dict['receipt_photo_count'] = MeaningTrail.receipt_photo_count(exchange_id)
        tx_dict['is_finished'] = MeaningTrail.is_finished(exchange_id)
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
# The only legal moves. Receipting happens through add_xc_comment (a receipt
# is what moves an exchange to 'Receipted'), never by setting status directly.
_TRANSITIONS = {
    'Initiated':   {'In Progress', 'Cancelled'},
    'In Progress': {'Finished', 'Cancelled'},
    'Finished':    set(),
    'Receipted':   set(),
    'Additional Comments Added': set(),
    'Cancelled':   set(),
}


@validate_session
def update_xc_status(exchange_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        new_status = data.get('status', '')
        if new_status not in _VALID_STATUSES:
            return jsonify({'message': 'Invalid status'}), 400

        tx_dict, is_initiator, is_other = _load_visible_exchange(exchange_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Exchange not found'}), 404
        if not (is_initiator or is_other):
            return jsonify({'message': 'Only participants can change the status'}), 403

        current = tx_dict.get('exchange_status') or 'Initiated'
        if new_status not in _TRANSITIONS.get(current, set()):
            return jsonify({'message': f'Cannot move an exchange from {current} to {new_status}',
                            'status': current}), 409

        if not MeaningTrail.set_status_for(tx_dict['user_id'], exchange_id, new_status):
            return jsonify({'message': 'Failed to update status'}), 500
        return jsonify({'message': 'Status updated', 'status': new_status}), 200
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

        tx_dict, is_initiator, is_other = _load_visible_exchange(exchange_id, user_id)
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
        # The single acknowledgement slot is first-come: never overwrite it.
        if comment_type == 'other' and tx_dict.get('other_comment'):
            return jsonify({'message': 'This exchange already has an acknowledgement'}), 409

        author_name = None
        if comment_type in ('other', 'gratitude'):
            from app.models.user import User
            u = User.get(str(user_id))
            if u:
                author_name = f"{u.name or ''} {u.surname or ''}".strip() or u.email

        ok = MeaningTrail.add_comment_for(
            tx_dict['user_id'], exchange_id, comment_type, text,
            author_id=str(user_id), author_name=author_name,
            cards=cards if cards else None,
            context=(data.get('context') or None),
        )
        if ok:
            if comment_type == 'gratitude':
                # Notify whoever can read a notification: for an entity-
                # initiated exchange, that's the human who acted on its
                # behalf, not the entity's own id.
                notify_target = tx_dict.get('initiator_acting_user_id') or tx_dict['user_id']
                Notification.create(
                    user_id=notify_target, actor_id=user_id, actor_name=author_name,
                    type_='receipt_received',
                    message=f'{author_name} left you a receipt',
                    link=f'/exchange?id={exchange_id}',
                )
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
        tx_dict, _, _ = _load_visible_exchange(exchange_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Exchange not found'}), 404

        liked, count = Likes.toggle(exchange_id, comment_type, user_id)
        return jsonify({'liked': liked, 'count': count, 'comment_type': comment_type}), 200
    except Exception as e:
        logger.error(f"Error in like_exchange: {e}")
        return jsonify({'message': 'Internal server error'}), 500
