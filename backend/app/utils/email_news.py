"""Notifications by email, for those who switched them on.

Off until a member picks topics, and then only to an address they confirmed.
An email carries the line their inbox has and a link, nothing more. Every one
can be stopped with one press, without signing in.
"""
import hmac
import logging
import re
import uuid

from app.db import session
from app.utils import demo, mailer, mails
from app.utils.access import as_uuid

log = logging.getLogger(__name__)

USER_DDL = 'ALTER TABLE users ADD IF NOT EXISTS email_topics set<text>'

EXCHANGES, GROUPS, THANKS, PERSONAS = 'exchanges', 'groups', 'thanks', 'personas'
TOPICS = (
    (EXCHANGES, 'Offers, needs and exchanges', 'Someone takes up, confirms or withdraws one, or leaves you a receipt.'),
    (GROUPS, 'Your groups', 'A new proposal in a group you belong to.'),
    (THANKS, 'Thanks and follows', 'An acknowledgement, a highlight, or a new follower.'),
    (PERSONAS, 'AI personas too', 'Also when it is one of the AI personas from the demo spheres.'),
)
KEYS = tuple(key for key, _, _ in TOPICS)

# Each kind of notification -> (its topic, the subject), or None: never emailed.
# Subjects are ours alone: a title someone typed doesn't belong on a lock screen.
KINDS = {
    'opening_accepted': (EXCHANGES, 'Someone wants to take up your opening'),
    'opening_confirmed': (EXCHANGES, 'Your exchange has started'),
    'opening_declined': (EXCHANGES, 'Your acceptance was declined'),
    'opening_cancelled': (EXCHANGES, 'An opening you accepted was withdrawn'),
    'receipt_received': (EXCHANGES, 'You were left a receipt'),
    'proposal_opened': (GROUPS, 'A new proposal in your group'),
    'acknowledgement': (THANKS, 'A new acknowledgement'),
    'acknowledgement_highlighted': (THANKS, 'Your acknowledgement was highlighted'),
    'new_follower': (THANKS, 'You have a new follower'),
    'demo_invite': None,
}
PER_PERSON_DAY, ALL_DAY = 20, 500
_STOP = re.compile(r'([0-9a-f]{32})\.([0-9a-f]{32})')


def ensure_tables():
    session.execute(USER_DDL)


def settings_of(user_id):
    """The member's own email settings, or None for no such member."""
    row = session.execute('SELECT email, is_agent, email_confirmed_at, email_topics FROM users WHERE user_id = %s',
                          [as_uuid(user_id)]).one()
    if not row:
        return None
    chosen = set(row.email_topics or ())
    return {
        'on': mailer.enabled(),
        'email': row.email,
        'can_receive': not row.is_agent and mailer.deliverable(row.email or ''),
        'confirmed': bool(row.email_confirmed_at),
        'topics': [key for key in KEYS if key in chosen],
        'choices': [{'key': key, 'label': label, 'about': about} for key, label, about in TOPICS],
    }


def choose(user_id, topics):
    session.execute('UPDATE users SET email_topics = %s WHERE user_id = %s',
                    [set(topics) or None, as_uuid(user_id)])


# -- Sending -----------------------------------------------------------------
def notify(user_id, actor_id, kind, message, link):
    """Called for every notification. It must never break what caused it."""
    try:
        if KINDS.get(kind) and mailer.enabled():
            mailer.queue(_send, user_id, actor_id, kind, message, link)
    except Exception as e:  # noqa: BLE001
        log.warning('Email notification not queued: %s', type(e).__name__)


def _send(user_id, actor_id, kind, message, link):
    uid = as_uuid(user_id)
    row = session.execute('SELECT email, is_agent, email_confirmed_at, email_topics FROM users WHERE user_id = %s',
                          [uid]).one() if uid else None
    if not row or row.is_agent or not row.email_confirmed_at:
        return
    topic, subject = KINDS[kind]
    chosen = set(row.email_topics or ())
    if topic not in chosen or (PERSONAS not in chosen and actor_id and demo.is_agent(actor_id)):
        return
    if not mailer.deliverable(row.email or ''):
        return
    if not mailer.take(f'news:{uid}', PER_PERSON_DAY) or not mailer.take('news:all', ALL_DAY):
        return
    token = stop_token(uid)
    where = link if isinstance(link, str) and link.startswith('/') and not link.startswith('//') else '/'
    mailer.send(
        row.email,
        mails.news(subject, message, mailer.site(where), mailer.site(f'/unsubscribe#{token}'), mailer.site('/settings#email')),
        'notification',
        # RFC 8058: a mail program's own Unsubscribe button posts here.
        headers={'List-Unsubscribe': f"<{mailer.site(f'/api/email/unsubscribe/{token}')}>",
                 'List-Unsubscribe-Post': 'List-Unsubscribe=One-Click'})


# -- Stopping ----------------------------------------------------------------
def stop_token(user_id):
    """Signed rather than stored. All it can ever do is switch these emails off."""
    uid = as_uuid(user_id).hex
    return f"{uid}.{mailer.signed(f'email-off:{uid}')[:32]}"


def stop(token):
    """Every topic off; False for a link that isn't ours."""
    match = _STOP.fullmatch(token or '')
    if not match or not hmac.compare_digest(match.group(2), mailer.signed(f'email-off:{match.group(1)}')[:32]):
        return False
    uid = uuid.UUID(match.group(1))
    if session.execute('SELECT user_id FROM users WHERE user_id = %s', [uid]).one():
        choose(uid, ())
    return True
