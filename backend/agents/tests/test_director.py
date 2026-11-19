"""The director end to end against an in-memory store and a fake platform."""
import types
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from agents import config
from agents.personas import Persona

NOW = datetime(2026, 11, 20, 10, 0)
SPHERE = 'sph-1'
MARIE, JOE, REAL = 'p-marie', 'p-joe', 'real-1'


class FakeStore(types.ModuleType):
    """Just enough of agents.store, in memory."""

    def __init__(self):
        super().__init__('fake_store')
        self.settings, self.queue, self.done, self.log = {}, [], set(), []
        self.db = SimpleNamespace(execute=lambda q, *a: [SimpleNamespace(key=k) for k in self.done])

    def paused(self, now=None): return False
    def setting(self, k, d=None): return self.settings.get(k, d)
    def set_setting(self, k, v): self.settings[k] = v
    def json_setting(self, k, d=None): return self.settings.get(k, d)
    def set_json_setting(self, k, v): self.settings[k] = v
    def mark_done(self, k): self.done.add(k)
    def token_for(self, uid, email): return f'token-{uid}'
    def usage_today(self): return {'claude_calls': 0, 'images': 0, 'actions': 0, 'claude_in': 0, 'claude_out': 0}

    def enqueue(self, due_at, persona_id, action, payload, origin='real', sphere_id=None):
        self.queue.append({'due_at': due_at, 'task_id': len(self.queue), 'persona_id': persona_id,
                           'action': action, 'payload': payload, 'origin': origin, 'sphere_id': sphere_id})

    def due(self, now=None, limit=10):
        return [t for t in self.queue if t['due_at'] <= now][:limit]

    def remove(self, task): self.queue.remove(task)
    def postpone(self, task, minutes): task['due_at'] += timedelta(minutes=minutes)

    def log_action(self, persona_id, action, detail, **kw):
        self.log.append((persona_id, action, detail, kw))


class FakeApi:
    def __init__(self, routes, calls, who):
        self.routes, self.calls, self.who = routes, calls, who

    def get(self, path):
        self.calls.append((self.who, 'GET', path, None))
        value = self.routes.get(('GET', path))
        return value(self.who) if callable(value) else value

    def post(self, path, body=None):
        self.calls.append((self.who, 'POST', path, body))
        value = self.routes.get(('POST', path), {})
        return value(self.who) if callable(value) else value

    def upload(self, path, field, data, **kw):
        self.calls.append((self.who, 'UPLOAD', path, len(data)))
        return {}


@pytest.fixture
def world(monkeypatch):
    from agents import director as director_mod
    fake = FakeStore()
    monkeypatch.setattr(director_mod, 'store', fake)
    monkeypatch.setattr(config, 'DRY_RUN', False)
    personas = [Persona(MARIE, 'Marie Kondo', 'm@example.com', 'Tidy neighbour', 'Calm'),
                Persona(JOE, 'Joe Rogan', 'j@example.com', 'Fitness in the park', 'Casual')]
    routes, calls = {}, []
    clock = {'now': NOW}
    d = director_mod.Director(personas=personas, clock=lambda: clock['now'])
    monkeypatch.setattr(d, 'api', lambda pid: FakeApi(routes, calls, pid))
    d.sphere_personas = {SPHERE: [MARIE, JOE]}
    d.spheres = {SPHERE: {'name': 'Riverside Commons', 'description': 'A neighbourhood', 'projects': []}}
    return SimpleNamespace(d=d, store=fake, routes=routes, calls=calls, clock=clock)


def test_a_real_acceptance_is_confirmed_through_the_api(world):
    w = world
    w.routes[('GET', '/api/notifications')] = lambda who: {'notifications': [{
        'notification_id': 'n1', 'created_at': '2026-11-20T09:59:00', 'type': 'opening_accepted',
        'actor_id': REAL, 'actor_is_agent': False, 'link': '/opening?id=00000000-0000-0000-0000-0000000000aa',
        'is_read': False}]} if who == MARIE else {'notifications': []}
    w.d.openings = {'00000000-0000-0000-0000-0000000000aa': {'sphere_id': SPHERE, 'title': 'Tool board'}}
    w.routes[('GET', '/api/openings/00000000-0000-0000-0000-0000000000aa')] = {
        'title': 'Tool board', 'pending_acceptances': [{'accepter_id': REAL, 'accepter_name': 'Ada'}]}

    w.store.settings['baseline:inbox'] = '2026-11-19T00:00:00'     # past the first pass
    events = w.d.observe_inbox()
    w.d.plan_round(events)
    assert [t['action'] for t in w.store.queue] == ['confirm']
    assert ('p-marie', 'POST', '/api/notifications/read',
            {'created_at': '2026-11-20T09:59:00', 'notification_id': 'n1'}) in w.calls

    w.clock['now'] = NOW + timedelta(minutes=10)
    for task in w.store.due(w.clock['now']):
        w.d.run_task(task)
    assert (MARIE, 'POST', '/api/openings/00000000-0000-0000-0000-0000000000aa/confirm',
            {'accepter_id': REAL}) in w.calls
    assert w.store.queue == [] and "confirmed Ada's acceptance" in w.store.log[-1][2]


def test_nothing_outside_demo_spheres(world):
    w = world
    w.d.openings = {}
    w.routes[('GET', '/api/openings/x')] = {'sphere_id': 'real-sphere'}
    n = {'notification_id': 'n2', 'created_at': '2026-11-20T09:00:00', 'type': 'opening_accepted',
         'actor_id': REAL, 'actor_is_agent': False, 'link': '/opening?id=x', 'is_read': False}
    assert w.d._from_notification(MARIE, n) is None


def test_dry_run_only_logs(world, monkeypatch):
    w = world
    monkeypatch.setattr(config, 'DRY_RUN', True)
    w.store.enqueue(NOW, JOE, 'follow', {'user_id': REAL})
    w.d.run_task(w.store.queue[0])
    assert not [c for c in w.calls if c[1] == 'POST']
    assert w.store.log[-1][2].startswith('dry run: would follow')


def test_following_back_never_unfollows(world):
    w = world
    w.routes[('GET', f'/api/users/{REAL}')] = {'name': 'Ada', 'is_following': True}
    assert w.d.do_follow(w.d.personas[JOE], {'user_id': REAL}) == 'already follows Ada'
    assert not [c for c in w.calls if c[1] == 'POST']


def test_a_receipt_is_written_with_the_personas_own_cards(world):
    w = world
    xid = 'x1'
    w.routes[('GET', f'/api/exchange/{xid}')] = {'is_initiator': False, 'is_other': True, 'exchange': {
        'exchange_description': 'Fence rebuild', 'exchange_long_description': 'We reset the posts.',
        'initiator_name': 'Ada', 'other_user_name': 'Marie Kondo', 'source_service_id': None}}
    w.routes[('GET', f'/api/value_cards/{MARIE}')] = [{'card_id': 'c1', 'title': 'Intentional space', 'color_key': 'sage'}]
    written = SimpleNamespace(text='It meant a lot.', frankl_mode='experiential', card_ids=['c1', 'not-mine'])
    w.d._writer = SimpleNamespace(receipt=lambda *a, **k: written)
    detail = w.d.do_write_side(w.d.personas[MARIE], {'exchange_id': xid, 'side': 'receipt'})
    post = next(c for c in w.calls if c[1] == 'POST')
    assert post[2] == f'/api/exchange/{xid}/comment'
    assert post[3]['type'] == 'gratitude' and post[3]['card_ids'] == ['c1'] and post[3]['frankl_mode'] == 'experiential'
    assert 'receipt' in detail


def test_the_daily_budget_holds_writing_back(world, monkeypatch):
    w = world
    monkeypatch.setattr(w.store, 'usage_today', lambda: {'claude_calls': config.DAILY_CLAUDE_CALLS, 'images': 0})
    w.store.enqueue(NOW, JOE, 'post_opening', {'sphere_id': SPHERE, 'kind': 'offer'})
    task = w.store.queue[0]
    w.d.run_task(task)
    assert task in w.store.queue and task['due_at'] > NOW       # postponed, not run


def test_the_first_inbox_pass_answers_nothing_old(world):
    w = world
    w.routes[('GET', '/api/notifications')] = {'notifications': [{
        'notification_id': 'old', 'created_at': '2026-09-12T00:33:41', 'type': 'new_follower',
        'actor_id': REAL, 'actor_is_agent': False, 'link': '/user?id=x', 'is_read': False}]}
    assert w.d.observe_inbox() == []
    assert 'baseline:inbox' in w.store.settings
    assert any(c[2] == '/api/notifications/read' for c in w.calls)     # cleared, not answered


def test_a_post_can_ask_for_its_banner(world):
    w = world
    w.routes[('POST', '/api/openings')] = {'service_id': 'o-new'}
    w.d._writer = SimpleNamespace(opening=lambda *a, **k: SimpleNamespace(
        title='Long ladder free to borrow', description='Knock on my door.'))
    w.d._illustrator = SimpleNamespace(banner=lambda subject: b'jpeg-bytes')
    detail = w.d.do_post_opening(w.d.personas[JOE], {'sphere_id': SPHERE, 'kind': 'offer', 'banner': True})
    assert ('p-joe', 'UPLOAD', '/api/openings/o-new/image', len(b'jpeg-bytes')) in w.calls
    assert 'with a banner' in detail
    w.calls.clear()
    w.routes[('POST', '/api/openings')] = {'service_id': 'o-two'}
    detail = w.d.do_post_opening(w.d.personas[JOE], {'sphere_id': SPHERE, 'kind': 'need', 'banner': False})
    assert not any(c[1] == 'UPLOAD' for c in w.calls) and 'banner' not in detail
