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
