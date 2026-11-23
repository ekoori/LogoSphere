"""
File: ./backend/app/routes/meaning_trail.py
Description: Flask route file handling MeaningTrail operations. Auth is provided by
the Cassandra-backed @validate_session decorator (consistent with the other
routes), which injects the authenticated user_id.
Methods:
    [x] get_meaning_trail() : GET/POST '/meaning_trail' — fetch a user's trust trail.
"""

import logging
import uuid
from datetime import datetime, timedelta
from flask import request, jsonify, current_app as app, Response
from app.models.meaning_trail import MeaningTrail, Likes, LIKE_TYPES, own_like_targets

OWN_NOUN = {'exchange': 'exchange', 'gratitude': 'receipt', 'user': 'note', 'other': 'acknowledgement'}
from app.models.notification import Notification
from app.utils.validation import is_supported_image
from app.utils.pictures import picture_response
from app.middleware.session_middleware import validate_session
from app.models.spheres import Sphere
from app.utils.permissions import is_platform_admin
from app.utils.access import Sight, as_uuid, exchange_sphere, resolve_cards
from app.models.openings import Service
from app.utils import evidence

logger = logging.getLogger(__name__)


# ── Visibility ──────────────────────────────────────────────────────────────
# An exchange has no sphere column of its own; it inherits one from the opening
# it came from, or from its project (app/utils/access.py). Participants (and
# platform admins) always see it; anyone else must belong to that sphere.
# Exchanges with no resolvable sphere (legacy/direct ones) stay visible to any
# signed-in member.
def _can_view_exchange(tx_dict, is_participant, viewer_id):
    if is_participant or is_platform_admin(viewer_id):
        return True
    sphere_id = exchange_sphere(tx_dict)
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
    """Exchange pictures and receipt photos: private (behind the exchange's
    permission check), labelled with their content (see app/utils/pictures)."""
    return picture_response(data, private=True)


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
                refused = evidence.refusal(tx_dict, [image])
                if refused:
                    return jsonify({'message': refused}), 400
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
        if tx_dict is None or not tx_dict.get('has_image'):
            return ('', 404)
        return _image_response(MeaningTrail.get_image(exchange_id))
    except Exception as e:
        logger.error(f"Error in get_exchange_image: {e}")
        return ('', 404)


# A receipt may say about how long it took: a quarter of an hour to 100 hours.
HOURS_MIN, HOURS_MAX = 0.25, 100

# Photos are sent just after the receipt that may itself finish the exchange.
PHOTOS_FOLLOW_RECEIPT = timedelta(hours=1)


def _evidence_is_settled(tx_dict, exchange_id):
    """Receipt photos are evidence: once the exchange is finished they may be
    added once, soon after the receipt, and never replaced."""
    if not MeaningTrail.is_finished(exchange_id):
        return False
    if MeaningTrail.receipt_photo_count(exchange_id):
        return True
    written = tx_dict.get('gratitude_comment_timestamp')
    return not written or datetime.utcnow() - datetime.fromisoformat(written) > PHOTOS_FOLLOW_RECEIPT


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
        if _evidence_is_settled(tx_dict, exchange_id):
            return jsonify({'message': "This exchange is finished: its receipt photos can't be changed"}), 409
        images = []
        for f in request.files.getlist('photos')[:3]:
            b = f.read()
            if b and is_supported_image(b):
                images.append(b)
        # All or none: a receipt doesn't half-arrive.
        refused = evidence.refusal(tx_dict, images)
        if refused:
            return jsonify({'message': refused}), 400
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
        photo = MeaningTrail.get_receipt_photo(exchange_id, idx)
        if photo and not evidence.photo_may_show(tx_dict, photo):
            return ('', 404)
        return _image_response(photo)
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
    # get_meaning_trail returns [] for an empty trail and None on error (an
    # outage raises, and the app answers 503). An error is not "not found".
    if trust_trail is None:
        return jsonify({'message': 'Could not load the Meaning Trail'}), 500
    # Someone else's trail shows only what could be opened one by one.
    sight = Sight(user_id)
    return jsonify([row for row in trust_trail if sight.exchange(row)]), 200


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
    sight = Sight(user_id)
    rows = MeaningTrail.get_by_project_id(project_id, viewer_id=user_id)
    return jsonify([row for row in rows if sight.exchange(row)]), 200


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
        source = as_uuid(tx_dict.get('source_service_id'))
        tx_dict['borrow'] = bool(source) and Service.is_loan(source)
        from app.utils.trails import Trail
        as_trail = Trail(tx_dict['exchange_id'], 'exchange', '', tx_dict, exchange_sphere(tx_dict))
        return jsonify({
            'exchange': tx_dict,
            'can_acknowledge': as_trail.writable(Sight(user_id)),
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


def _hours(given):
    """(hours to the nearest quarter, None) or (None, what's wrong). Nothing given is fine."""
    if given is None or given == '':
        return None, None
    if isinstance(given, bool):
        return None, 'Say the hours as a number, or leave them out.'
    try:
        hours = float(given)
    except (TypeError, ValueError):
        return None, 'Say the hours as a number, or leave them out.'
    if not HOURS_MIN <= hours <= HOURS_MAX:
        return None, f'Hours go from a quarter of an hour to {HOURS_MAX:g}.'
    return round(hours * 4) / 4, None


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

        # An exchange takes any number of acknowledgements, by anyone in its
        # sphere or either side (app/routes/trails.py).
        if comment_type == 'other':
            from app.routes.trails import add_acknowledgement
            named = data.get('card_ids') or [c.get('card_id') for c in cards if isinstance(c, dict)]
            body, code = add_acknowledgement(exchange_id, user_id, text, named)
            if code == 201:
                return jsonify({**body, 'message': 'Comment added'}), 200
            return jsonify(body), code

        # Receipts and the initiator note are participant-only.
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
        if comment_type == 'gratitude':
            from app.models.user import User
            u = User.get(str(user_id))
            if u:
                author_name = f"{u.name or ''} {u.surname or ''}".strip() or 'A member'

        # A comment may name the value card(s) it expressed: by id, so it pins
        # the exact version. The wording kept with it is the stored card's, not
        # whatever the client sent along.
        named = data.get('card_ids') or [c.get('card_id') for c in cards if isinstance(c, dict)]
        resolved = resolve_cards(named, [
            user_id, tx_dict.get('user_id'), tx_dict.get('other_user_id'),
            tx_dict.get('initiator_acting_user_id'), tx_dict.get('recipient_acting_user_id')])
        cards = [c.to_dict() for c in resolved]
        card_ids = [str(c.card_id) for c in resolved]
        frankl_mode = data.get('frankl_mode')
        if frankl_mode not in ('creative', 'experiential', 'attitudinal'):
            frankl_mode = None
        hours, wrong = _hours(data.get('hours')) if comment_type == 'gratitude' else (None, None)
        if wrong:
            return jsonify({'message': wrong}), 400
        ok = MeaningTrail.add_comment_for(
            tx_dict['user_id'], exchange_id, comment_type, text,
            author_id=str(user_id), author_name=author_name,
            cards=cards if cards else None,
            context=(data.get('context') or None),
            card_ids=card_ids if comment_type == 'gratitude' else None,
            frankl_mode=frankl_mode if comment_type == 'gratitude' else None,
            hours=hours,
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
        tx_dict, is_initiator, is_other = _load_visible_exchange(exchange_id, user_id)
        if tx_dict is None:
            return jsonify({'message': 'Exchange not found'}), 404

        if comment_type == 'other' and tx_dict.get('acknowledgements'):
            from app.routes.trails import like_acknowledgement
            body, code = like_acknowledgement(exchange_id, tx_dict['other_comment_id'], user_id)
            return jsonify({**body, 'comment_type': 'other'}), code

        # Appreciation is a signal from others: nobody likes what they made (an
        # old self-like can still be taken off).
        if comment_type in own_like_targets(tx_dict, user_id, is_initiator, is_other) and \
                not Likes.is_liked_by(exchange_id, comment_type, user_id):
            return jsonify({'message': f"You can't appreciate your own {OWN_NOUN[comment_type]}"}), 403

        liked, count = Likes.toggle(exchange_id, comment_type, user_id)
        return jsonify({'liked': liked, 'count': count, 'comment_type': comment_type,
                        'by': Likes.likers(exchange_id, comment_type)}), 200
    except Exception as e:
        logger.error(f"Error in like_exchange: {e}")
        return jsonify({'message': 'Internal server error'}), 500
