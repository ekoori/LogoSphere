# Routes: Value Cards API
# GET  /api/value_cards/<user_id>  — public, returns all cards for a user
# POST /api/value_cards             — authenticated, creates a card for the session user
# DELETE /api/value_cards/<card_id> — authenticated, deletes own card

import logging
from flask import request, jsonify, current_app as app
from app.models.value_card import ValueCard
from app.utils.permissions import can_manage_entity as _can_manage_entity
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


def get_value_cards(target_user_id):
    """Public — no auth required."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
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
        if not _can_manage_entity(entity_id, user_id):
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
def delete_entity_value_card(entity_id, card_id, user_id=None):
    """Delete a value card from an entity."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        if not _can_manage_entity(entity_id, user_id):
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
        if not is_self and not _can_manage_entity(target_id, user_id):
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
