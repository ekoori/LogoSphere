# Value cards (the Meaning Graph): a person's own cards, versioned edits,
# endorsement and review, cloning, and the cards of spheres/alliances/projects.
# Only a card's owner - or, for an entity, its managers - may write it; a
# platform admin's manage-anything override never reaches a person's graph.
import uuid

import pytest

from conftest import TOOL_LIBRARY

CARD = {
    'title': 'Test value (delete me)', 'care_about': 'Leaving things better than I found them',
    'because': 'Testing', 'looks_like': ['Cleaning up after tests'], 'frankl_mode': 'creative', 'color_key': 'leaf',
}


@pytest.fixture
def made_cards(db):
    """Collects (owner_id, card_id) of cards a test creates; deletes them after."""
    made = []
    yield made
    for owner, card in made:
        db.execute('DELETE FROM value_cards WHERE user_id = %s AND card_id = %s', [uuid.UUID(owner), uuid.UUID(card)])


def test_personal_card_lifecycle(api, made_cards):
    marie = api.uid('marie')
    assert api.post('/api/value_cards', who='marie', json={'title': 'No substance'})[0] == 400   # care_about required

    status, card = api.post('/api/value_cards', who='marie', json=CARD)
    assert status == 201 and card['user_id'] == marie and card['is_current'] is True
    made_cards.append((marie, card['card_id']))
    _, cards = api.get(f'/api/value_cards/{marie}', who='david')
    assert any(c['card_id'] == card['card_id'] for c in cards)

    # An edit is a new version; the old one is kept, no longer current.
    status, edited = api.patch(f"/api/value_cards/{card['card_id']}", who='marie', json={'title': 'Test value v2'})
    assert status == 200 and edited['title'] == 'Test value v2' and edited['replaces_card_id'] == card['card_id']
    made_cards.append((marie, edited['card_id']))
    _, cards = api.get(f'/api/value_cards/{marie}', who='marie')
    ids = [c['card_id'] for c in cards]
    assert edited['card_id'] in ids and card['card_id'] not in ids

    status, endorsed = api.post(f"/api/value_cards/{edited['card_id']}/endorse", who='marie')
    assert status == 200 and endorsed['endorsed'] is True and endorsed['needs_review'] is False
    status, reviewed = api.post(f"/api/value_cards/{edited['card_id']}/review", who='marie')
    assert status == 200 and reviewed['reviewed_at']

    status, _ = api.delete(f"/api/value_cards/{edited['card_id']}", who='marie')
    assert status == 200
    _, cards = api.get(f'/api/value_cards/{marie}', who='marie')
    assert edited['card_id'] not in [c['card_id'] for c in cards]


def test_only_the_owner_edits_their_cards(api, made_cards):
    marie = api.uid('marie')
    _, card = api.post('/api/value_cards', who='marie', json=CARD)
    made_cards.append((marie, card['card_id']))
    # Someone else (even a platform admin) addresses only their own partition: not found.
    assert api.patch(f"/api/value_cards/{card['card_id']}", who='admin', json={'title': 'hijack'})[0] == 404
    assert api.post(f"/api/value_cards/{card['card_id']}/endorse", who='david')[0] == 404
    api.delete(f"/api/value_cards/{card['card_id']}", who='david')
    _, cards = api.get(f'/api/value_cards/{marie}', who='marie')
    assert card['card_id'] in [c['card_id'] for c in cards]


def test_clone_onto_yourself_or_a_group_you_manage(api, made_cards):
    marie, david, admin = api.uid('marie'), api.uid('david'), api.uid('admin')
    status, mine = api.post('/api/value_cards/clone', who='marie', json={'source': CARD, 'target_id': marie})
    assert status == 201 and mine['user_id'] == marie
    made_cards.append((marie, mine['card_id']))
    # Not onto another person - and not by a platform admin either.
    assert api.post('/api/value_cards/clone', who='marie', json={'source': CARD, 'target_id': david})[0] == 403
    assert api.post('/api/value_cards/clone', who='admin', json={'source': CARD, 'target_id': marie})[0] == 403
    # Onto a project the caller manages.
    status, onto_project = api.post('/api/value_cards/clone', who='admin', json={'source': CARD, 'target_id': TOOL_LIBRARY})
    assert status == 201 and onto_project['user_id'] == TOOL_LIBRARY
    made_cards.append((TOOL_LIBRARY, onto_project['card_id']))
    assert api.post('/api/value_cards/clone', who='admin', json={'source': {}, 'target_id': admin})[0] == 400


def test_entity_cards_are_for_its_managers(api, made_cards):
    # David is a member of Riverside but doesn't manage the Tool Library.
    assert api.post(f'/api/entity_value_cards/{TOOL_LIBRARY}', who='david', json=CARD)[0] == 403
    status, card = api.post(f'/api/entity_value_cards/{TOOL_LIBRARY}', who='admin', json=CARD)
    assert status == 201 and card['user_id'] == TOOL_LIBRARY
    made_cards.append((TOOL_LIBRARY, card['card_id']))

    status, edited = api.patch(f"/api/entity_value_cards/{TOOL_LIBRARY}/{card['card_id']}", who='admin',
                               json={'title': 'Test entity value v2'})
    assert status == 200 and edited['replaces_card_id'] == card['card_id']
    made_cards.append((TOOL_LIBRARY, edited['card_id']))
    assert api.post(f"/api/entity_value_cards/{TOOL_LIBRARY}/{edited['card_id']}/endorse", who='admin')[1]['endorsed'] is True
    assert api.post(f"/api/entity_value_cards/{TOOL_LIBRARY}/{edited['card_id']}/review", who='admin')[0] == 200
    assert api.delete(f"/api/entity_value_cards/{TOOL_LIBRARY}/{edited['card_id']}", who='david')[0] == 403
    assert api.delete(f"/api/entity_value_cards/{TOOL_LIBRARY}/{edited['card_id']}", who='admin')[0] == 200


def test_entity_card_routes_never_write_a_persons_graph(api):
    """Regression: can_manage_entity is true for a platform admin on ANY id, so
    these routes let an admin write value cards onto a person's Meaning Graph."""
    marie = api.uid('marie')
    assert api.post(f'/api/entity_value_cards/{marie}', who='admin', json=CARD)[0] == 403
    _, cards = api.get(f'/api/value_cards/{marie}', who='marie')
    assert all(c['title'] != CARD['title'] for c in cards)
