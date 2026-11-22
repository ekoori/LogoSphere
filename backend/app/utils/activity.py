"""What the people you follow did lately, and whom you both know.

Neither shows anything that couldn't already be opened one by one: every item
passes the same Sight, a block either way hides it, and whom someone follows
is told to nobody else. Newest first, never ranked.
"""
from datetime import datetime

from app.models.acknowledgement import Acknowledgement
from app.models.follow import Follow
from app.models.meaning_trail import MeaningTrail
from app.models.openings import Service
from app.utils import demo, events, safety
from app.utils.access import Sight, as_uuid
from app.utils.names import resolve_user_names
from app.utils.trails import Trail

SHOWN, KNOWN_SHOWN, EXCERPT = 50, 24, 160
ACKS_LOOKED_AT = 200        # each costs reads to find whose trail it's on
DONE = ('Finished', 'Receipted', 'Additional Comments Added')


def humans(exchange):
    """The people on its two sides, initiator first: a group's is whoever acted for it."""
    return [exchange.initiator_acting_user_id or exchange.user_id,
            exchange.recipient_acting_user_id or exchange.other_user_id]


def _openings(sight, people):
    for s in Service.get_all():
        who = s.acting_user_id or s.provider_id
        if who not in people or not s.is_current or s.status == 'Cancelled':
            continue
        if s.cadence != 'perpetual' and s.status in ('In Progress', 'Completed'):
            continue        # taken: the exchange says it
        if not sight.opening(s):
            continue
        if s.type == 'need':
            says = 'asks to borrow' if s.borrow else 'needs'
        else:
            says = 'offers to lend' if s.borrow else 'offers'
        if s.acting_user_id and s.provider_name:
            says = f'for {s.provider_name} {says}'
        yield {'kind': 'opening', 'at': s.created_at, 'who': who, 'says': says, 'title': s.title or '',
               'link': f'/opening?id={s.service_id}', 'is_demo': demo.is_demo_sphere(s.sphere_id)}


def _exchanges(sight, people, hidden):
    found = [x for x in MeaningTrail.every_row()
             if x.exchange_status != 'Cancelled' and people & set(humans(x)) and not hidden & set(humans(x))]
    if not found:
        return
    names = MeaningTrail._name_map()
    for x in found:
        if not sight.exchange(x):
            continue
        first, second = humans(x)
        who, other = (first, x.other_user_id) if first in people else (second, x.user_id)
        done = x.exchange_status in DONE
        at = (x.receipted_at or x.finished_at) if done else None
        with_whom = 'you' if other == sight.id else names.get(other) or 'a member'
        yield {'kind': 'exchange', 'at': at or x.project_start_timestamp, 'who': who,
               'says': f"{'finished' if done else 'started'} an exchange with {with_whom}",
               'title': x.exchange_description or '', 'link': f'/exchange?id={x.exchange_id}',
               'is_demo': demo.exchange_is_demo(x)}


def _acknowledgements(sight, people, hidden):
    theirs = sorted((a for a in Acknowledgement.everything() if a.author_id in people),
                    key=lambda a: a.created_at or datetime.min, reverse=True)
    kept = 0
    for ack in theirs[:ACKS_LOOKED_AT]:
        trail = Trail.find(ack.trail_id)
        if not trail or not trail.readable(sight):
            continue
        if trail.kind == 'user' and trail.id in hidden:
            continue
        if trail.kind == 'exchange' and hidden & set(humans(trail.subject)):
            continue
        if trail.kind == 'user' and trail.id == sight.id:
            says, title = 'acknowledged you', ''
        else:
            says, title = 'acknowledged', trail.name
        yield {'kind': 'acknowledgement', 'at': ack.created_at, 'who': ack.author_id, 'says': says, 'title': title,
               'text': ack.body[:EXCERPT] + ('…' if len(ack.body) > EXCERPT else ''), 'link': trail.link,
               'is_demo': trail.kind != 'user' and demo.is_demo_sphere(trail.sphere_id)}
        kept += 1
        if kept >= SHOWN:
            return


def _events(sight, people):
    now = datetime.utcnow()
    for event in events.everything():
        if event.creator_id in people and event.visible(sight) and event.upcoming(now):
            yield {'kind': 'event', 'at': event.made_at, 'who': event.creator_id, 'says': 'put on', 'title': event.title,
                   'link': event.link, 'is_demo': demo.is_demo_sphere(event.sphere_id)}


def of_followed(viewer):
    sight = Sight(viewer)
    hidden = safety.hidden_from(sight.id)
    people = set(Follow.following_ids(sight.id)) - hidden - {sight.id}
    if not people:
        return []
    items = [*_openings(sight, people), *_exchanges(sight, people, hidden),
             *_acknowledgements(sight, people, hidden), *_events(sight, people)]
    items.sort(key=lambda item: item['at'] or datetime.min, reverse=True)
    items = items[:SHOWN]
    names = resolve_user_names({item['who'] for item in items})
    return [{**item, 'at': item['at'].isoformat() if item['at'] else None,
             'who': {'id': str(item['who']), 'name': names.get(item['who']) or 'A former member',
                     'is_agent': demo.is_agent(item['who'])}}
            for item in items]


def both_know(viewer, other):
    """People you follow or had an exchange with, who had an exchange with them.
    Only exchanges you can see count, so it tells you nothing new about theirs."""
    sight, them = Sight(viewer), as_uuid(other)
    me = sight.id
    if not them or them == me:
        return []
    hidden = safety.hidden_from(me)
    if them in hidden:
        return []
    mine, theirs = set(Follow.following_ids(me)), set()
    for x in MeaningTrail.every_row():
        sides = set(humans(x))
        if x.exchange_status == 'Cancelled' or not sides & {me, them} or not sight.exchange(x):
            continue
        if me in sides:
            mine |= sides
        if them in sides:
            theirs |= sides
    both = (mine & theirs) - {me, them, None} - hidden
    names = resolve_user_names(both)        # people only: a group has no name there
    known = sorted(names.items(), key=lambda pair: (pair[1].lower(), str(pair[0])))[:KNOWN_SHOWN]
    return [{'id': str(uid), 'name': name, 'is_agent': demo.is_agent(uid)} for uid, name in known]
