"""The Meaning Graph, and how it is worked out.

  GET  /api/meaning_graph            the cards you may see, and how close they are
  GET  /api/meaning_graph/method     the method in full; no session needed
  POST /api/meaning_graph/judgement  {a, b, close: true|false|null}
"""
from flask import current_app as app, jsonify, request

from app.middleware.session_middleware import validate_session
from app.utils import closeness, meaning_graph
from app.utils.access import Sight
from app.utils.permissions import can_manage_entity


def _options():
    return app.make_default_options_response(), 200


@validate_session
def get_meaning_graph(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    return jsonify(meaning_graph.get_graph().for_viewer(Sight(user_id))), 200


def get_method():
    """Public: a method people can't read isn't a transparent one."""
    if request.method == 'OPTIONS':
        return _options()
    return jsonify({**closeness.method(), 'shown_from': meaning_graph.SHOWN_FROM,
                    'kept_from': meaning_graph.KEPT_FROM, 'kept_each': meaning_graph.KEPT_EACH}), 200


@validate_session
def post_judgement(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    data = request.get_json(silent=True) or {}
    a, b = str(data.get('a') or ''), str(data.get('b') or '')
    if 'close' not in data or (data['close'] is not None and not isinstance(data['close'], bool)):
        return jsonify({'message': 'close is true, false or null'}), 400
    if not a or a == b:
        return jsonify({'message': 'Pick two different cards'}), 400
    sight = Sight(user_id)
    graph = meaning_graph.get_graph(fresh=True)
    cards = [graph.cards.get(x) for x in (a, b)]
    if not all(c and graph.owners.visible(c.user_id, sight) for c in cards):
        return jsonify({'message': 'Not found'}), 404
    if not graph.owners.is_person(sight.id):
        return jsonify({'message': "AI personas don't judge"}), 403
    for card in cards:
        owner = graph.owners.all[card.user_id]
        own = card.user_id == sight.id or (
            owner['kind'] != 'user' and can_manage_entity(card.user_id, sight.id, include_platform_admin=False))
        if own:
            return jsonify({'message': "You don't judge a pair with your own card in it"}), 403
    meaning_graph.judge(a, b, sight.id, data['close'])
    pair = tuple(sorted((a, b)))
    return jsonify({'edge': meaning_graph.get_graph(fresh=True).edge(pair, sight.id)}), 200


def register(app_):
    meaning_graph.ensure_tables()
    app_.add_url_rule('/api/meaning_graph', view_func=get_meaning_graph, methods=['GET', 'OPTIONS'])
    app_.add_url_rule('/api/meaning_graph/method', view_func=get_method, methods=['GET', 'OPTIONS'])
    app_.add_url_rule('/api/meaning_graph/judgement', view_func=post_judgement, methods=['POST', 'OPTIONS'])
