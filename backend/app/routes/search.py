# File: ./backend/app/routes/search.py
# Description: Search across the platform.
#
#   GET /api/search?q=<text>[&kinds=user,sphere,alliance,project,opening,card][&limit=8]
#       Plain text match on names, titles, descriptions and value cards.
#   GET /api/search/vicinity?[q=<text>|around=<owner id>][&kinds=...][&limit=8]
#       Value-graph vicinity: rank people, spheres, alliances, projects and
#       openings by cosine similarity between value-graph vectors (see
#       utils/search_vectors.py). With neither q nor around, it's "around me".
#
# Both respect what the viewer may see: sphere-scoped openings, alliances and
# projects only inside the viewer's spheres (platform admins see everything).
import logging
import uuid

from flask import request, jsonify, current_app as app

from app.middleware.session_middleware import validate_session
from app.models.spheres import Sphere
from app.utils.permissions import is_platform_admin
from app.utils.search_vectors import get_index, tokenize, is_uuid

logger = logging.getLogger(__name__)

ALL_KINDS = ('user', 'sphere', 'alliance', 'project', 'opening', 'card')
KIND_LABEL = {'user': 'People', 'sphere': 'Spheres', 'alliance': 'Alliances',
              'project': 'Projects', 'opening': 'Openings', 'card': 'Value cards'}


def _kinds_param():
    raw = (request.args.get('kinds') or '').strip()
    if not raw:
        return set(ALL_KINDS)
    return {k for k in raw.split(',') if k in ALL_KINDS}


def _limit_param(default=8, cap=50):
    try:
        return max(1, min(cap, int(request.args.get('limit', default))))
    except (TypeError, ValueError):
        return default


class _Viewer:
    """What the viewer may see, computed once per request."""

    def __init__(self, user_id):
        self.id = str(user_id)
        self.admin = is_platform_admin(user_id)
        self.spheres = {str(s) for s in Sphere.member_sphere_ids(uuid.UUID(self.id))}

    def can_see(self, item):
        if self.admin:
            return True
        kind = item['kind']
        if kind in ('user', 'sphere'):
            return True
        if kind == 'opening':
            if item.get('provider_id') == self.id:
                return True
            return not item.get('sphere_id') or item['sphere_id'] in self.spheres
        # alliances / projects: members, or inside one of my spheres
        if self.id in item.get('members', set()):
            return True
        return not item.get('sphere_id') or item['sphere_id'] in self.spheres


def _base_result(item_id, item, score):
    return {
        'id': item_id, 'kind': item['kind'], 'name': item['name'], 'link': item['link'],
        'summary': (item.get('summary') or '')[:220],
        'sphere_id': item.get('sphere_id'), 'sphere_name': item.get('sphere_name'),
        'score': round(float(score), 4),
    }


# ── Plain text search ────────────────────────────────────────────────────────
def _text_score(query_words, *fields):
    """0 when nothing matches. Whole-phrase and name-field hits score highest;
    then each query word found in any field."""
    q = ' '.join(query_words)
    score = 0.0
    for weight, field in fields:
        f = (field or '').lower()
        if not f:
            continue
        if q and q in f:
            score += 4.0 * weight
        for w in query_words:
            if w in f:
                score += 1.0 * weight
    return score


@validate_session
def search(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        q = (request.args.get('q') or '').strip()
        if len(q) < 2:
            return jsonify({'query': q, 'groups': [], 'total': 0}), 200
        words = [w for w in q.lower().split() if w] or [q.lower()]
        kinds = _kinds_param()
        limit = _limit_param()
        viewer = _Viewer(user_id)
        index = get_index()

        buckets = {k: [] for k in ALL_KINDS}
        for oid, o in index.owners.items():
            if o['kind'] not in kinds and 'card' not in kinds:
                continue
            if not viewer.can_see(o):
                continue
            if o['kind'] in kinds:
                sc = _text_score(words, (2.0, o['name']), (1.0, o.get('summary')), (0.7, o.get('sphere_name')))
                if sc > 0:
                    r = _base_result(oid, o, sc)
                    r['member_count'] = len(o.get('members') or ())
                    r['card_count'] = len(o['cards'])
                    buckets[o['kind']].append(r)
            if 'card' in kinds:
                for c in o['cards']:
                    sc = _text_score(words, (2.0, c['title']), (1.0, c['care_about']), (0.7, c['because']),
                                     (0.5, ' '.join(c.get('looks_like') or [])))
                    if sc > 0:
                        buckets['card'].append({
                            'id': c['card_id'], 'kind': 'card', 'name': c['title'] or 'Untitled card',
                            'link': o['link'], 'summary': (c['care_about'] or '')[:220],
                            'owner_id': oid, 'owner_name': o['name'], 'owner_kind': o['kind'],
                            'color_key': c.get('color_key'), 'card': c, 'score': round(sc, 4),
                        })
        if 'opening' in kinds:
            for sid, op in index.openings.items():
                if not viewer.can_see(op):
                    continue
                sc = _text_score(words, (2.0, op['name']), (1.0, op.get('summary')), (0.7, op.get('provider')),
                                 (0.7, ' '.join(op.get('values') or [])), (0.5, op.get('sphere_name')))
                if sc > 0:
                    r = _base_result(sid, op, sc)
                    r['type'] = op['type']
                    r['provider'] = op['provider']
                    buckets['opening'].append(r)

        groups, total = [], 0
        for kind in ALL_KINDS:
            items = sorted(buckets[kind], key=lambda r: (-r['score'], r['name'].lower()))
            if not items:
                continue
            total += len(items)
            groups.append({'kind': kind, 'label': KIND_LABEL[kind], 'count': len(items), 'items': items[:limit]})
        return jsonify({'query': q, 'groups': groups, 'total': total}), 200
    except Exception as e:
        logger.error(f"Error in search: {e}")
        return jsonify({'message': 'Internal server error'}), 500


# ── Value-graph vicinity search ──────────────────────────────────────────────
@validate_session
def search_vicinity(user_id=None):
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        q = (request.args.get('q') or '').strip()
        around = (request.args.get('around') or '').strip()
        if not q and not around:
            around = str(user_id)
        if around and not is_uuid(around):
            return jsonify({'message': 'around must be a user/sphere/alliance/project id'}), 400
        kinds = _kinds_param() - {'card'}
        limit = _limit_param()
        viewer = _Viewer(user_id)
        index = get_index()

        anchor = index.owners.get(around) if around else None
        if around and not anchor:
            return jsonify({'message': 'Unknown id to search around'}), 404
        qvec = index.query_vector(text=q if q else None, around=around if not q else None)
        if not qvec:
            return jsonify({
                'query': q, 'around': _anchor_dict(around, anchor), 'groups': [], 'total': 0,
                'note': 'No value cards to search from yet - add a few to your value graph first.'
                        if around else 'Nothing to search for.',
            }), 200

        buckets = {k: [] for k in ALL_KINDS}
        for oid, vec in index.vectors.items():
            o = index.owners[oid]
            if o['kind'] not in kinds or oid == around or not viewer.can_see(o):
                continue
            sim = _cos(qvec, vec)
            if sim <= 0.02:
                continue
            r = _base_result(oid, o, sim)
            r['similarity'] = round(sim, 3)
            r['member_count'] = len(o.get('members') or ())
            r['card_count'] = len(o['cards'])
            r['why'] = index.explain(qvec, vec)
            shared = index.shared_cards(around, oid) if around and not q else []
            r['shared_cards'] = [{'card_id': c['card_id'], 'title': c['title'], 'color_key': c['color_key']}
                                 for c in shared[:6]]
            r['cards'] = [{'card_id': c['card_id'], 'title': c['title'], 'color_key': c['color_key']}
                          for c in o['cards'][:6]]
            buckets[o['kind']].append(r)
        if 'opening' in kinds:
            for sid, vec in index.opening_vectors.items():
                op = index.openings[sid]
                if not viewer.can_see(op) or op.get('provider_id') == around:
                    continue
                sim = _cos(qvec, vec)
                if sim <= 0.02:
                    continue
                r = _base_result(sid, op, sim)
                r['similarity'] = round(sim, 3)
                r['type'] = op['type']
                r['provider'] = op['provider']
                r['why'] = index.explain(qvec, vec)
                buckets['opening'].append(r)

        groups, total = [], 0
        for kind in ALL_KINDS:
            items = sorted(buckets[kind], key=lambda r: -r['score'])
            if not items:
                continue
            total += len(items)
            groups.append({'kind': kind, 'label': KIND_LABEL[kind], 'count': len(items), 'items': items[:limit]})
        return jsonify({'query': q, 'around': _anchor_dict(around, anchor), 'groups': groups, 'total': total,
                        'method': 'tf-idf cosine over value-card text'}), 200
    except Exception as e:
        logger.error(f"Error in search_vicinity: {e}")
        return jsonify({'message': 'Internal server error'}), 500


def _anchor_dict(around, anchor):
    if not around or not anchor:
        return None
    return {'id': around, 'kind': anchor['kind'], 'name': anchor['name'], 'link': anchor['link'],
            'card_count': len(anchor['cards'])}


def _cos(a, b):
    from app.utils.search_vectors import cosine
    return cosine(a, b)


# Silence "unused import" for tokenize - kept exported for tests/tools.
_ = tokenize
