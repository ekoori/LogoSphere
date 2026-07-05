import logging
import uuid
from flask import request, jsonify, current_app as app
from app.models.openings import Service
from app.models.user import User
from app.models.meaning_trail import MeaningTrail
from app.models.spheres import Sphere
from app.utils.permissions import can_manage_entity, get_entity_info, entity_sphere_ids
from app.utils.validation import is_supported_image, entity_image_response
from app.middleware.session_middleware import validate_session
from app.models.notification import Notification

logger = logging.getLogger(__name__)


def _is_provider_or_manager(service, user_id):
    """True if `user_id` is the opening's provider, or — when the opening was
    posted on behalf of a sphere/alliance/project (provider_id is the entity's
    own id) — a human who manages that entity."""
    if str(service.provider_id) == str(user_id):
        return True
    return can_manage_entity(service.provider_id, user_id)


def _enrich_service(s, viewer, include_exchanges=False):
    """Build the full dict for one service, including viewer-relative fields.
    Shared by the list and single-item endpoints. `include_exchanges` adds the
    confirmed exchanges spawned from this opening (single-opening page only —
    it's an extra per-opening query we don't want in the marketplace list)."""
    sid = s.service_id
    is_provider = viewer is not None and _is_provider_or_manager(s, viewer)
    # The banner image is served separately via GET /api/openings/<id>/image
    # (see has_image) so it never bloats the list/detail JSON.
    d = s.to_dict(include_image=False)
    d['likes'] = Service.like_count(sid)
    d['liked_by_current_user'] = Service.is_liked_by(sid, viewer) if viewer else False
    d['pending_acceptances'] = Service.acceptances(sid, status='pending') if is_provider else []
    # Resolve the viewer's own acceptance even when they accepted on behalf of
    # an entity (the row is keyed by the entity, not the human).
    d['my_acceptance'] = Service.acceptance_for_actor(sid, viewer) if viewer else None
    d['activity'] = Service.activity_summary(sid, s.provider_id) if s.cadence == 'perpetual' else None
    if include_exchanges:
        d['exchanges'] = Service.acceptances(sid, status='confirmed')
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
            # Record which human posted on the entity's behalf → "Joe on behalf
            # of <Entity>" — the entity is the provider, but the act is attributed.
            actor = User.get(str(user_id))
            actor_name = None
            if actor:
                actor_name = f"{actor.name or ''} {actor.surname or ''}".strip() or actor.email
            data = {**data, 'provider_name': info['name'],
                    'acting_user_id': str(user_id), 'acting_user_name': actor_name}
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

        return jsonify(_enrich_service(service, viewer, include_exchanges=True)), 200
    except ValueError:
        return jsonify({'message': 'Invalid opening id'}), 400
    except Exception as e:
        logger.error(f"Error in get_service: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def accept_service(service_id, user_id=None):
    """Step 1 of two — the recipient signals acceptance. This records a pending
    acceptance; the exchange is only created once the provider confirms.

    A human may accept on behalf of an alliance or project they manage by
    passing `acting_as_id`: the entity becomes the accepter (and the party in
    the resulting exchange), with the human recorded as having acted for it.
    The acting entity must belong to the opening's sphere when the opening is
    sphere-scoped — an entity can only act inside spheres it's part of."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        service_uuid = uuid.UUID(service_id)
        service = Service.get_by_id(service_uuid)
        if not service:
            return jsonify({'message': 'Opening not found'}), 404
        if _is_provider_or_manager(service, user_id):
            return jsonify({'message': 'You cannot accept your own opening'}), 400
        # A single opening stays open to everyone until the provider confirms one
        # acceptance (which moves it to 'In Progress' and out of the marketplace);
        # only then — or if completed/cancelled — is it closed to new accepters.
        if service.status in ('Completed', 'Cancelled') or \
                (service.cadence != 'perpetual' and service.status == 'In Progress'):
            return jsonify({'message': 'This opening is no longer open'}), 409

        # Optionally accept "as" an alliance/project the caller manages.
        data = request.get_json(silent=True) or {}
        acting_as_id = data.get('acting_as_id')
        acting_user_id = None
        acting_user_name = None
        if acting_as_id:
            info = get_entity_info(acting_as_id)
            if not info or info['kind'] not in ('alliance', 'project'):
                return jsonify({'message': 'You can only accept as an alliance or project'}), 400
            if str(acting_as_id) == str(service.provider_id):
                return jsonify({'message': 'This entity posted the opening — it can\'t accept it'}), 400
            if not can_manage_entity(acting_as_id, user_id):
                return jsonify({'message': 'Not authorized to accept on behalf of this entity'}), 403
            # The entity must be within the opening's sphere (if it has one).
            if service.sphere_id and str(service.sphere_id) not in entity_sphere_ids(acting_as_id):
                return jsonify({'message': f"This {info['kind']} isn't part of the opening's sphere"}), 400
            accepter_uuid = uuid.UUID(str(acting_as_id))
            accepter_name = info['name']
            acting_user_id = uuid.UUID(str(user_id))
            actor = User.get(str(user_id))
            if actor:
                acting_user_name = f"{actor.name or ''} {actor.surname or ''}".strip() or actor.email
        else:
            accepter_uuid = uuid.UUID(str(user_id))
            accepter = User.get(str(user_id))
            if not accepter:
                return jsonify({'message': 'User not found'}), 404
            accepter_name = f"{accepter.name or ''} {accepter.surname or ''}".strip() or accepter.email

        # One acceptance per actor. The opening is NOT locked here — it stays
        # available to others until the provider confirms one of the pending
        # acceptances (see confirm_service).
        existing = Service.acceptance_for_actor(service_uuid, uuid.UUID(str(user_id)))
        if existing:
            msg = 'Already confirmed' if existing['status'] == 'confirmed' else 'Awaiting confirmation'
            return jsonify({'message': msg, 'acceptance': existing}), 200

        Service.record_acceptance(service_uuid, accepter_uuid, accepter_name,
                                  acting_user_id=acting_user_id, acting_user_name=acting_user_name)

        # Notify whoever can actually read a notification: for an opening
        # posted as an entity, that's the human who acted on its behalf
        # (acting_user_id), not the entity's own id — an entity has no inbox.
        notify_target = getattr(service, 'acting_user_id', None) or service.provider_id
        Notification.create(
            user_id=notify_target, actor_id=user_id, actor_name=accepter_name,
            type_='opening_accepted',
            message=f'{accepter_name} wants to accept your opening "{service.title}"',
            link=f'/opening?id={service_id}',
        )

        logger.info(f"Opening {service_id} accepted (pending) by {user_id} as {accepter_uuid}")
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
            acting_user_id=getattr(service, 'acting_user_id', None),
            acting_user_name=getattr(service, 'acting_user_name', None),
            long_description=getattr(service, 'description', None),
            image=getattr(service, 'image', None),
            # When the opening was accepted on behalf of an entity, carry the
            # human who accepted through to the exchange's recipient side.
            recipient_acting_user_id=acceptance.get('acting_user_id'),
            recipient_acting_user_name=acceptance.get('acting_user_name'),
            source_service_id=service_uuid,
        )
        if not exchange_id:
            return jsonify({'message': 'Failed to create exchange'}), 500

        Service.mark_confirmed(service_uuid, accepter_uuid, exchange_id)
        # A single opening is now spoken for and leaves the marketplace.
        if service.cadence != 'perpetual':
            Service.set_status(service_uuid, 'In Progress')

        confirmer = User.get(str(user_id))
        confirmer_name = (f"{confirmer.name or ''} {confirmer.surname or ''}".strip() or confirmer.email) if confirmer else service.provider_name
        # Notify the human on the accepter side — the one who acted for the
        # entity if it was an entity acceptance, else the accepter directly.
        notify_accepter = acceptance.get('acting_user_id') or accepter_uuid
        Notification.create(
            user_id=notify_accepter, actor_id=user_id, actor_name=confirmer_name,
            type_='opening_confirmed',
            message=f'Your acceptance of "{service.title}" was confirmed — the exchange has started',
            link=f'/exchange?id={exchange_id}',
        )

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


def get_service_image(service_id):
    """Serve an opening's banner image for <img src>. Public + cacheable —
    keeps the blob out of the openings list JSON (loaded lazily per card)."""
    try:
        return entity_image_response(Service.get_image(uuid.UUID(service_id)))
    except (ValueError, TypeError):
        return ('', 404)
    except Exception as e:
        logger.error(f"Error in get_service_image: {e}")
        return ('', 404)


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
