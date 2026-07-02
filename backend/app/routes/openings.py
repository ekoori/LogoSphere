import logging
import uuid
from flask import request, jsonify, current_app as app
from app.models.openings import Service
from app.models.user import User
from app.models.meaning_trail import MeaningTrail
from app.models.spheres import Sphere
from app.utils.permissions import can_manage_entity, get_entity_info
from app.utils.validation import is_supported_image
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


def _is_provider_or_manager(service, user_id):
    """True if `user_id` is the opening's provider, or — when the opening was
    posted on behalf of a sphere/alliance/project (provider_id is the entity's
    own id) — a human who manages that entity."""
    if str(service.provider_id) == str(user_id):
        return True
    return can_manage_entity(service.provider_id, user_id)


def _enrich_service(s, viewer):
    """Build the full dict for one service, including viewer-relative fields.
    Shared by the list and single-item endpoints."""
    sid = s.service_id
    is_provider = viewer is not None and _is_provider_or_manager(s, viewer)
    d = s.to_dict()
    d['likes'] = Service.like_count(sid)
    d['liked_by_current_user'] = Service.is_liked_by(sid, viewer) if viewer else False
    d['pending_acceptances'] = Service.acceptances(sid, status='pending') if is_provider else []
    d['my_acceptance'] = Service.get_acceptance(sid, viewer) if viewer else None
    d['activity'] = Service.activity_summary(sid, s.provider_id) if s.cadence == 'perpetual' else None
    return d


@validate_session
def create_service(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        if not data.get('title'):
            return jsonify({'message': 'Service title is required'}), 400

        # An opening may be posted "as" a sphere/alliance/project instead of
        # the human posting it — the entity becomes the provider, so the
        # opening (and any exchange it spawns) lives under the entity's own
        # identity rather than the manager's personal profile.
        acting_as_id = data.get('acting_as_id')
        if acting_as_id:
            if not can_manage_entity(acting_as_id, user_id):
                return jsonify({'message': 'Not authorized to post on behalf of this entity'}), 403
            info = get_entity_info(acting_as_id)
            if not info:
                return jsonify({'message': 'Unknown entity'}), 400
            provider_id = uuid.UUID(str(acting_as_id))
            data = {**data, 'provider_name': info['name']}
        else:
            provider_id = uuid.UUID(str(user_id))

        new_service = Service.create(data=data, provider_id=provider_id)
        logger.info(f"Created service {new_service.service_id}")
        return jsonify(new_service.to_dict()), 201
    except Exception as e:
        logger.error(f"Error in create_service: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def get_services(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        viewer = uuid.UUID(str(user_id)) if user_id else None
        joined_spheres = Sphere.member_sphere_ids(viewer)
        services = []
        for s in Service.get_all():
            is_provider = viewer is not None and _is_provider_or_manager(s, viewer)

            # A single opening disappears from the marketplace once it has been
            # confirmed (status advanced past Accepted). Its participants still
            # reach the exchange from their meaning trail.
            if s.cadence != 'perpetual' and s.status in ('In Progress', 'Completed'):
                continue

            # Sphere-scoped openings are only visible to that sphere's members
            # (a member sees their own opening regardless). Standalone openings
            # (no sphere_id) remain visible to everyone.
            if s.sphere_id and s.sphere_id not in joined_spheres and not is_provider:
                continue

            services.append(_enrich_service(s, viewer))
        logger.info(f"Retrieved {len(services)} services")
        return jsonify(services), 200
    except Exception as e:
        logger.error(f"Error in get_services: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def get_service(service_id, user_id=None):
    """Single-opening fetch for the detail page. Visible to anyone who could
    see it in the list (sphere members / provider), or once it's already
    progressed past the marketplace (its own participants still reach it)."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        service_uuid = uuid.UUID(service_id)
        service = Service.get_by_id(service_uuid)
        if not service:
            return jsonify({'message': 'Opening not found'}), 404

        viewer = uuid.UUID(str(user_id))
        is_provider = _is_provider_or_manager(service, viewer)
        if service.sphere_id and not is_provider:
            joined_spheres = Sphere.member_sphere_ids(viewer)
            if service.sphere_id not in joined_spheres:
                return jsonify({'message': 'Not authorized to view this opening'}), 403

        return jsonify(_enrich_service(service, viewer)), 200
    except ValueError:
        return jsonify({'message': 'Invalid opening id'}), 400
    except Exception as e:
        logger.error(f"Error in get_service: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def accept_service(service_id, user_id=None):
    """Step 1 of two — the recipient signals acceptance. This records a pending
    acceptance; the exchange is only created once the provider confirms."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        service_uuid = uuid.UUID(service_id)
        service = Service.get_by_id(service_uuid)
        if not service:
            return jsonify({'message': 'Opening not found'}), 404
        if _is_provider_or_manager(service, user_id):
            return jsonify({'message': 'You cannot accept your own opening'}), 400
        if service.status in ('Completed', 'Cancelled'):
            return jsonify({'message': 'This opening is no longer open'}), 409
        # A single opening can only be locked to one accepter.
        if service.cadence != 'perpetual' and service.status == 'Accepted' \
                and str(getattr(service, 'accepted_by', '')) != str(user_id):
            return jsonify({'message': 'This opening has already been accepted'}), 409

        existing = Service.get_acceptance(service_uuid, uuid.UUID(str(user_id)))
        if existing:
            msg = 'Already confirmed' if existing['status'] == 'confirmed' else 'Awaiting confirmation'
            return jsonify({'message': msg, 'acceptance': existing}), 200

        accepter = User.get(str(user_id))
        if not accepter:
            return jsonify({'message': 'User not found'}), 404
        accepter_name = f"{accepter.name or ''} {accepter.surname or ''}".strip() or accepter.email

        Service.record_acceptance(service_uuid, uuid.UUID(str(user_id)), accepter_name)
        if service.cadence != 'perpetual':
            Service.mark_accepted(service_uuid, uuid.UUID(str(user_id)), accepter_name)

        logger.info(f"Opening {service_id} accepted (pending) by {user_id}")
        return jsonify({
            'message': 'Acceptance recorded — awaiting the provider\'s confirmation',
            'status': 'pending',
        }), 200
    except ValueError:
        return jsonify({'message': 'Invalid opening id'}), 400
    except Exception as e:
        logger.error(f"Error in accept_service: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def confirm_service(service_id, user_id=None):
    """Step 2 of two — the provider confirms a pending acceptance, which creates
    the exchange between the two of them. Single openings then leave the list."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        service_uuid = uuid.UUID(service_id)
        data = request.get_json() or {}
        accepter_id = data.get('accepter_id')
        if not accepter_id:
            return jsonify({'message': 'accepter_id is required'}), 400
        accepter_uuid = uuid.UUID(str(accepter_id))

        service = Service.get_by_id(service_uuid)
        if not service:
            return jsonify({'message': 'Opening not found'}), 404
        if not _is_provider_or_manager(service, user_id):
            return jsonify({'message': 'Only the provider can confirm acceptances'}), 403

        acceptance = Service.get_acceptance(service_uuid, accepter_uuid)
        if not acceptance:
            return jsonify({'message': 'No such acceptance'}), 404
        if acceptance['status'] == 'confirmed':
            return jsonify({'message': 'Already confirmed',
                            'exchange_id': acceptance['exchange_id']}), 200

        exchange_id = MeaningTrail.create_for_opening(
            initiator_id=service.provider_id,
            other_user_id=accepter_uuid,
            other_user_name=acceptance['accepter_name'],
            description=service.title,
            project_name=service.project_name,
        )
        if not exchange_id:
            return jsonify({'message': 'Failed to create exchange'}), 500

        Service.mark_confirmed(service_uuid, accepter_uuid, exchange_id)
        # A single opening is now spoken for and leaves the marketplace.
        if service.cadence != 'perpetual':
            Service.set_status(service_uuid, 'In Progress')

        logger.info(f"Opening {service_id} confirmed for {accepter_id}, exchange {exchange_id}")
        return jsonify({'message': 'Confirmed', 'exchange_id': str(exchange_id)}), 200
    except ValueError:
        return jsonify({'message': 'Invalid id'}), 400
    except Exception as e:
        logger.error(f"Error in confirm_service: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def reject_service(service_id, user_id=None):
    """The provider declines a pending acceptance. The acceptance is removed and,
    for a single opening, the opening reopens for others."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        service_uuid = uuid.UUID(service_id)
        data = request.get_json() or {}
        accepter_id = data.get('accepter_id')
        if not accepter_id:
            return jsonify({'message': 'accepter_id is required'}), 400
        accepter_uuid = uuid.UUID(str(accepter_id))

        service = Service.get_by_id(service_uuid)
        if not service:
            return jsonify({'message': 'Opening not found'}), 404
        if not _is_provider_or_manager(service, user_id):
            return jsonify({'message': 'Only the provider can reject acceptances'}), 403

        acceptance = Service.get_acceptance(service_uuid, accepter_uuid)
        if not acceptance:
            return jsonify({'message': 'No such acceptance'}), 404
        if acceptance['status'] == 'confirmed':
            return jsonify({'message': 'This acceptance is already confirmed'}), 409

        Service.remove_acceptance(service_uuid, accepter_uuid)
        if service.cadence != 'perpetual':
            Service.reopen(service_uuid)

        logger.info(f"Opening {service_id} acceptance by {accepter_id} rejected")
        return jsonify({'message': 'Acceptance declined'}), 200
    except ValueError:
        return jsonify({'message': 'Invalid id'}), 400
    except Exception as e:
        logger.error(f"Error in reject_service: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def like_service(service_id, user_id=None):
    """Toggle the current user's like on an opening. Returns {liked, likes}."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        service_uuid = uuid.UUID(service_id)
        if not Service.get_by_id(service_uuid):
            return jsonify({'message': 'Opening not found'}), 404
        liked, count = Service.toggle_like(service_uuid, uuid.UUID(str(user_id)))
        return jsonify({'liked': liked, 'likes': count}), 200
    except ValueError:
        return jsonify({'message': 'Invalid opening id'}), 400
    except Exception as e:
        logger.error(f"Error in like_service: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def update_service_image(service_id, user_id=None):
    """Set the opening's banner image — the provider, or a human managing the
    entity that provided it, can do this from the opening's own page."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        service_uuid = uuid.UUID(service_id)
        service = Service.get_by_id(service_uuid)
        if not service:
            return jsonify({'message': 'Opening not found'}), 404
        if not _is_provider_or_manager(service, user_id):
            return jsonify({'message': 'Not authorized to manage this opening'}), 403
        image_file = request.files.get('image')
        if not image_file:
            return jsonify({'message': 'image file is required'}), 400
        image_bytes = image_file.read()
        if not is_supported_image(image_bytes):
            return jsonify({'message': 'Unsupported image format (use JPEG, PNG, GIF or WebP)'}), 400
        Service.set_image(service_uuid, image_bytes)
        return jsonify({'message': 'Image updated'}), 200
    except ValueError:
        return jsonify({'message': 'Invalid opening id'}), 400
    except Exception as e:
        logger.error(f"Error in update_service_image: {e}")
        return jsonify({'message': 'Internal server error'}), 500
