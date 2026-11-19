"""What the personas do about what they see - pure functions, no I/O.

The director turns API reads into Events and hands them to plan(), which
returns Plans (a persona, an action, when) and the updated State. Everything
here is deterministic given the rng, so it is tested directly.

Rules:
- Only things in demo spheres happen at all (the director only observes those).
- Something a real member did always gets its reactions, and gives the sphere
  ripple credits. Something a persona did gets a reaction only while the
  sphere has credits, and each such reaction spends one. Credits fade.
- Essential replies (confirming an acceptance, writing one's side of an
  exchange) are never dropped for a busy member; courtesies (likes, follows,
  offers of help) are limited per member per hour.
- Nothing is planned twice: every plan carries a done key.
"""
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Dict, List, Optional

from agents import config


@dataclass(frozen=True)
class Event:
    kind: str                      # see REACTIONS below
    key: str                       # unique per event, for "seen"
    actor_id: Optional[str]        # who did it
    actor_is_agent: bool
    sphere_id: Optional[str]
    persona_id: Optional[str] = None   # whose inbox / trail it showed up in
    ref: dict = field(default_factory=dict)


@dataclass
class Plan:
    persona_id: str
    action: str
    payload: dict
    due_at: datetime
    origin: str                    # 'real' | 'ripple'
    sphere_id: Optional[str]
    done_key: str
    member_id: Optional[str] = None    # the real member a courtesy is aimed at


@dataclass
class State:
    ripple: Dict[str, dict] = field(default_factory=dict)       # sphere -> {credits, at}
    member_hits: Dict[str, List[str]] = field(default_factory=dict)   # member -> [iso times]
    done: set = field(default_factory=set)                     # done keys known this round

    def credits(self, sphere_id, now):
        r = self.ripple.get(sphere_id or '')
        if not r:
            return 0.0
        if now - datetime.fromisoformat(r['at']) > timedelta(minutes=config.RIPPLE_MINUTES):
            return 0.0
        return float(r['credits'])

    def add_credits(self, sphere_id, now):
        have = self.credits(sphere_id, now)
        self.ripple[sphere_id or ''] = {'credits': min(config.RIPPLE_CAP, have + config.RIPPLE_PER_REAL_ACTION),
                                        'at': now.isoformat()}

    def spend_credit(self, sphere_id, now):
        have = self.credits(sphere_id, now)
        if have < 1:
            return False
        self.ripple[sphere_id or ''] = {'credits': have - 1, 'at': self.ripple[sphere_id or '']['at']}
        return True

    def member_ok(self, member_id, now):
        hits = [t for t in self.member_hits.get(member_id, [])
                if now - datetime.fromisoformat(t) < timedelta(hours=1)]
        self.member_hits[member_id] = hits
        return len(hits) < config.PER_MEMBER_PER_HOUR

    def hit_member(self, member_id, now):
        self.member_hits.setdefault(member_id, []).append(now.isoformat())


def _later(rng, now, low_minutes, high_minutes):
    return now + timedelta(minutes=rng.uniform(low_minutes, high_minutes))


def plan(events, state, now=None, rng=None, sphere_personas=None):
    """-> list of Plans. `sphere_personas` maps a sphere id to the persona ids
    who belong to it (for choosing who responds)."""
    now = now or datetime.utcnow()
    rng = rng or random.Random()
    sphere_personas = sphere_personas or {}
    plans = []

    def add(persona_id, action, payload, due_at, origin, event, done_key, member_id=None, essential=False):
        if done_key in state.done or not persona_id:
            return
        if member_id and not essential:
            if not state.member_ok(member_id, now):
                return
            state.hit_member(member_id, now)
        state.done.add(done_key)
        plans.append(Plan(persona_id, action, payload, due_at, origin, event.sphere_id, done_key, member_id))

    for e in events:
        real = not e.actor_is_agent
        # Something a real member just did livens the sphere up; a standing
        # state seen again (an exchange still waiting) does not.
        if real and not e.ref.get('standing'):
            state.add_credits(e.sphere_id, now)
        origin = 'real' if real else 'ripple'
        handler = REACTIONS.get(e.kind)
        if handler is None:
            continue
        # A persona reacting to a persona costs a credit; no credit, no reaction.
        if not real and handler.ripple_cost and not state.spend_credit(e.sphere_id, now):
            continue
        handler(e, origin, add, now, rng, sphere_personas, state)
    return plans


# ── Reactions ────────────────────────────────────────────────────────────────
def _reaction(ripple_cost=True):
    def wrap(fn):
        fn.ripple_cost = ripple_cost
        return fn
    return wrap


@_reaction()
def _accept_request(e, origin, add, now, rng, sp, state):
    """Someone wants to accept a persona's opening: the persona confirms."""
    add(e.persona_id, 'confirm', {'service_id': e.ref['service_id'], 'actor_id': e.actor_id},
        _later(rng, now, 2, 8), origin, e, f"confirm:{e.ref['service_id']}:{e.actor_id}",
        member_id=e.actor_id if origin == 'real' else None, essential=True)


@_reaction()
def _new_follower(e, origin, add, now, rng, sp, state):
    add(e.persona_id, 'follow', {'user_id': e.actor_id}, _later(rng, now, 1, 6), origin, e,
        f'follow:{e.persona_id}:{e.actor_id}', member_id=e.actor_id if origin == 'real' else None)


@_reaction()
def _receipt_received(e, origin, add, now, rng, sp, state):
    add(e.persona_id, 'like_receipt', {'exchange_id': e.ref['exchange_id']}, _later(rng, now, 3, 12), origin, e,
        f"like_receipt:{e.ref['exchange_id']}:{e.persona_id}")


@_reaction()
def _new_opening(e, origin, add, now, rng, sp, state):
    """A new opening in a demo sphere: the best-matching persona offers to take
    it up; another may appreciate it. Less eager when a persona posted it."""
    provider = e.actor_id
    candidates = [p for p in e.ref.get('candidates') or sp.get(e.sphere_id, []) if p != provider]
    if not candidates:
        return
    member = provider if origin == 'real' else None
    if origin == 'real' or rng.random() < 0.3:
        add(candidates[0], 'accept', {'service_id': e.ref['service_id']}, _later(rng, now, 3, 15), origin, e,
            f"accept:{e.ref['service_id']}:{candidates[0]}", member_id=member)
    if len(candidates) > 1 and rng.random() < (0.6 if origin == 'real' else 0.4):
        liker = candidates[1 + rng.randrange(len(candidates) - 1)]
        add(liker, 'like_opening', {'service_id': e.ref['service_id']}, _later(rng, now, 2, 20), origin, e,
            f"like_opening:{e.ref['service_id']}:{liker}", member_id=member)
    # Now and then a persona posts something of their own while people are around.
    if origin == 'real' and rng.random() < 0.2 and state.credits(e.sphere_id, now) >= 2:
        poster = candidates[rng.randrange(len(candidates))]
        add(poster, 'post_opening', {'sphere_id': e.sphere_id, 'kind': rng.choice(['offer', 'need'])},
            _later(rng, now, 20, 90), origin, e, f"post_opening:{e.key}")


@_reaction()
def _liked_persona_opening(e, origin, add, now, rng, sp, state):
    """Appreciation returned: the persona appreciates one of the member's openings."""
    target = e.ref.get('their_opening')
    if not target:
        return
    add(e.persona_id, 'like_opening', {'service_id': target}, _later(rng, now, 5, 30), origin, e,
        f'like_opening:{target}:{e.persona_id}', member_id=e.actor_id if origin == 'real' else None)


@_reaction(ripple_cost=False)
def _exchange_finished(e, origin, add, now, rng, sp, state):
    """The persona writes its own side of a finished exchange."""
    if origin == 'ripple' and state.credits(e.sphere_id, now) < 1:
        return       # persona-to-persona: waits until people are around
    add(e.persona_id, 'write_side', {'exchange_id': e.ref['exchange_id'], 'side': e.ref['side']},
        _later(rng, now, 5, 30), origin, e, f"write_side:{e.ref['exchange_id']}:{e.persona_id}", essential=True)


@_reaction(ripple_cost=False)
def _exchange_open(e, origin, add, now, rng, sp, state):
    """An exchange the persona started is waiting to move on. With a real
    member, the persona only moves it to In Progress (the member decides when
    it's finished); between personas it moves along over a few hours."""
    status, with_real = e.ref['status'], e.ref.get('with_real', False)
    if status == 'Initiated':
        add(e.persona_id, 'advance', {'exchange_id': e.ref['exchange_id'], 'to': 'In Progress'},
            _later(rng, now, 30, 90) if with_real else _later(rng, now, 10, 40),
            'real' if with_real else 'ripple', e, f"advance:{e.ref['exchange_id']}:In Progress", essential=True)
    elif status == 'In Progress' and not with_real:
        add(e.persona_id, 'advance', {'exchange_id': e.ref['exchange_id'], 'to': 'Finished'},
            _later(rng, now, 60, 240), 'ripple', e, f"advance:{e.ref['exchange_id']}:Finished", essential=True)


@_reaction()
def _member_joined(e, origin, add, now, rng, sp, state):
    if origin != 'real':
        return
    personas = sp.get(e.sphere_id, [])
    if not personas:
        return
    greeter = personas[rng.randrange(len(personas))]
    add(greeter, 'follow', {'user_id': e.actor_id}, _later(rng, now, 5, 20), origin, e,
        f'follow:{greeter}:{e.actor_id}', member_id=e.actor_id)


@_reaction()
def _exchange_receipted(e, origin, add, now, rng, sp, state):
    """A finished exchange with a real member: a third persona may acknowledge it."""
    if origin != 'real' or rng.random() >= 0.3:
        return
    others = [p for p in sp.get(e.sphere_id, []) if p not in (e.ref.get('parties') or [])]
    if not others:
        return
    who = others[rng.randrange(len(others))]
    add(who, 'acknowledge', {'exchange_id': e.ref['exchange_id']}, _later(rng, now, 30, 180), origin, e,
        f"acknowledge:{e.ref['exchange_id']}")


REACTIONS = {
    'accept_request': _accept_request,
    'new_follower': _new_follower,
    'receipt_received': _receipt_received,
    'new_opening': _new_opening,
    'liked_persona_opening': _liked_persona_opening,
    'exchange_finished': _exchange_finished,
    'exchange_open': _exchange_open,
    'member_joined': _member_joined,
    'exchange_receipted': _exchange_receipted,
}

# Actions that need Claude (and count toward the daily cap).
WRITING = {'write_side', 'post_opening', 'acknowledge'}
