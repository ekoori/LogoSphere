# Value-graph vectors for the "vicinity" search.
#
# Every user, sphere, alliance and project owns a set of value cards (its
# value graph). This module turns each graph into a sparse vector and ranks
# owners by cosine similarity - to a free-text query or to another owner's
# graph. Openings get a vector from their own text so they can be ranked in
# the same space.
#
# The vectoriser is deliberately self-contained (TF-IDF over word tokens plus
# a few structural tokens) so it runs on the production host with no model
# download and no external API. `Vectorizer` is the seam: swap `embed()` for a
# dense-embedding provider later without touching the ranking code.
import math
import re
import time
import uuid
from collections import Counter, defaultdict

from app.db import session as cassandra_session

_TOKEN_RE = re.compile(r"[a-z0-9][a-z0-9'-]{1,}")
# Words that carry no meaning of their own. Short list on purpose: value cards
# are written in plain language and most words there are signal.
_STOP = set("""a an and are as at be because but by can do for from has have i if in into is it its
me my not of on or our so that the their them then there they this to us we what when which
who will with you your""".split())
# Card fields, with how much a token from each contributes.
_CARD_FIELDS = (('title', 3.0), ('care_about', 2.0), ('because', 1.0), ('looks_like', 1.0),
                ('drift_looks_like', 0.5), ('in_conflict', 0.5), ('never_do', 0.5))
_INDEX_TTL = 30.0


def tokenize(text):
    """Lower-cased word tokens (plus adjacent-word bigrams so 'mutual aid'
    stays distinct from 'mutual' and 'aid'), stop words removed."""
    if not text:
        return []
    if isinstance(text, (list, tuple, set)):
        text = ' '.join(str(t) for t in text)
    words = [w for w in _TOKEN_RE.findall(str(text).lower()) if w not in _STOP]
    bigrams = [f'{a}_{b}' for a, b in zip(words, words[1:])]
    return words + bigrams


def _norm_title(title):
    return re.sub(r'[^a-z0-9]+', ' ', (title or '').lower()).strip()


class Vectorizer:
    """Sparse TF-IDF vectors. `fit(docs)` learns idf from a corpus of token
    Counters; `embed(counter)` returns a unit-length {token: weight} dict."""

    def __init__(self):
        self.idf = {}
        self.n_docs = 0

    def fit(self, docs):
        df = Counter()
        for d in docs:
            df.update(set(d))
        self.n_docs = max(1, len(docs))
        # Smoothed idf; a token in every document still counts a little.
        self.idf = {t: math.log((1 + self.n_docs) / (1 + n)) + 1.0 for t, n in df.items()}
        return self

    def embed(self, counter):
        if not counter:
            return {}
        vec = {}
        for t, tf in counter.items():
            w = (1 + math.log(tf)) * self.idf.get(t, math.log(1 + self.n_docs) + 1.0)
            if w > 0:
                vec[t] = w
        norm = math.sqrt(sum(w * w for w in vec.values())) or 1.0
        return {t: w / norm for t, w in vec.items()}


def cosine(a, b):
    if not a or not b:
        return 0.0
    if len(a) > len(b):
        a, b = b, a
    return sum(w * b[t] for t, w in a.items() if t in b)


def card_tokens(card):
    """Weighted token Counter for one value card. Besides the words, the
    card's normalised title is one strong token of its own, so two graphs that
    adopted (cloned) the same card are close even if the rest differs."""
    c = Counter()
    for field, weight in _CARD_FIELDS:
        for t in tokenize(card.get(field)):
            c[t] += weight
    title = _norm_title(card.get('title'))
    if title:
        c[f'card:{title}'] += 4.0
    if card.get('frankl_mode'):
        c[f'mode:{card["frankl_mode"]}'] += 0.5
    return c


def text_tokens(*texts):
    c = Counter()
    for text in texts:
        for t in tokenize(text):
            c[t] += 1.0
    return c


class ValueGraphIndex:
    """All value graphs (and openings) vectorised, rebuilt lazily every
    _INDEX_TTL seconds. Small data, so a full scan is fine; the cache keeps a
    burst of searches from re-scanning."""

    def __init__(self):
        self.built_at = 0.0
        self.owners = {}      # owner_id (str) -> {'kind','name','link','sphere_id','sphere_name','cards':[...],'members':set}
        self.vectors = {}     # owner_id (str) -> unit vector
        self.openings = {}    # service_id (str) -> {'name','link',...}
        self.opening_vectors = {}
        self.vectorizer = Vectorizer()

    def ensure(self):
        if time.time() - self.built_at < _INDEX_TTL:
            return self
        self.build()
        return self

    # ── building ────────────────────────────────────────────────────────────
    def build(self):
        from app.models.spheres import Sphere
        from app.models.alliance import Alliance
        from app.models.project import Project
        from app.models.openings import Service

        owners = {}
        for r in cassandra_session.execute("SELECT user_id, name, surname, location FROM users"):
            name = f"{r.name or ''} {r.surname or ''}".strip() or 'Member'
            owners[str(r.user_id)] = {'kind': 'user', 'name': name, 'link': f'/user?id={r.user_id}',
                                      'sphere_id': None, 'sphere_name': None, 'members': set(),
                                      'summary': r.location or '', 'cards': []}
        for s in Sphere.get_all():
            owners[str(s.sphere_id)] = {'kind': 'sphere', 'name': s.name, 'link': f'/sphere?id={s.sphere_id}',
                                        'sphere_id': str(s.sphere_id), 'sphere_name': s.name,
                                        'members': {str(m) for m in (s.participants or [])},
                                        'summary': s.description or '', 'cards': [],
                                        'is_public': bool(getattr(s, 'is_public', False))}
        for a in Alliance.get_all():
            owners[str(a.alliance_id)] = {'kind': 'alliance', 'name': a.name, 'link': f'/alliance?id={a.alliance_id}',
                                          'sphere_id': str(a.sphere_id) if a.sphere_id else None,
                                          'sphere_name': a.sphere_name,
                                          'members': {str(m) for m in (a.members or [])},
                                          'summary': a.description or '', 'cards': []}
        for p in Project.get_all():
            owners[str(p.project_id)] = {'kind': 'project', 'name': p.name, 'link': f'/project?id={p.project_id}',
                                         'sphere_id': str(p.sphere_id) if p.sphere_id else None,
                                         'sphere_name': p.sphere_name,
                                         'members': {str(m) for m in (p.participants or [])},
                                         'summary': p.description or '', 'cards': []}

        # Every current value card, grouped by owner.
        for r in cassandra_session.execute(
                "SELECT user_id, card_id, title, care_about, because, looks_like, drift_looks_like, "
                "in_conflict, never_do, frankl_mode, color_key, is_current FROM value_cards"):
            if getattr(r, 'is_current', True) is False:
                continue
            o = owners.get(str(r.user_id))
            if o is None:
                continue
            o['cards'].append({
                'card_id': str(r.card_id), 'title': r.title or '', 'care_about': r.care_about or '',
                'because': r.because or '', 'looks_like': list(r.looks_like or []),
                'drift_looks_like': r.drift_looks_like or '', 'in_conflict': r.in_conflict or '',
                'never_do': r.never_do or '', 'frankl_mode': r.frankl_mode or '',
                'color_key': r.color_key or 'honey',
            })

        openings = {}
        for s in Service.get_all():
            if not s.is_current or s.status in ('Cancelled', 'Completed'):
                continue
            if s.cadence != 'perpetual' and s.status == 'In Progress':
                continue
            openings[str(s.service_id)] = {
                'kind': 'opening', 'name': s.title, 'link': f'/opening?id={s.service_id}',
                'sphere_id': str(s.sphere_id) if s.sphere_id else None, 'sphere_name': s.sphere_name,
                'provider_id': str(s.provider_id) if s.provider_id else None, 'provider': s.provider_name,
                'type': s.type, 'summary': s.description or '', 'values': list(s.values or []),
            }

        # Corpus = one document per owner-with-cards + one per opening.
        owner_docs = {oid: sum((card_tokens(c) for c in o['cards']), Counter()) for oid, o in owners.items() if o['cards']}
        opening_docs = {}
        for sid, op in openings.items():
            doc = text_tokens(op['name'], op['name'], op['summary'], op['values'])
            # An opening also inherits a little of its provider's value graph.
            prov = owner_docs.get(op['provider_id'])
            if prov:
                for t, w in prov.items():
                    doc[t] += 0.25 * w
            opening_docs[sid] = doc
        self.vectorizer = Vectorizer().fit(list(owner_docs.values()) + list(opening_docs.values()))
        self.owners = owners
        self.vectors = {oid: self.vectorizer.embed(d) for oid, d in owner_docs.items()}
        self.openings = openings
        self.opening_vectors = {sid: self.vectorizer.embed(d) for sid, d in opening_docs.items()}
        self.built_at = time.time()

    # ── querying ────────────────────────────────────────────────────────────
    def query_vector(self, text=None, around=None):
        """Vector for a free-text query, or for an existing owner's graph."""
        if around and str(around) in self.vectors:
            return self.vectors[str(around)]
        if text:
            return self.vectorizer.embed(text_tokens(text))
        return {}

    def explain(self, qvec, target_vec, limit=4):
        """The tokens that contributed most to a match, readable."""
        contrib = sorted(((w * target_vec[t], t) for t, w in qvec.items() if t in target_vec), reverse=True)
        out = []
        for _, t in contrib:
            if t.startswith('card:') or t.startswith('mode:') or '_' in t:
                continue
            out.append(t)
            if len(out) >= limit:
                break
        return out

    def shared_cards(self, around, owner_id):
        """Cards two owners share by (normalised) title - the clearest sign of
        a common value; shown as chips on the result."""
        a = self.owners.get(str(around))
        b = self.owners.get(str(owner_id))
        if not a or not b:
            return []
        titles = {_norm_title(c['title']) for c in a['cards'] if c.get('title')}
        return [c for c in b['cards'] if _norm_title(c['title']) in titles]


_index = ValueGraphIndex()


def get_index():
    return _index.ensure()


def invalidate_index():
    _index.built_at = 0.0


def is_uuid(value):
    try:
        uuid.UUID(str(value))
        return True
    except (ValueError, TypeError, AttributeError):
        return False
