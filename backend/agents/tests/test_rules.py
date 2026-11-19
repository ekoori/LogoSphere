"""The personas' rules, without a database or an API."""
import random
from datetime import datetime, timedelta

from agents import config
from agents.rules import Event, State, plan

NOW = datetime(2026, 11, 20, 10, 0)
SPHERE = 'sphere-1'
REAL = 'real-member'
PERSONAS = ['p-marie', 'p-joe', 'p-emma']


def run(events, state=None, seed=1, now=NOW):
    state = state or State()
    return plan(events, state, now=now, rng=random.Random(seed), sphere_personas={SPHERE: PERSONAS}), state


def accept(actor=REAL, agent=False, key='n:1', persona='p-marie'):
    return Event('accept_request', key, actor, agent, SPHERE, persona, {'service_id': 's1'})


def test_a_real_members_acceptance_is_confirmed_after_a_while():
    plans, state = run([accept()])
    assert [(p.persona_id, p.action, p.origin) for p in plans] == [('p-marie', 'confirm', 'real')]
    assert timedelta(minutes=2) <= plans[0].due_at - NOW <= timedelta(minutes=8)
    assert state.credits(SPHERE, NOW) == config.RIPPLE_PER_REAL_ACTION


def test_personas_react_to_personas_only_on_credits():
    # Nobody real has been around: a persona's acceptance waits for people.
    plans, _ = run([accept(actor='p-joe', agent=True)])
    assert plans == []
    # A real member's action first gives the sphere credits to spend.
    plans, state = run([Event('new_follower', 'n:0', REAL, False, SPHERE, 'p-emma'),
                        accept(actor='p-joe', agent=True, key='n:2')])
    assert [p.action for p in plans] == ['follow', 'confirm']
    assert plans[1].origin == 'ripple'
    assert state.credits(SPHERE, NOW) == config.RIPPLE_PER_REAL_ACTION - 1


def test_credits_fade_when_people_leave():
    _, state = run([Event('new_follower', 'n:0', REAL, False, SPHERE, 'p-emma')])
    later = NOW + timedelta(minutes=config.RIPPLE_MINUTES + 1)
    plans, _ = run([accept(actor='p-joe', agent=True, key='n:9')], state=state, now=later)
    assert plans == []


def test_credits_are_capped():
    events = [Event('new_follower', f'n:{i}', f'real-{i}', False, SPHERE, 'p-emma') for i in range(10)]
    _, state = run(events)
    assert state.credits(SPHERE, NOW) == config.RIPPLE_CAP


def test_nothing_is_planned_twice():
    state = State()
    first, _ = run([accept()], state=state)
    again, _ = run([accept(key='n:other-notification')], state=state)
    assert len(first) == 1 and again == []


def test_courtesies_to_one_member_are_limited_per_hour_but_replies_are_not():
    follows = [Event('new_follower', f'n:{i}', REAL, False, SPHERE, persona)
               for i, persona in enumerate(['p-marie', 'p-joe', 'p-emma', 'p-x', 'p-y'])]
    plans, _ = run(follows + [accept(key='n:acc')])
    courtesies = [p for p in plans if p.action == 'follow']
    assert len(courtesies) == config.PER_MEMBER_PER_HOUR
    assert any(p.action == 'confirm' for p in plans)       # essential: never dropped


def test_a_new_need_is_taken_up_by_the_closest_persona():
    e = Event('new_opening', 'o:1', REAL, False, SPHERE, ref={'service_id': 's9', 'candidates': ['p-emma', 'p-joe']})
    plans, _ = run([e], seed=3)
    assert plans[0].persona_id == 'p-emma' and plans[0].action == 'accept'
    assert all(p.persona_id != REAL for p in plans)


def test_nobody_takes_up_their_own_opening():
    e = Event('new_opening', 'o:2', 'p-emma', True, SPHERE, ref={'service_id': 's8', 'candidates': ['p-emma']})
    _, state = run([Event('new_follower', 'n:0', REAL, False, SPHERE, 'p-joe')])
    plans, _ = run([e], state=state, seed=1)
    assert all(p.persona_id != 'p-emma' for p in plans)


def test_finished_exchanges_get_the_personas_side_written():
    e = Event('exchange_finished', 'x:1:p-joe', REAL, False, SPHERE, 'p-joe',
              {'exchange_id': 'x1', 'side': 'receipt', 'standing': True})
    plans, state = run([e])
    assert [(p.action, p.payload['side']) for p in plans] == [('write_side', 'receipt')]
    # A standing state seen again earns the sphere no credits.
    assert state.credits(SPHERE, NOW) == 0


def test_between_personas_an_exchange_moves_only_while_people_are_around():
    open_ = Event('exchange_open', 'x:2:Initiated', 'p-emma', True, SPHERE, 'p-joe',
                  {'exchange_id': 'x2', 'status': 'Initiated', 'with_real': False, 'standing': True})
    done = Event('exchange_finished', 'x:3:p-joe', 'p-emma', True, SPHERE, 'p-joe',
                 {'exchange_id': 'x3', 'side': 'note', 'standing': True})
    # Nobody real around: nothing moves.
    plans, _ = run([open_, done])
    assert plans == []
    # Someone real did something: it moves on, spending a credit.
    plans, state = run([Event('new_follower', 'n:0', REAL, False, SPHERE, 'p-emma'), open_, done])
    assert [p.action for p in plans] == ['follow', 'advance', 'write_side']
    assert plans[1].payload['to'] == 'In Progress'


def test_with_a_real_member_the_persona_does_not_finish_the_exchange():
    e = Event('exchange_open', 'x:4:In Progress', REAL, False, SPHERE, 'p-joe',
              {'exchange_id': 'x4', 'status': 'In Progress', 'with_real': True, 'standing': True})
    plans, _ = run([e])
    assert plans == []


def test_a_new_member_is_welcomed():
    plans, _ = run([Event('member_joined', 'j:1', REAL, False, SPHERE)])
    assert [p.action for p in plans] == ['follow'] and plans[0].payload == {'user_id': REAL}
    assert plans[0].persona_id in PERSONAS
