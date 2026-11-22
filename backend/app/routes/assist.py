"""AI help, only when asked (app/utils/assist.py):

  GET  /api/ai              what is switched on, and what is left of your day
  POST /api/ai/value_card   your notes -> a draft card and a question; not saved
  POST /api/ai/picture      a picture for an opening, group or event; not saved
"""
import base64

from flask import current_app as app, jsonify, request

from app.middleware.session_middleware import validate_session
from app.utils import ai_pictures, assist

NOTES_MAX = 1500
DRAFT_FIELDS = ('title', 'care_about', 'because', 'looks_like', 'drift_looks_like', 'in_conflict', 'never_do')


def _options():
    return app.make_default_options_response(), 200


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _draft(raw):
    """Only the card's own fields go out, and only so much of each."""
    if not isinstance(raw, dict):
        return {}
    out = {}
    for field in DRAFT_FIELDS:
        value = raw.get(field)
        if field == 'looks_like' and isinstance(value, list):
            value = [assist.short(v, 160) for v in value[:6] if assist.short(v, 160)]
        elif isinstance(value, str):
            value = assist.short(value, 400)
        else:
            continue
        if value:
            out[field] = value
    return out


@validate_session
def ai_status(user_id=None):
    return jsonify(assist.status(user_id)), 200


@validate_session
def value_card_help(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    data = _body()
    notes = assist.short(data.get('notes'), NOTES_MAX)
    draft = _draft(data.get('draft'))
    if not notes and not draft:
        return jsonify({'message': 'Write a few words about what matters to you first.'}), 400
    try:
        out = assist.draft_card(user_id, notes, draft, group=data.get('group') is True, brief=data.get('brief') is True)
    except assist.AssistError as e:
        return jsonify({'message': e.message}), e.status
    return jsonify({**out, 'left': assist.left(user_id, assist.CARDS)}), 200


@validate_session
def picture_help(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    data = _body()
    purpose = data.get('purpose')
    if purpose not in tuple(assist.PURPOSES):
        return jsonify({'message': 'AI draws for offers, needs, groups and events, never for receipts.'}), 400
    title = assist.short(data.get('title'), 120)
    if not title:
        return jsonify({'message': 'Give it a title first, so the picture has something to show.'}), 400
    try:
        picture = assist.draw(user_id, purpose, title,
                              description=assist.short(data.get('description'), 600),
                              hint=assist.short(data.get('hint'), 300))
    except assist.AssistError as e:
        return jsonify({'message': e.message}), e.status
    return jsonify({
        'image': base64.b64encode(picture).decode('ascii'),
        'content_type': 'image/jpeg',
        'left': assist.left(user_id, assist.PICTURES),
    }), 200


def register(app_):
    ai_pictures.ensure_tables()
    assist.ensure_tables()
    app_.add_url_rule('/api/ai', view_func=ai_status, methods=['GET'])
    app_.add_url_rule('/api/ai/value_card', view_func=value_card_help, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/ai/picture', view_func=picture_help, methods=['POST', 'OPTIONS'])
