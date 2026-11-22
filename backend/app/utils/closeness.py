# How close are two value cards? Method 1: in the open, and the same for everyone.
#
# A value is what someone attends to when they choose (the Meaning Alignment
# Institute's "attentional policies": Klingefjord, Lowe & Edelman 2024,
# arXiv:2404.10636). So two cards are close when they attend to the same things
# (words), when people put both on the same act (lived), or when one was made
# from the other (lineage); and people's own judgement outweighs the arithmetic
# as it gathers (judgement). Their moral graph links "wiser than" and has no
# distance, so this measure is ours.
#
# Never an input: likes, follows, roles, how active someone is, who they are.
# Writing more words or more cards buys nothing. No model, no outside service,
# nothing hidden: `method()` publishes every constant, word list and family.
#
# Pure functions: no database (that's app/utils/meaning_graph.py).
import math
import re
import unicodedata
from collections import Counter

VERSION = 1

# What is attended to. Left out on purpose: never_do, drift_looks_like and
# in_conflict, where shared words often mean disagreement ("never gossip").
FIELDS = (('care_about', 0.35), ('looks_like', 0.30), ('title', 0.20), ('because', 0.15))

LIVED_MIN_PEOPLE = 2    # fewer would show one person's act
LIVED_HALF = 3          # this many people make "lived" 0.5
LINEAGE = 0.5
JUDGES_MIN = 2
JUDGES_HALF = 4         # this many judges weigh as much as the arithmetic

STOP_WORDS = frozenset("""
a about above across act acting after again against all almost along already also although always am among an and
another any anyone anything are around as at away back be because been before behind being below between both but by
can cannot come comes could did do does doesn doing don done down during each either else enough even ever every
everyone everything few first for from further get gets getting go goes going had has have having he her here hers him
his how however i if in instead into is isn it its itself just keep keeping kept last least less let like made make makes
making many may me might more most much must my myself never new next no nobody none nor not nothing now of off often
on once one only onto or other others our ours ourselves out over own part people per person rather really same see
seeing seem seems she should since so some someone something sometimes still such take takes taking than that the
their theirs them themselves then there these they thing things this those though through to together too toward
towards treat treating treats two under until up upon us use used uses using very was way we well were what whatever
when where whether which while who whom whose why will with within without would yet you your yours yourself
""".split())

# Words counted as one, because people say the same thing differently. A
# judgement, so it is short, plain, and published with the method.
FAMILIES = {
    'giving': 'gift gifts give gives giving given gave donate donation generous generosity',
    'sharing': 'share shares shared sharing pool pooled pooling lend lends lending loan loans borrow borrows borrowed borrowing commons communal collective collectively',
    'neighbours': 'community communities neighbour neighbours neighbor neighbors neighbourhood neighborhood household households street village',
    'repair': 'repair repairs repairing repaired fix fixes fixing fixed mend mends mending mended broken maintain maintains maintaining maintenance restore restoring',
    'learning': 'learn learns learning learned learnt teach teaches teaching taught educate educating education skill skills mentor mentoring mentorship lesson lessons beginner beginners',
    'knowledge': 'knowledge understand understands understanding research researching researcher researchers science scientific wisdom',
    'openness': 'open openly opened transparent transparency visible publish publishes published publishing publication public publicly',
    'access': 'access accessible accessibility barrier barriers gatekeeping privilege',
    'honesty': 'honest honestly honesty truth truths truthful candour sincere sincerity',
    'care': 'care cares caring cared tend tending nurture nurturing compassion compassionate empathy kindness',
    'need': 'need needs needed needy vulnerable hardship stigma elderly frail',
    'growing': 'food grow grows growing grown grower growers harvest harvests soil garden gardens gardening cultivate cultivated cultivating compost composting crop crops farming',
    'seeds': 'seed seeds variety varieties',
    'nature': 'nature wild wildlife habitat habitats species biodiversity pollinator pollinators insect insects ecology ecological native natives plant plants planting',
    'energy': 'energy electricity grid battery batteries solar',
    'computing': 'compute computing computer computers gpu gpus cluster processing software',
    'curiosity': 'curious curiosity wonder wondering question questions explore exploring discovery',
    'reuse': 'waste wasted wasting surplus reuse reusing recycle recycling',
    'tools': 'tool tools toolshed equipment',
    'fairness': 'fair fairly fairness justice equity equitable equal equally equality impartial',
    'freedom': 'freedom liberation liberty liberating democratic autonomy',
    'listening': 'listen listens listening dialogue conversation conversations',
    'responsibility': 'responsibility responsible accountable accountability steward stewards stewarding stewardship',
    'belonging': 'belong belongs belonging welcome welcomes welcoming welcomed include including inclusion inclusive',
    'joy': 'joy joyful delight play playful fun',
    'health': 'health healthy wellbeing body',
}

_WORD = re.compile(r"[^\W\d_]+(?:'[^\W\d_]+)*")
_VOWELS = set('aeiouy')


def stem(word):
    """A word without its everyday English endings. Rough and predictable on purpose."""
    w = word
    if len(w) > 4 and w.endswith(('ies', 'ied')):
        w = w[:-3] + 'y'
    elif len(w) > 4 and w.endswith(('sses', 'xes', 'zes', 'ches', 'shes')):
        w = w[:-2]
    elif len(w) > 3 and w.endswith('s') and not w.endswith(('ss', 'us', 'is')):
        w = w[:-1]
    for ending in ('ing', 'ed'):
        base = w[:-len(ending)]
        if w.endswith(ending) and len(base) >= 3 and _VOWELS & set(base):
            if base[-1] == base[-2] and base[-1] not in 'lsz':
                base = base[:-1]
            w = base
            break
    w = w.replace('iz', 'is') if w.endswith(('ize', 'iz', 'ization')) else w
    if len(w) > 4 and w.endswith('e'):
        w = w[:-1]
    return w


_FAMILY_OF = {stem(word): name for name, words in FAMILIES.items() for word in words.split()}


def words_of(value):
    """(what it counts as, the word itself) for each meaningful word."""
    if isinstance(value, (list, tuple, set)):
        value = ' . '.join(str(v) for v in value)
    text = unicodedata.normalize('NFKC', str(value or '')).lower().replace('’', "'")
    out = []
    for word in _WORD.findall(text):
        word = word.split("'")[0]
        # Scripts without spaces or cases still match, as written.
        if not word or word in STOP_WORDS or (len(word) < 2 and word.isascii()):
            continue
        base = stem(word)
        family = _FAMILY_OF.get(base)
        out.append((f'~{family}' if family else base, word))
    return out


def rarity(cards):
    """How telling each word is: counted over owners, so writing more cards
    doesn't make your words common. `cards` have an 'owner'."""
    used = {}
    for card in cards:
        bag = used.setdefault(str(card['owner']), set())
        for field, _ in FIELDS:
            bag.update(token for token, _ in words_of(card.get(field)))
    df = Counter(token for bag in used.values() for token in bag)
    total = len(used)
    return {token: math.log((1 + total) / (1 + n)) + 1.0 for token, n in df.items()}


def _unit(vector):
    norm = math.sqrt(math.fsum(v * v for v in vector.values()))
    return {t: v / norm for t, v in vector.items()} if norm else {}


def profile(card, idf):
    """A card as (unit vector, {token: the words it used}). Each field is
    normalised by itself first, so a longer field says no more than a short one."""
    vector, said = {}, {}
    for field, weight in FIELDS:
        pairs = words_of(card.get(field))
        if not pairs:
            continue
        # A word counts once in a field: repeating it buys nothing.
        unit = _unit({t: idf.get(t, 1.0) for t in sorted({token for token, _ in pairs})})
        for token, value in unit.items():
            vector[token] = vector.get(token, 0.0) + weight * value
        for token, word in pairs:
            said.setdefault(token, set()).add(word)
    return _unit(vector), said


def words_scores(profiles):
    """{(a, b): cosine} for every pair sharing a word; a < b."""
    posting = {}
    for key in sorted(profiles):
        for token, value in profiles[key][0].items():
            posting.setdefault(token, []).append((key, value))
    scores = {}
    for token in sorted(posting):
        seen = posting[token]
        for i, (a, x) in enumerate(seen):
            for b, y in seen[i + 1:]:
                scores[(a, b)] = scores.get((a, b), 0.0) + x * y
    return {pair: min(1.0, s) for pair, s in scores.items()}


def shared_words(one, other, limit=5):
    """Why: the words behind a words score, biggest share first."""
    (x, said_x), (y, said_y) = one, other
    parts = sorted(((x[t] * y[t], t) for t in x if t in y), key=lambda p: (-p[0], p[1]))
    total = math.fsum(p for p, _ in parts)
    return [{
        'counts_as': token.lstrip('~'),
        'family': token.startswith('~'),
        'here': sorted(said_x[token]),
        'there': sorted(said_y[token]),
        'share': round(part / total, 3),
    } for part, token in parts[:limit]] if total else []


def lived_score(people):
    """`people`: how many different people put both cards on one act."""
    return people / (people + LIVED_HALF) if people >= LIVED_MIN_PEOPLE else 0.0


def combine(words=0.0, people=0, lineage=False, judges=0, said_close=0):
    """The closeness of a pair, 0 to 1."""
    lived = lived_score(people)
    made_from = LINEAGE if lineage else 0.0
    score = 1 - (1 - min(1.0, max(0.0, words))) * (1 - lived) * (1 - made_from)
    if judges >= JUDGES_MIN:
        score = (JUDGES_HALF * score + said_close) / (JUDGES_HALF + judges)
    return score


def method():
    """Everything needed to work a score out by hand."""
    return {
        'version': VERSION,
        'idea': ('Two value cards are close when they attend to the same things, when people put both on the '
                 'same act, or when one was made from the other. People judge too, and as more do their '
                 'judgement outweighs the arithmetic.'),
        'formula': [
            'words = cosine similarity of the two cards\' words; a word counts once in a field, by its rarity; each field is normalised first, then counts by its weight',
            'rarity of a word = ln((1 + owners) / (1 + owners who use it)) + 1',
            f'lived = people / (people + {LIVED_HALF}), from {LIVED_MIN_PEOPLE} people who each put both cards on one receipt, note or acknowledgement',
            f'lineage = {LINEAGE} when one card was made from the other',
            'arithmetic = 1 - (1 - words) x (1 - lived) x (1 - lineage)',
            f'closeness = ({JUDGES_HALF} x arithmetic + people saying close) / ({JUDGES_HALF} + judges), from {JUDGES_MIN} judges',
        ],
        'fields': [{'field': f, 'weight': w} for f, w in FIELDS],
        'not_counted': ['never_do', 'drift_looks_like', 'in_conflict'],
        'never_inputs': ['likes', 'follows', 'roles', 'how active someone is', 'who someone is', 'money'],
        'rules': [
            'The same two cards have the same closeness whoever looks.',
            'Writing longer, or writing more cards, buys nothing.',
            'One person, one judgement for each pair; nobody judges a pair with their own card in it.',
            'AI personas never judge, and what they do is never evidence.',
            'You see only cards you may see.',
        ],
        'limits': [
            'Words can be shared without the meaning being shared, and the reverse: that is what judgement is for.',
            'Word endings and families are English; other languages match word for word.',
        ],
        'stop_words': sorted(STOP_WORDS),
        'families': {name: sorted(words.split()) for name, words in sorted(FAMILIES.items())},
        'sources': [
            {'title': 'What are human values, and how do we align AI to them? (Klingefjord, Lowe, Edelman 2024)',
             'url': 'https://arxiv.org/abs/2404.10636'},
        ],
    }
