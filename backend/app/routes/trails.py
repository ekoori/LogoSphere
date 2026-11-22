"""Meaning Trails as one timeline, and the acknowledgements on them.

  GET    /api/trails/<id>                                     the timeline
  POST   /api/trails/<id>/acknowledgements                    {text, card_ids}
  DELETE /api/trails/<id>/acknowledgements/<ack>              author, trail owner, platform admin
  POST   /api/trails/<id>/acknowledgements/<ack>/like         {liked}
  POST   /api/trails/<id>/acknowledgements/<ack>/highlight    {highlighted}, the trail's owner

<id> is a person's, sphere's, alliance's, project's or exchange's.
"""
import logging

from flask import current_app as app, jsonify, request

from app.middleware.session_middleware import validate_session
from app.models.acknowledgement import MAX_CARDS, MAX_TEXT, Acknowledgement, ensure_tables
from app.models.meaning_trail import MeaningTrail
from app.models.notification import Notification
from app.utils import safety, timeline
from app.utils.access import Sight, resolve_cards
from app.utils.names import resolve_user_names
from app.utils.trails import Trail

logger = logging.getLogger(__name__)

NOT_FOUND = {'message': 'Not found'}


def _options():
    return app.make_default_options_response(), 200


def _open(trail_id, user_id):
    """(trail, sight), with trail None when it isn't there or isn't theirs to see."""
    sight = Sight(user_id)
    trail = Trail.find(trail_id)
    return (trail if trail and trail.readable(sight) else None), sight


def _run_dict(run, sight, names, owner):
    lit, kept = timeline.highlights(run), timeline.shown(run)
    items = []
    for a in run:
        d = a.to_dict(sight.id, names=names, highlighted=a.ack_id in lit, owner=owner, moderator=sight.admin)
        d['shown'] = a.ack_id in kept
        items.append(d)
    return {
        'type': 'acknowledgements',
        # The oldest one's id: stays put as newer ones join the run.
        'id': str(run[-1].ack_id),
        'at': items[0]['created_at'],
        'items': items,
        'folded': len(kept) < len(run),
    }


@validate_session
def get_trail(trail_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    trail, sight = _open(trail_id, user_id)
    if not trail:
        return jsonify(NOT_FOUND), 404
    entries = trail.chronology(sight)
    authors = {a.author_id for what, run in entries if what == 'run' for a in run if a.author_id}
    names = resolve_user_names(authors)
    owner = trail.owned(sight)
    people, kinds = MeaningTrail._name_map(), MeaningTrail._kind_map()
    out = []
    for what, thing in entries:
        if what == 'run':
            out.append(_run_dict(thing, sight, names, owner))
            continue
        # A person's trail reads from their side; a group's from each initiator's.
        whose = trail.id if trail.kind == 'user' else thing.user_id
        d = MeaningTrail._enrich(thing, whose, sight.id, people, kinds)
        out.append({'type': 'exchange', 'id': d['exchange_id'], 'at': d['project_start_timestamp'], 'exchange': d})
    return jsonify({
        'trail_id': str(trail.id), 'kind': trail.kind, 'name': trail.name,
        'can_acknowledge': trail.writable(sight), 'can_highlight': owner,
        'max_highlights': timeline.MAX_HIGHLIGHTS, 'entries': out,
    }), 200


def add_acknowledgement(trail_id, user_id, text, card_ids):
    """(body, status). The exchange page's older comment route lands here too."""
    trail, sight = _open(trail_id, user_id)
    if not trail:
        return NOT_FOUND, 404
    if not trail.writable(sight):
        return {'message': 'Join the sphere first to acknowledge here'}, 403
    # A person's trail, or an exchange of theirs, after a block either way.
    if trail.kind in ('user', 'exchange'):
        people = trail.people()
        if sight.id not in people and any(safety.between(sight.id, person) for person in people):
            return {'message': "You can't acknowledge here."}, 403
    text = text.strip() if isinstance(text, str) else ''
    if not text:
        return {'message': 'Write a few words first'}, 400
    if len(text) > MAX_TEXT:
        return {'message': f'Keep it under {MAX_TEXT} characters'}, 400
    cards = resolve_cards(card_ids, trail.card_owners(sight.id), limit=MAX_CARDS)
    author = resolve_user_names([sight.id]).get(sight.id) or 'A member'
    ack = Acknowledgement.create(trail.id, sight.id, author, text, [c.to_dict() for c in cards])
    what = {'user': f'{author} left an acknowledgement on your Meaning Trail',
            'exchange': f'{author} acknowledged your exchange "{trail.name}"'}.get(
        trail.kind, f"{author} left an acknowledgement on {trail.name}'s Meaning Trail")
    for person in trail.people():
        if person != sight.id:
            Notification.create(user_id=person, actor_id=sight.id, actor_name=author,
                                type_='acknowledgement', message=what, link=trail.link)
    return {'message': 'Acknowledgement added',
            'acknowledgement': ack.to_dict(sight.id, owner=trail.owned(sight), moderator=sight.admin)}, 201


@validate_session
def post_acknowledgement(trail_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    data = request.get_json(silent=True) or {}
    body, status = add_acknowledgement(trail_id, user_id, data.get('text'), data.get('card_ids'))
    return jsonify(body), status


@validate_session
def delete_acknowledgement(trail_id, ack_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    sight = Sight(user_id)
    trail = Trail.find(trail_id)
    ack = trail and Acknowledgement.find(trail.id, ack_id)
    if not ack:
        return jsonify(NOT_FOUND), 404
    # Its author may take it back even after leaving the sphere.
    if ack.author_id != sight.id and not sight.admin and not trail.owned(sight):
        if not trail.readable(sight):
            return jsonify(NOT_FOUND), 404
        return jsonify({'message': "Only its author or the trail's owner can remove it"}), 403
    ack.remove()
    return jsonify({'message': 'Acknowledgement removed'}), 200


def like_acknowledgement(trail_id, ack_id, user_id, liked=None):
    """(body, status); `liked` None toggles, for older clients."""
    trail, sight = _open(trail_id, user_id)
    ack = trail and Acknowledgement.find(trail.id, ack_id)
    if not ack:
        return NOT_FOUND, 404
    adding = liked if isinstance(liked, bool) else not ack.liked_by(sight.id)
    if adding and ack.author_id == sight.id:
        return {'message': "You can't appreciate your own acknowledgement"}, 403
    likes = ack.set_like(sight.id, adding)
    return {'liked': likes['liked'], 'count': likes['count'], 'by': likes['by']}, 200


@validate_session
def post_like(trail_id, ack_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    liked = (request.get_json(silent=True) or {}).get('liked')
    body, status = like_acknowledgement(trail_id, ack_id, user_id, liked)
    return jsonify(body), status


@validate_session
def post_highlight(trail_id, ack_id, user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    on = (request.get_json(silent=True) or {}).get('highlighted', True)
    if not isinstance(on, bool):
        return jsonify({'message': 'highlighted is true or false'}), 400
    trail, sight = _open(trail_id, user_id)
    if not trail:
        return jsonify(NOT_FOUND), 404
    if not trail.owned(sight):
        return jsonify({'message': 'Only the owner of this Meaning Trail can highlight'}), 403
    # Counted over the whole trail, not just what this person happens to see.
    entries = trail.chronology()
    ack = next((a for what, run in entries if what == 'run' for a in run if str(a.ack_id) == str(ack_id)), None)
    if not ack:
        return jsonify(NOT_FOUND), 404
    run = timeline.run_of(entries, ack.ack_id)
    was_lit = ack.ack_id in timeline.highlights(run)
    if on and not was_lit:
        if not timeline.may_highlight(entries, ack.ack_id):
            return jsonify({'message': 'Two in this group are highlighted already. Remove one highlight first.'}), 409
        ack.highlight(True)
        if ack.author_id and ack.author_id != sight.id:
            owner = resolve_user_names([sight.id]).get(sight.id) or 'A member'
            Notification.create(user_id=ack.author_id, actor_id=sight.id, actor_name=owner,
                                type_='acknowledgement_highlighted',
                                message=f'{owner} highlighted your acknowledgement', link=trail.link)
    elif not on and ack.highlighted_at:
        ack.highlight(False)
    return jsonify({'highlighted': on}), 200


def register(app_):
    ensure_tables()
    base = '/api/trails/<trail_id>'
    one = f'{base}/acknowledgements/<ack_id>'
    app_.add_url_rule(base, view_func=get_trail, methods=['GET', 'OPTIONS'])
    app_.add_url_rule(f'{base}/acknowledgements', view_func=post_acknowledgement, methods=['POST', 'OPTIONS'])
    app_.add_url_rule(one, view_func=delete_acknowledgement, methods=['DELETE', 'OPTIONS'])
    app_.add_url_rule(f'{one}/like', endpoint='like_trail_ack', view_func=post_like, methods=['POST', 'OPTIONS'])
    app_.add_url_rule(f'{one}/highlight', endpoint='highlight_trail_ack', view_func=post_highlight, methods=['POST', 'OPTIONS'])
