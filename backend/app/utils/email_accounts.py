"""Email and accounts: joining, confirming an address, a forgotten password.

Joining is email first. Nothing is made until the link in the email is opened
and a password chosen there, so nobody can make an account, with a password
they know, for someone else's address.

Links are one-time. Only their hashes are stored, they carry the token in the
URL's fragment (which never reaches a server's log), and the pages they open
change nothing until a button is pressed (mail scanners open links).

The functions that send are queued (app/utils/mailer.queue).
"""
import hashlib
import secrets
from datetime import datetime

from app.db import session
from app.utils import mailer, mails, password_reset
from app.utils.access import as_uuid

SIGNUP, CONFIRM = 'signup', 'confirm'
LINK_HOURS = 24
RESET_HOURS = 2     # shorter than an administrator's link, which travels more slowly
NAME_MAX = 80

# Not `token`: CQL reserves it.
LINKS_DDL = ('CREATE TABLE IF NOT EXISTS email_links ('
             'link_hash text PRIMARY KEY, purpose text, email text, name text, user_id uuid, made_at timestamp) '
             'WITH default_time_to_live = 86400')
USER_DDL = 'ALTER TABLE users ADD IF NOT EXISTS email_confirmed_at timestamp'
# The invitation someone is signing up with, as its hash (app/utils/invites.py).
INVITE_DDL = 'ALTER TABLE email_links ADD IF NOT EXISTS invite text'

# Account email, at most: per address an hour, per address a day, altogether a day.
PER_ADDRESS_HOUR, PER_ADDRESS_DAY, ALL_DAY = 3, 8, 300


def ensure_tables():
    session.execute(LINKS_DDL)
    session.execute(INVITE_DDL)
    session.execute(USER_DDL)


def _hash(token):
    return hashlib.sha256(token.encode('utf-8')).hexdigest()


def _issue(purpose, email, name=None, user_id=None, invite=None):
    token = secrets.token_urlsafe(32)
    session.execute(
        'INSERT INTO email_links (link_hash, purpose, email, name, user_id, invite, made_at) '
        'VALUES (%s, %s, %s, %s, %s, %s, %s)',
        [_hash(token), purpose, email, name, user_id, invite, datetime.utcnow()])
    return token


def _read(purpose, token):
    if not isinstance(token, str) or not 20 <= len(token) <= 200:
        return None
    row = session.execute('SELECT purpose, email, name, user_id, invite FROM email_links WHERE link_hash = %s', [_hash(token)]).one()
    return row if row and row.purpose == purpose else None


def _spend(token):
    """True for whoever got here first."""
    return bool(session.execute('DELETE FROM email_links WHERE link_hash = %s IF EXISTS', [_hash(token)]).was_applied)


def _account(email):
    row = session.execute('SELECT user_id FROM user_credentials WHERE email = %s', [email]).one()
    return row.user_id if row else None


def _person(user_id):
    return session.execute('SELECT user_id, email, is_agent, email_confirmed_at FROM users WHERE user_id = %s',
                           [as_uuid(user_id)]).one()


def _may_write(email):
    return (mailer.deliverable(email)
            and mailer.take(f'to:{email}:hour', PER_ADDRESS_HOUR, mailer.HOUR)
            and mailer.take(f'to:{email}:day', PER_ADDRESS_DAY)
            and mailer.take('accounts:all', ALL_DAY))


def set_confirmed(user_id):
    if _person(user_id):        # an UPDATE would bring a deleted account's row back
        session.execute('UPDATE users SET email_confirmed_at = %s WHERE user_id = %s',
                        [datetime.utcnow(), as_uuid(user_id)])


# -- Joining -----------------------------------------------------------------
def send_sign_up(email, name, invite=None):
    """Either letter looks the same from outside: who has an account isn't told."""
    if not _may_write(email):
        return
    if _account(email):
        mailer.send(email, mails.have_account(mailer.site('/login')), 'sign-up')
        return
    token = _issue(SIGNUP, email, name=name, invite=invite)
    mailer.send(email, mails.finish_sign_up(mailer.site(f'/join#token={token}'), LINK_HOURS), 'sign-up')


def finish_sign_up(token, password):
    """(the new User, None, the invitation's hash if any) or (None, 'expired' | 'taken', None)."""
    from app.models.user import User        # models import utils
    link = _read(SIGNUP, token)
    if not link or not _spend(token):
        return None, 'expired', None
    if _account(link.email):
        return None, 'taken', None
    user = User.register({'name': link.name, 'email': link.email, 'password': password})
    if not user:
        return None, 'taken', None
    set_confirmed(user.user_id)
    return user, None, link.invite


# -- A forgotten password ----------------------------------------------------
def send_reset(email):
    uid = _account(email)
    person = _person(uid) if uid else None
    if not person or person.is_agent or not _may_write(email):
        return
    token, _ = password_reset.issue_reset_token(uid, hours=RESET_HOURS)
    mailer.send(email, mails.reset_password(mailer.site(f'/reset-password#token={token}'), RESET_HOURS), 'password-reset')


def send_password_changed(user_id):
    person = _person(user_id)
    if not person or person.is_agent or not mailer.deliverable(person.email):
        return
    if mailer.take(f'changed:{person.user_id}', 5):
        mailer.send(person.email, mails.password_changed(mailer.site('/login')), 'password-changed')


# -- Confirming the address of an account that has one ------------------------
def send_confirmation(user_id):
    person = _person(user_id)
    if not person or person.is_agent or person.email_confirmed_at:
        return
    email = (person.email or '').strip().lower()
    if not _may_write(email):
        return
    token = _issue(CONFIRM, email, user_id=person.user_id)
    mailer.send(email, mails.confirm_address(mailer.site(f'/confirm-email#token={token}'), LINK_HOURS), 'confirm-email')


def confirm(token):
    link = _read(CONFIRM, token)
    person = _person(link.user_id) if link and link.user_id else None
    if not person or (person.email or '').strip().lower() != link.email or not _spend(token):
        return False
    set_confirmed(person.user_id)
    return True


def forget(user_id):
    """A removed account's links."""
    uid = as_uuid(user_id)
    for row in session.execute('SELECT link_hash, user_id FROM email_links'):
        if row.user_id == uid:
            session.execute('DELETE FROM email_links WHERE link_hash = %s', [row.link_hash])
