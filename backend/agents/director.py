"""The director: watch the demo spheres, plan the personas' reactions, act.

Each cycle it reads what changed - personas' inboxes, new openings and
appreciation in demo spheres, the personas' exchanges, new members - turns
that into Events, lets rules.plan() decide, queues the Plans, and runs the
ones that are due. Personas act only through the platform API.
"""
import logging
import random
import re
from datetime import datetime, timedelta

from agents import config, store
from agents.personas import load as load_personas
from agents.platform import Platform, PlatformError
from agents.rules import WRITING, Event, State, plan
from agents.writer import WriterError

log = logging.getLogger('agents')

LINK_ID = re.compile(r'id=([0-9a-fA-F-]{36})')


def _link_id(link):
    m = LINK_ID.search(link or '')
    return m.group(1) if m else None


class Director:
    def __init__(self, writer=None, illustrator=None, rng=None, clock=datetime.utcnow, personas=None):
        self.personas = {p.user_id: p for p in (personas if personas is not None else load_personas())}
        self.rng = rng or random.Random()
        self.clock = clock
        self._writer, self._illustrator = writer, illustrator
        self.clients = {}
        self.last = {}                       # observer -> when it last ran
        self.sphere_personas = {}            # demo sphere -> persona ids in it
        self.spheres = {}                    # demo sphere id -> {name, description, projects}
        self.openings = {}                   # demo opening id -> opening dict (latest read)
        self.usage = {'claude_in': 0, 'claude_out': 0, 'claude_calls': 0, 'images': 0}

    # ── Plumbing ─────────────────────────────────────────────────────────────
    def api(self, persona_id):
        if persona_id not in self.clients:
            p = self.personas[persona_id]
            self.clients[persona_id] = Platform(store.token_for(p.user_id, p.email))
        return self.clients[persona_id]

    def _count(self, tokens_in, tokens_out):
        self.usage['claude_in'] += tokens_in
        self.usage['claude_out'] += tokens_out
        self.usage['claude_calls'] += 1

    @property
    def writer(self):
        if self._writer is None:
            from agents.writer import Writer
            self._writer = Writer(usage=self._count)
        return self._writer

    @property
    def illustrator(self):
        if self._illustrator is None:
            from agents.images import Illustrator
            self._illustrator = Illustrator()
        return self._illustrator

    def due(self, name, seconds):
        now = self.clock()
        if name in self.last and now - self.last[name] < timedelta(seconds=seconds):
            return False
        self.last[name] = now
        return True

    def observer(self, sphere_id=None):
        """A persona who can see the sphere (or any persona)."""
        ids = self.sphere_personas.get(sphere_id) if sphere_id else None
        return (ids or list(self.personas))[0]

    def home_sphere(self, persona_id):
        for sid, ids in self.sphere_personas.items():
            if persona_id in ids:
                return sid
        return None

    # ── One cycle ────────────────────────────────────────────────────────────
    def cycle(self):
        if store.paused(self.clock()):
            log.info('Paused (the test suite is running)')
            return
        events = []
        if self.due('members', 300) or not self.sphere_personas:
            events += self.observe_members()
        if self.due('inbox', 30):
            events += self.observe_inbox()
        if self.due('openings', 60):
            events += self.observe_openings()
        if self.due('trails', 300):
            events += self.observe_trails()
        if events:
            self.plan_round(events)
        for task in store.due(self.clock(), limit=5):
            self.run_task(task)

    def plan_round(self, events):
        state = State(**(store.json_setting('rules_state') or {}))
        state.done = set(r.key for r in store.db.execute('SELECT key FROM agent_done'))
        plans = plan(events, state, now=self.clock(), rng=self.rng, sphere_personas=self.sphere_personas)
        for p in plans:
            store.enqueue(p.due_at, p.persona_id, p.action, p.payload, p.origin, p.sphere_id)
            store.mark_done(p.done_key)
            log.info('Planned: %s %s at %s (%s)', self.personas[p.persona_id].name, p.action,
                     p.due_at.strftime('%H:%M'), p.origin)
        store.set_json_setting('rules_state', {'ripple': state.ripple, 'member_hits': state.member_hits})

    # ── Observers ────────────────────────────────────────────────────────────
    def observe_members(self):
        events = []
        who = self.observer()
        for s in self.api(who).get('/api/spheres'):
            if not s.get('is_demo'):
                continue
            sid = s['sphere_id']
            detail = self.api(who).get(f'/api/spheres/{sid}')
            members = detail.get('members') or []
            self.spheres[sid] = {'name': detail.get('name'), 'description': detail.get('description'),
                                 'projects': detail.get('projects') or []}
            self.sphere_personas[sid] = [m['id'] for m in members if m['id'] in self.personas]
            real = sorted(m['id'] for m in members if not m.get('is_agent') and m.get('role') != 'pending')
            known = store.json_setting(f'members:{sid}')
            if known is not None:
                for uid in set(real) - set(known):
                    events.append(Event('member_joined', f'j:{sid}:{uid}', uid, False, sid))
            store.set_json_setting(f'members:{sid}', real)
        return events

    def observe_inbox(self):
        # The first pass only clears what piled up before the personas
        # existed: they don't answer September's notifications today.
        baseline = store.setting('baseline:inbox') is None
        events = []
        for pid in self.personas:
            try:
                inbox = self.api(pid).get('/api/notifications')
            except PlatformError as e:
                log.warning('Inbox of %s: %s', self.personas[pid].name, e)
                continue
            for n in inbox.get('notifications') or []:
                if n.get('is_read'):
                    continue
                event = None if baseline else self._from_notification(pid, n)
                if event:
                    events.append(event)
                try:
                    self.api(pid).post('/api/notifications/read',
                                       {'created_at': n['created_at'], 'notification_id': n['notification_id']})
                except PlatformError:
                    pass
        if baseline:
            store.set_setting('baseline:inbox', self.clock().isoformat())
        return events

    def _from_notification(self, pid, n):
        kind, actor = n.get('type'), n.get('actor_id')
        if not actor or actor == pid:
            return None
        key, agent = f"n:{n['notification_id']}", bool(n.get('actor_is_agent'))
        if kind == 'opening_accepted':
            sid = _link_id(n.get('link'))
            sphere = self._opening_sphere(pid, sid)
            if sphere not in self.sphere_personas:
                return None          # not a demo sphere: personas stay out of it
            return Event('accept_request', key, actor, agent, sphere, pid, {'service_id': sid})
        if kind == 'new_follower':
            return Event('new_follower', key, actor, agent, self.home_sphere(pid), pid)
        if kind == 'receipt_received':
            xid = _link_id(n.get('link'))
            if not xid:
                return None
            try:
                x = self.api(pid).get(f'/api/exchange/{xid}')['exchange']
            except PlatformError:
                return None
            if not x.get('is_demo'):
                return None
            return Event('receipt_received', key, actor, agent, self.home_sphere(pid), pid, {'exchange_id': xid})
        return None

    def _opening_sphere(self, pid, sid):
        if not sid:
            return None
        if sid in self.openings:
            return self.openings[sid].get('sphere_id')
        try:
            return self.api(pid).get(f'/api/openings/{sid}').get('sphere_id')
        except PlatformError:
            return None

    def observe_openings(self):
        seen_ids, items = set(), []
        for sid in self.sphere_personas:
            for o in self.api(self.observer(sid)).get('/api/openings'):
                if o.get('is_demo') and o['id'] not in seen_ids:
                    seen_ids.add(o['id'])
                    items.append(o)
        self.openings = {o['id']: o for o in items}
        events = []
        newest = max((o.get('created_at') or '' for o in items), default='')
        marker = store.setting('seen:openings')
        if marker is not None:
            for o in items:
                if (o.get('created_at') or '') > marker:
                    actor = o.get('acting_user_id') or o['provider_id']
                    events.append(Event('new_opening', f"o:{o['id']}", actor, bool(o.get('provider_is_agent')),
                                        o.get('sphere_id'), ref={'service_id': o['id'],
                                                                 'candidates': self._candidates(o)}))
        if newest and newest > (marker or ''):
            store.set_setting('seen:openings', newest)

        # Appreciation of a persona's opening by a real member, returned in kind.
        likes = {f"{o['id']}|{l['id']}": o for o in items if o.get('provider_is_agent')
                 for l in o.get('liked_by') or []}
        known = store.json_setting('seen:likes')
        if known is not None:
            for k in set(likes) - set(known):
                sid, liker = k.split('|')
                o = likes[k]
                persona = o.get('acting_user_id') or o['provider_id']
                if liker in self.personas or persona not in self.personas:
                    continue
                theirs = next((x['id'] for x in items if (x.get('acting_user_id') or x['provider_id']) == liker), None)
                events.append(Event('liked_persona_opening', f'l:{k}', liker, False, o.get('sphere_id'), persona,
                                    {'service_id': sid, 'their_opening': theirs}))
        store.set_json_setting('seen:likes', sorted(likes))
        return events

    def _candidates(self, opening):
        """Personas in the opening's sphere, closest value graphs first."""
        members = self.sphere_personas.get(opening.get('sphere_id'), [])
        q = f"{opening.get('title') or ''} {opening.get('description') or ''}".strip()
        ranked = []
        try:
            from urllib.parse import quote
            res = self.api(self.observer(opening.get('sphere_id'))).get(
                f'/api/search/vicinity?q={quote(q[:300])}&kinds=user&limit=50')
            for g in res.get('groups') or []:
                ranked += [i['id'] for i in g.get('items') or []]
        except PlatformError:
            pass
        out = [p for p in ranked if p in members]
        rest = [p for p in members if p not in out]
        self.rng.shuffle(rest)
        return out + rest

    def observe_trails(self):
        events = []
        for pid in self.personas:
            try:
                rows = self.api(pid).get('/api/meaning_trail')
            except PlatformError as e:
                log.warning('Trail of %s: %s', self.personas[pid].name, e)
                continue
            for r in rows:
                if not r.get('is_demo'):
                    continue
                events += self._from_trail_row(pid, r)
        return events

    def _from_trail_row(self, pid, r):
        xid, status = r['exchange_id'], r.get('exchange_status')
        initiator = r.get('initiator_acting_user_id') or r.get('initiator_id') or r.get('user_id')
        recipient = r.get('recipient_acting_user_id') or r.get('other_user_id')
        if pid == initiator:
            side, other, other_agent = 'note', recipient, bool(r.get('other_is_agent'))
        elif pid == recipient:
            side, other, other_agent = 'receipt', initiator, bool(r.get('initiator_is_agent'))
        else:
            return []
        sphere = (self.openings.get(r.get('source_service_id')) or {}).get('sphere_id') or self.home_sphere(pid)
        written = r.get('user_comment') if side == 'note' else r.get('gratitude_comment')
        out = []
        # Trail events describe a standing state, not something just done:
        # they earn no ripple credits (adds_credit=False via ref).
        if status in ('Finished', 'Receipted') and not written:
            out.append(Event('exchange_finished', f'x:{xid}:{pid}', other, other_agent, sphere, pid,
                             {'exchange_id': xid, 'side': side, 'standing': True}))
        if status in ('Initiated', 'In Progress') and side == 'note':
            out.append(Event('exchange_open', f'x:{xid}:{status}', other, other_agent, sphere, pid,
                             {'exchange_id': xid, 'status': status, 'with_real': not other_agent, 'standing': True}))
        if status == 'Receipted' and not other_agent:
            out.append(Event('exchange_receipted', f'x:{xid}:receipted', other, False, sphere, pid,
                             {'exchange_id': xid, 'parties': [pid, other], 'standing': True}))
        return out

    # ── Doing ────────────────────────────────────────────────────────────────
    def over_budget(self, action):
        if action not in WRITING:
            return False
        used = store.usage_today()
        return used['claude_calls'] >= config.DAILY_CLAUDE_CALLS

    def run_task(self, task):
        persona = self.personas.get(task['persona_id'])
        if persona is None:
            store.remove(task)
            return
        action, payload = task['action'], task['payload']
        if self.over_budget(action):
            log.info('Daily Claude budget reached; %s waits', action)
            store.postpone(task, 120)
            return
        if config.DRY_RUN:
            store.log_action(persona.user_id, action, f'dry run: would {action} {payload}', dry_run=True)
            log.info('Dry run: %s would %s %s', persona.name, action, payload)
            store.remove(task)
            return
        self.usage = {'claude_in': 0, 'claude_out': 0, 'claude_calls': 0, 'images': 0}
        try:
            detail = getattr(self, f'do_{action}')(persona, payload)
            store.log_action(persona.user_id, action, detail or action, **self.usage)
            log.info('%s: %s', persona.name, detail)
            store.remove(task)
        except PlatformError as e:
            if e.status >= 500:
                store.postpone(task, 10)
            else:
                store.log_action(persona.user_id, action, f'skipped: {e}', **self.usage)
                store.remove(task)
        except WriterError as e:
            log.warning('Writer failed (%s); %s retried later', e, action)
            store.postpone(task, 30)
        except Exception:
            log.exception('%s failed for %s', action, persona.name)
            store.log_action(persona.user_id, action, 'failed (see the journal)', **self.usage)
            store.remove(task)

    def do_confirm(self, p, payload):
        api, sid = self.api(p.user_id), payload['service_id']
        o = api.get(f'/api/openings/{sid}')
        match = next((a for a in o.get('pending_acceptances') or []
                      if payload['actor_id'] in (a.get('accepter_id'), a.get('acting_user_id'))), None)
        if not match:
            return f"nothing to confirm on '{o.get('title')}'"
        api.post(f'/api/openings/{sid}/confirm', {'accepter_id': match['accepter_id']})
        return f"confirmed {match.get('accepter_name')}'s acceptance of '{o.get('title')}'"

    def do_follow(self, p, payload):
        api, uid = self.api(p.user_id), payload['user_id']
        person = api.get(f'/api/users/{uid}')
        if person.get('is_following'):
            return f"already follows {person.get('name')}"
        api.post(f'/api/users/{uid}/follow')
        return f"followed {person.get('name')}"

    def do_like_opening(self, p, payload):
        r = self.api(p.user_id).post(f"/api/openings/{payload['service_id']}/like", {'liked': True})
        return f"appreciated opening {payload['service_id']} ({r.get('likes')} now)"

    def do_like_receipt(self, p, payload):
        api, xid = self.api(p.user_id), payload['exchange_id']
        x = api.get(f'/api/exchange/{xid}')['exchange']
        if ((x.get('likes') or {}).get('gratitude') or {}).get('liked'):
            return 'already appreciated that receipt'
        api.post(f'/api/exchange/{xid}/like', {'comment_type': 'gratitude'})
        return f"appreciated the receipt on '{x.get('exchange_description')}'"

    def do_accept(self, p, payload):
        api, sid = self.api(p.user_id), payload['service_id']
        api.post(f'/api/openings/{sid}/accept', {})
        title = (self.openings.get(sid) or {}).get('title') or sid
        return f"offered to take up '{title}'"

    def do_advance(self, p, payload):
        self.api(p.user_id).post(f"/api/exchange/{payload['exchange_id']}/status", {'status': payload['to']})
        return f"moved exchange {payload['exchange_id']} to {payload['to']}"

    def _exchange_story(self, p, xid):
        api = self.api(p.user_id)
        body = api.get(f'/api/exchange/{xid}')
        x = body['exchange']
        opening = self.openings.get(x.get('source_service_id')) or {}
        if not opening and x.get('source_service_id'):
            try:
                opening = api.get(f"/api/openings/{x['source_service_id']}")
            except PlatformError:
                opening = {}
        story = {'title': x.get('exchange_description'),
                 'description': x.get('exchange_long_description') or opening.get('description') or ''}
        return api, body, x, opening, story

    def do_write_side(self, p, payload):
        xid = payload['exchange_id']
        api, body, x, opening, story = self._exchange_story(p, xid)
        initiator = body.get('is_initiator')
        other = x.get('other_user_name') if initiator else x.get('initiator_name')
        # An offer's provider (the initiator) gave; a need's provider received.
        gave = bool(initiator) == ((opening.get('type') or 'offer') == 'offer')
        cards = api.get(f'/api/value_cards/{p.user_id}')
        card_by_id = {c['card_id']: c for c in cards}
        if initiator:
            if x.get('user_comment'):
                return 'note already written'
            text = self.writer.note(p, story, other, gave, cards)
            kind, extra = 'user', {}
        else:
            if x.get('gratitude_comment'):
                return 'receipt already written'
            text = self.writer.receipt(p, story, other, gave, cards)
            kind, extra = 'gratitude', {'frankl_mode': getattr(text, 'frankl_mode', None)}
        if text is None:
            return 'declined to write'
        ids = [i for i in text.card_ids if i in card_by_id][:2]
        api.post(f'/api/exchange/{xid}/comment', {
            'type': kind, 'text': text.text, 'card_ids': ids,
            'cards': [{'card_id': i, 'title': card_by_id[i].get('title'), 'color_key': card_by_id[i].get('color_key')}
                      for i in ids], **extra})
        return f"wrote their {'note' if initiator else 'receipt'} on '{story['title']}'"

    def do_acknowledge(self, p, payload):
        xid = payload['exchange_id']
        api, body, x, opening, story = self._exchange_story(p, xid)
        if x.get('other_comment'):
            return 'already acknowledged'
        parties = f"{x.get('initiator_name')} and {x.get('other_user_name')}"
        text = self.writer.acknowledgement(p, story, parties)
        if text is None:
            return 'declined to write'
        api.post(f'/api/exchange/{xid}/comment', {'type': 'other', 'text': text.text})
        return f"acknowledged '{story['title']}'"

    def do_post_opening(self, p, payload):
        sid, kind = payload['sphere_id'], payload.get('kind') or 'offer'
        sphere = self.spheres.get(sid) or {}
        projects = [x for x in sphere.get('projects') or [] if isinstance(x, str)]
        project = self.rng.choice(projects) if projects and self.rng.random() < 0.5 else None
        recent = [o.get('title') for o in self.openings.values() if o.get('sphere_id') == sid][:12]
        text = self.writer.opening(p, sphere, kind, project=project, recent=recent)
        if text is None:
            return 'declined to write'
        created = self.api(p.user_id).post('/api/openings', {
            'type': kind, 'title': text.title[:120], 'description': text.description,
            'sphere_id': sid, 'sphere_name': sphere.get('name'), 'project_name': project})
        detail = f"posted {kind} '{text.title}'"
        if self.rng.random() < config.IMAGE_SHARE and store.usage_today()['images'] < config.DAILY_IMAGES:
            try:
                image = self.illustrator.banner(f'{text.title}. {text.description}')
                self.api(p.user_id).upload(f"/api/openings/{created['service_id']}/image", 'image', image)
                self.usage['images'] += 1
                detail += ' with a banner'
            except Exception as e:      # no credit, outage: the opening stands without a picture
                log.warning('No banner for %s: %s', text.title, e)
        return detail
