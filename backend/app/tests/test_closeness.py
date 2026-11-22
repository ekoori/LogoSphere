# The promises the closeness method makes (app/utils/closeness.py), one by one.
import math
import random

from app.utils import closeness as C


def card(owner, care, **fields):
    return dict(owner=owner, care_about=care, **fields)


def scores(cards):
    idf = C.rarity(cards.values())
    return C.words_scores({k: C.profile(c, idf) for k, c in cards.items()})


BASE = {
    'a': card('ann', 'Mending broken tools for neighbours', title='Repair first', looks_like=['Fix it before buying']),
    'b': card('ben', 'A shared shed of tools anyone can borrow', title='Borrow first', looks_like=['Lend the drill']),
    'c': card('cy', 'Quiet mornings watching birds', title='Stillness', looks_like=['Sitting by water']),
}


def test_identical_cards_are_as_close_as_can_be():
    same = {'a': BASE['a'], 'b': dict(BASE['a'], owner='ben'), 'c': BASE['c']}
    assert math.isclose(scores(same)[('a', 'b')], 1.0, abs_tol=1e-9)


def test_nothing_shared_is_no_connection():
    assert ('a', 'c') not in scores(BASE)


def test_symmetric_and_the_order_of_cards_does_not_matter():
    keys = list(BASE)
    random.Random(4).shuffle(keys)
    one, two = scores(BASE), scores({k: BASE[k] for k in keys})
    assert one.keys() == two.keys()
    assert all(math.isclose(one[p], two[p], abs_tol=1e-12) for p in one)
    assert all(a < b and 0 <= s <= 1 for (a, b), s in one.items())


def test_who_someone_is_does_not_matter():
    renamed = {k: dict(c, owner=f"someone else {c['owner']}") for k, c in BASE.items()}
    assert scores(renamed) == scores(BASE)


def test_writing_longer_buys_nothing():
    wordy = {k: dict(c) for k, c in BASE.items()}
    wordy['a']['care_about'] = ' '.join([BASE['a']['care_about']] * 6)
    before, after = scores(BASE)[('a', 'b')], scores(wordy)[('a', 'b')]
    assert math.isclose(before, after, abs_tol=1e-9)


def test_writing_more_cards_does_not_change_what_is_rare():
    more = dict(BASE, **{f'a{n}': dict(BASE['a']) for n in range(20)})
    assert C.rarity(more.values()) == C.rarity(BASE.values())
    assert math.isclose(scores(more)[('a', 'b')], scores(BASE)[('a', 'b')], abs_tol=1e-9)


def test_what_you_would_never_do_is_not_agreement():
    no = {k: dict(c, never_do='Gossip about neighbours', in_conflict='Gossip', drift_looks_like='Gossip')
          for k, c in BASE.items()}
    assert scores(no) == scores(BASE)


def test_families_are_one_word():
    two = {'a': card('ann', 'gift'), 'b': card('ben', 'generosity')}
    assert math.isclose(scores(two)[('a', 'b')], 1.0, abs_tol=1e-9)


def test_words_without_english_still_match():
    two = {'a': card('ann', 'susjedska pomoć i povjerenje'), 'b': card('ben', 'povjerenje')}
    assert scores(two)[('a', 'b')] > 0


def test_one_persons_act_is_never_evidence():
    assert C.lived_score(1) == 0
    assert C.lived_score(2) == 0.4
    assert C.combine(words=0.2, people=1) == C.combine(words=0.2)


def test_one_judge_does_not_count_and_more_count_for_more():
    base = C.combine(words=0.3)
    assert C.combine(words=0.3, judges=1, said_close=1) == base
    two, ten = C.combine(words=0.3, judges=2, said_close=2), C.combine(words=0.3, judges=10, said_close=10)
    assert base < two < ten <= 1
    assert C.combine(words=0.9, judges=10, said_close=0) < 0.3           # people can overrule the words


def test_everything_stays_between_0_and_1():
    top = C.combine(words=1, people=99, lineage=True, judges=9, said_close=9)
    assert top == 1 and C.combine() == 0


def test_the_method_publishes_what_it_uses():
    m = C.method()
    assert [(f['field'], f['weight']) for f in m['fields']] == list(C.FIELDS)
    assert math.isclose(sum(f['weight'] for f in m['fields']), 1.0)
    assert set(m['families']) == set(C.FAMILIES) and set(m['stop_words']) == set(C.STOP_WORDS)


def test_why_two_cards_are_close_can_be_read():
    idf = C.rarity(BASE.values())
    why = C.shared_words(C.profile(BASE['a'], idf), C.profile(BASE['b'], idf))
    assert 'tools' in [w['counts_as'] for w in why]
    assert math.isclose(sum(w['share'] for w in why), 1.0, abs_tol=0.01)
