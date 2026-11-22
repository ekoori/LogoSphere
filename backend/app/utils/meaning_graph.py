# The Meaning Graph: every current value card a node, with the closeness of
# each pair (app/utils/closeness.py) as the edges.
#
# One graph is worked out for everyone, so a pair's closeness is the same
# whoever looks; each viewer is then shown only the cards they may read.
# A node is a card's whole history of edits (its first version's id), so
# judgements and evidence survive rewording.
import time
from collections import defaultdict
from itertools import combinations

from app.db import session
from app.models.acknowledgement import Acknowledgement
from app.models.meaning_trail import MeaningTrail
from app.models.value_card import ValueCard
from app.utils import closeness
from app.utils.access import as_uuid
from app.utils.demo import agent_ids, demo_sphere_ids
from app.utils.permissions import can_manage_entity

SHOWN_FROM = 0.12           # the threshold a graph opens at
KEPT_FROM = 0.06            # weaker pairs aren't sent at all
KEPT_EACH = 8               # each card's strongest pairs
FRESH_SECONDS = 5

JUDGEMENTS_DDL = ('CREATE TABLE IF NOT EXISTS meaning_judgements ('
                  'pair text, user_id uuid, is_close boolean, judged_at timestamp, '
                  'PRIMARY KEY ((pair), user_id))')
LINEAGE_DDL = 'ALTER TABLE value_cards ADD IF NOT EXISTS cloned_from uuid'


def ensure_tables():
    session.execute(JUDGEMENTS_DDL)
    session.execute(LINEAGE_DDL)


def pair_key(a, b):
    return '|'.join(sorted((str(a), str(b))))


def judge(a, b, user_id, close):
    """One person, one judgement for each pair; None takes it back."""
    pair, who = pair_key(a, b), as_uuid(user_id)
    if close is None:
        session.execute('DELETE FROM meaning_judgements WHERE pair = %s AND user_id = %s', [pair, who])
    else:
        session.execute('INSERT INTO meaning_judgements (pair, user_id, is_close, judged_at) '
                        'VALUES (%s, %s, %s, toTimestamp(now()))', [pair, who, bool(close)])


def judgements_by(user_id):
    who = as_uuid(user_id)
    return [{'cards': r.pair.split('|'), 'close': r.is_close, 'at': r.judged_at}
            for r in session.execute('SELECT pair, user_id, is_close, judged_at FROM meaning_judgements')
            if r.user_id == who]


def forget_judge(user_id):
    who = as_uuid(user_id)
    for r in list(session.execute('SELECT pair, user_id FROM meaning_judgements')):
        if r.user_id == who:
            session.execute('DELETE FROM meaning_judgements WHERE pair = %s AND user_id = %s', [r.pair, who])


class Owners:
    """Who owns cards: people, spheres, alliances, projects."""

    def __init__(self):
        agents, demos = agent_ids(), demo_sphere_ids()
        self.all = {}
        self.sphere_members = {}
        for r in session.execute('SELECT user_id, name, surname FROM users'):
            name = f"{r.name or ''} {r.surname or ''}".strip() or 'A member'
            agent = r.user_id in agents
            self.all[r.user_id] = dict(kind='user', name=name, is_agent=agent, is_demo=agent, sphere=None, members=set())
        for r in session.execute('SELECT sphere_id, name, participants FROM spheres'):
            members = set(r.participants or [])
            self.sphere_members[r.sphere_id] = members
            self.all[r.sphere_id] = dict(kind='sphere', name=r.name or 'A sphere', is_agent=False,
                                         is_demo=r.sphere_id in demos, sphere=r.sphere_id, members=members)
        for kind, table, key, col in (('alliance', 'alliances', 'alliance_id', 'members'),
                                      ('project', 'projects', 'project_id', 'participants')):
            for r in session.execute(f'SELECT {key}, name, sphere_id, {col} FROM {table}'):
                self.all[getattr(r, key)] = dict(kind=kind, name=r.name or f'A {kind}', is_agent=False,
                                                 is_demo=r.sphere_id in demos, sphere=r.sphere_id,
                                                 members=set(getattr(r, col) or []))

    def is_person(self, user_id):
        owner = self.all.get(user_id)
        return bool(owner) and owner['kind'] == 'user' and not owner['is_agent']

    def visible(self, owner_id, sight):
        """The same rule as reading that owner's cards (Sight.value_cards)."""
        owner = self.all[owner_id]
        if owner['kind'] in ('user', 'sphere'):
            return True
        return sight.sphere(owner['sphere']) or sight.id in owner['members']

    def near(self, owner_id, sight):
        """In one of the viewer's spheres."""
        owner = self.all[owner_id]
        if owner['kind'] == 'user':
            return any(owner_id in self.sphere_members.get(s, ()) for s in sight.spheres)
        return owner['sphere'] in sight.spheres


class Graph:
    def __init__(self):
        self.built_at = time.monotonic()
        self.owners = Owners()
        rows = list(session.execute('SELECT * FROM value_cards'))
        self._before = {r.card_id: r.replaces_card_id for r in rows if r.replaces_card_id}
        self._roots = {}

        self.cards = {}
        for r in rows:
            if r.is_current is False or r.user_id not in self.owners.all:
                continue
            root = self.root(r.card_id)
            kept = self.cards.get(root)
            if kept is None or (r.created_at and (not kept.created_at or r.created_at > kept.created_at)):
                self.cards[root] = ValueCard._row_to_card(r)

        texts = {root: dict({f: getattr(c, f) for f, _ in closeness.FIELDS}, owner=c.user_id)
                 for root, c in self.cards.items()}
        idf = closeness.rarity(texts.values())
        self.profiles = {root: closeness.profile(text, idf) for root, text in texts.items()}
        self.words = closeness.words_scores(self.profiles)
        self.lineage = self._lineage(rows)
        self.people = self._lived()
        self.judged = self._judged()
        self.scores = {pair: self.score(pair) for pair in
                       set(self.words) | self.lineage | set(self.people) | set(self.judged)}
        self.kept = self._strongest()

    def root(self, card_id):
        """The first version of a card."""
        start = key = str(card_id)
        if start in self._roots:
            return self._roots[start]
        seen, current = {start}, as_uuid(card_id)
        while current in self._before and str(self._before[current]) not in seen:
            current = self._before[current]
            key = str(current)
            seen.add(key)
        self._roots[start] = key
        return key

    def _pair(self, one, other):
        a, b = sorted((one, other))
        return (a, b) if a != b and a in self.cards and b in self.cards else None

    def _lineage(self, rows):
        out = set()
        for r in rows:
            source = getattr(r, 'cloned_from', None)
            pair = source and self._pair(self.root(r.card_id), self.root(source))
            if pair:
                out.add(pair)
        return out

    def _lived(self):
        """For each pair: the different people who put both cards on one act.
        Only people: a persona's act is never evidence."""
        out = defaultdict(set)

        def saw(author, cards):
            if not self.owners.is_person(as_uuid(author)):
                return
            named = {self.root(c['card_id']) for c in cards or []
                     if isinstance(c, dict) and as_uuid(c.get('card_id'))}
            for one, other in combinations(sorted(named), 2):
                pair = self._pair(one, other)
                if pair:
                    out[pair].add(str(author))

        for row in MeaningTrail.every_row():
            if not (row.gratitude_comment_cards or row.user_comment_cards):
                continue
            d = row.to_dict()
            saw(d['recipient_acting_user_id'] or d['other_user_id'], d['gratitude_comment_cards'])
            saw(d['initiator_acting_user_id'] or d['user_id'], d['user_comment_cards'])
        for ack in Acknowledgement.everything():
            if ack.cards:
                saw(ack.author_id, ack.cards)
        return out

    def _judged(self):
        out = defaultdict(dict)
        for r in session.execute('SELECT pair, user_id, is_close FROM meaning_judgements'):
            one, _, other = r.pair.partition('|')
            pair = self._pair(one, other)
            if not pair or r.is_close is None or not self.owners.is_person(r.user_id):
                continue
            if r.user_id in (self.cards[pair[0]].user_id, self.cards[pair[1]].user_id):
                continue
            out[pair][r.user_id] = bool(r.is_close)
        return out

    def score(self, pair):
        votes = self.judged.get(pair, {})
        return closeness.combine(words=self.words.get(pair, 0.0), people=len(self.people.get(pair, ())),
                                 lineage=pair in self.lineage, judges=len(votes), said_close=sum(votes.values()))

    def _strongest(self):
        by_card = defaultdict(list)
        for pair, score in self.scores.items():
            if score >= KEPT_FROM:
                for end in pair:
                    by_card[end].append((score, pair))
        kept = set(self.judged)
        for ranked in by_card.values():
            ranked.sort(reverse=True)
            kept.update(pair for _, pair in ranked[:KEPT_EACH])
        return kept

    # -- as one person sees it --------------------------------------------------
    def edge(self, pair, viewer_id):
        a, b = pair
        votes, people = self.judged.get(pair, {}), len(self.people.get(pair, ()))
        counted = len(votes) >= closeness.JUDGES_MIN
        return {
            'a': a, 'b': b,
            'closeness': round(self.scores.get(pair, self.score(pair)), 4),
            'words': round(self.words.get(pair, 0.0), 4),
            'shared': closeness.shared_words(self.profiles[a], self.profiles[b]),
            'people': people if people >= closeness.LIVED_MIN_PEOPLE else 0,
            'lineage': pair in self.lineage,
            'judges': len(votes) if counted else 0,
            'said_close': sum(votes.values()) if counted else 0,
            'my_judgement': votes.get(viewer_id),
        }

    def for_viewer(self, sight):
        owners, managed = self.owners, {}
        judge_at_all = owners.is_person(sight.id)

        def theirs(owner_id):
            if owner_id == sight.id:
                return True
            if owners.all[owner_id]['kind'] == 'user':
                return False
            if owner_id not in managed:
                managed[owner_id] = can_manage_entity(owner_id, sight.id, include_platform_admin=False)
            return managed[owner_id]

        seen = {root: c for root, c in self.cards.items() if owners.visible(c.user_id, sight)}
        nodes = []
        for root, card in sorted(seen.items()):
            owner = owners.all[card.user_id]
            nodes.append({
                'id': root,
                'card': card.to_dict(),
                'owner': {'id': str(card.user_id), 'name': owner['name'], 'kind': owner['kind'],
                          'is_agent': owner['is_agent']},
                'is_demo': owner['is_demo'],
                'mine': card.user_id == sight.id,
                'near': card.user_id == sight.id or owners.near(card.user_id, sight),
                'can_judge': judge_at_all and not theirs(card.user_id),
            })
        edges = [self.edge(p, sight.id) for p in sorted(self.kept) if p[0] in seen and p[1] in seen]
        return {'method_version': closeness.VERSION, 'shown_from': SHOWN_FROM, 'nodes': nodes, 'edges': edges}


_latest = None


def get_graph(fresh=False):
    global _latest
    graph = _latest
    if fresh or graph is None or time.monotonic() - graph.built_at > FRESH_SECONDS:
        graph = _latest = Graph()
    return graph
