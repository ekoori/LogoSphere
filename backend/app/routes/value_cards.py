# Routes: Value Cards API
# GET    /api/value_cards/<owner_id> — members (signed out: only a public sphere's charter)
# POST   /api/value_cards             — authenticated, creates a card for the session user
# PATCH  /api/value_cards/<card_id>   — authenticated, edits own card (versioned, see below)
# DELETE /api/value_cards/<card_id>   — authenticated, deletes own card
#
# Edits never mutate a card's stored history: ValueCard.update() writes the
# change as a new row and flips the old row to is_current=False rather than
# overwriting it, so anything that already captured the old wording (e.g. a
# meaning-trail comment snapshot) keeps showing it as it was.

import logging
from flask import request, jsonify, current_app as app
from app.models.value_card import ValueCard
from app.utils.permissions import can_manage_entity as _can_manage_entity, get_entity_info
from app.middleware.session_middleware import validate_session, optional_session
from app.utils.access import Sight

logger = logging.getLogger(__name__)


def _may_write_entity_cards(entity_id, user_id):
    """Who may write an entity's value cards: managers of a real sphere,
    alliance or project (or a platform admin). Never a person's Meaning Graph,
    which only its owner writes - can_manage_entity alone is true for a
    platform admin on ANY id, people included."""
    return get_entity_info(entity_id) is not None and _can_manage_entity(entity_id, user_id)


@optional_session
def get_value_cards(target_user_id, user_id=None):
    """Members read each other's cards and the charters of groups they may
    see. Signed out, only a public sphere's charter."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        verdict = Sight(user_id).value_cards(target_user_id)
        if verdict == 'signin':
            return jsonify({'message': 'Sign in to see these value cards'}), 401
        if verdict == 'hidden':
            return jsonify({'message': 'Not found'}), 404
        cards = ValueCard.get_for_user(target_user_id)
        return jsonify([c.to_dict() for c in cards]), 200
    except Exception as e:
        logger.error(f'Error fetching value cards: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def create_value_card(user_id=None):
    """Authenticated — creates a card for the session user."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        if not data.get('care_about'):
            return jsonify({'message': 'care_about is required'}), 400
        card = ValueCard.create(data, user_id)
        return jsonify(card.to_dict()), 201
    except Exception as e:
        logger.error(f'Error creating value card: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def edit_value_card(card_id, user_id=None):
    """Authenticated — only the card owner can edit their own card."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        card = ValueCard.update(user_id, card_id, data)
        if not card:
            return jsonify({'message': 'Value card not found'}), 404
        return jsonify(card.to_dict()), 200
    except Exception as e:
        logger.error(f'Error editing value card: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def delete_value_card(card_id, user_id=None):
    """Authenticated — only the card owner can delete."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        ValueCard.delete(user_id, card_id)
        return jsonify({'message': 'deleted'}), 200
    except Exception as e:
        logger.error(f'Error deleting value card: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def create_entity_value_card(entity_id, user_id=None):
    """Create a value card owned by an entity (sphere, alliance, project)."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        if not _may_write_entity_cards(entity_id, user_id):
            return jsonify({'message': 'Not authorized to manage this entity'}), 403
        data = request.get_json()
        if not data or not data.get('care_about'):
            return jsonify({'message': 'care_about is required'}), 400
        card = ValueCard.create(data, entity_id)
        return jsonify(card.to_dict()), 201
    except Exception as e:
        logger.error(f'Error creating entity value card: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def edit_entity_value_card(entity_id, card_id, user_id=None):
    """Edit a value card owned by an entity (sphere, alliance, project)."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        if not _may_write_entity_cards(entity_id, user_id):
            return jsonify({'message': 'Not authorized to manage this entity'}), 403
        data = request.get_json()
        if not data:
            return jsonify({'message': 'No data provided'}), 400
        card = ValueCard.update(entity_id, card_id, data)
        if not card:
            return jsonify({'message': 'Value card not found'}), 404
        return jsonify(card.to_dict()), 200
    except Exception as e:
        logger.error(f'Error editing entity value card: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def delete_entity_value_card(entity_id, card_id, user_id=None):
    """Delete a value card from an entity."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        if not _may_write_entity_cards(entity_id, user_id):
            return jsonify({'message': 'Not authorized to manage this entity'}), 403
        ValueCard.delete(entity_id, card_id)
        return jsonify({'message': 'deleted'}), 200
    except Exception as e:
        logger.error(f'Error deleting entity value card: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def clone_value_card(user_id=None):
    """Copy someone else's (or an entity's) value card onto your own Meaning
    Graph, or onto an entity you manage. The client sends the source card's
    field values directly (it already has them, having rendered the card) —
    this avoids an inefficient scan to look up a card by id alone, since
    value_cards is keyed by (owner_id, card_id) and a bare card_id doesn't
    identify a partition. Body: { source: {...card fields...}, target_id }."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        data = request.get_json() or {}
        source = data.get('source') or {}
        target_id = data.get('target_id')
        if not target_id:
            return jsonify({'message': 'target_id is required'}), 400
        if not source.get('care_about'):
            return jsonify({'message': 'Invalid source card'}), 400

        # Authorized targets: yourself, or an entity (sphere/alliance/project)
        # you manage — never an arbitrary other user or entity.
        is_self = str(target_id) == str(user_id)
        if not is_self and not _may_write_entity_cards(target_id, user_id):
            return jsonify({'message': 'Not authorized to add a value card there'}), 403

        clone_data = {
            'title': source.get('title', ''),
            'care_about': source.get('care_about', ''),
            'because': source.get('because', ''),
            'looks_like': source.get('looks_like') or [],
            'drift_looks_like': source.get('drift_looks_like', ''),
            'in_conflict': source.get('in_conflict', ''),
            'never_do': source.get('never_do', ''),
            'frankl_mode': source.get('frankl_mode', 'creative'),
            'color_key': source.get('color_key', 'honey'),
        }
        card = ValueCard.create(clone_data, target_id)
        return jsonify(card.to_dict()), 201
    except Exception as e:
        logger.error(f'Error cloning value card: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def endorse_value_card(card_id, user_id=None):
    """Owner endorses their own card on reflection (also marks it reviewed)."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        card = ValueCard.endorse(user_id, card_id)
        if not card:
            return jsonify({'message': 'Value card not found'}), 404
        return jsonify(card.to_dict()), 200
    except Exception as e:
        logger.error(f'Error endorsing value card: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def review_value_card(card_id, user_id=None):
    """Owner re-read the card and keeps it - resets the review cadence."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        card = ValueCard.mark_reviewed(user_id, card_id)
        if not card:
            return jsonify({'message': 'Value card not found'}), 404
        return jsonify(card.to_dict()), 200
    except Exception as e:
        logger.error(f'Error reviewing value card: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def endorse_entity_value_card(entity_id, card_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        if not _may_write_entity_cards(entity_id, user_id):
            return jsonify({'message': 'Not authorized to manage this entity'}), 403
        card = ValueCard.endorse(entity_id, card_id)
        if not card:
            return jsonify({'message': 'Value card not found'}), 404
        return jsonify(card.to_dict()), 200
    except Exception as e:
        logger.error(f'Error endorsing entity value card: {e}')
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def review_entity_value_card(entity_id, card_id, user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        if not _may_write_entity_cards(entity_id, user_id):
            return jsonify({'message': 'Not authorized to manage this entity'}), 403
        card = ValueCard.mark_reviewed(entity_id, card_id)
        if not card:
            return jsonify({'message': 'Value card not found'}), 404
        return jsonify(card.to_dict()), 200
    except Exception as e:
        logger.error(f'Error reviewing entity value card: {e}')
        return jsonify({'message': 'Internal server error'}), 500
