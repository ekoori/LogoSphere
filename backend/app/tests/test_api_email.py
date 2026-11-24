# Email: joining, forgotten passwords and opt-in notifications, with a stand-in
# for Mailgun. conftest switches email off, so nothing here can really send.
import re
import uuid
from pathlib import Path

import pytest

from app.models.notification import Notification
from app.utils import email_news, mailer, mails

PASSWORD = 'first-password-1'
SITE = 'https://site.test'


class Inline:
    def submit(self, job, *args):
        job(*args)


class Mailgun:
    """Keeps what it was sent; answers `statuses` in turn, then 200."""

    def __init__(self):
        self.sent, self.statuses, self.calls = [], [], 0

    def __call__(self, url, key, fields):
        self.calls += 1
        status = self.statuses.pop(0) if self.statuses else 200
        if status == 200:
            self.sent.append({'url': url, 'key': key, **dict(fields)})
        return status

    def to(self, address):
        return [m for m in self.sent if m['to'] == address]


def token_in(message, page):
    found = re.search(re.escape(f'{SITE}/{page}#token=') + r'([\w-]+)', message['text'])
    assert found, f'no {page} link in: {message["text"]}'
    return found.group(1)


@pytest.fixture
def mail(db, monkeypatch, tmp_path):
    fake = Mailgun()
    for name, value in (('MAIL', 'on'), ('MAILGUN_API_KEY', 'test-key'), ('MAILGUN_DOMAIN', 'mg.example.com'),
                        ('SITE_URL', SITE), ('MAIL_ENV_FILE', str(tmp_path / 'none.env'))):
        monkeypatch.setenv(name, value)
    for name in ('MAILGUN_BASE', 'MAIL_FROM', 'MAIL_TEST_MODE'):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(mailer, '_post', fake)
    monkeypatch.setattr(mailer, '_pool', Inline())
    monkeypatch.setattr(mailer, 'RETRY_WAITS', (0, 0))
    # The tests' members live at example.com, so a slip couldn't reach anyone.
    monkeypatch.setattr(mailer, 'RESERVED', ('invalid',))
    run, used = uuid.uuid4().hex, set()

    def bucket(name):
        key = f'test:{run}:{name}'
        used.add(key)
        return key

    monkeypatch.setattr(mailer, '_bucket', bucket)      # never the real allowances
    yield fake
    for key in used:
        db.execute('DELETE FROM mail_counts WHERE bucket = %s', [key])


@pytest.fixture
def visitor(app, db, mail, new_member):
    """(a signed-out client, a fresh address). What they made goes afterwards."""
    yield app.test_client(), new_member
    row = db.execute('SELECT user_id FROM user_credentials WHERE email = %s', [new_member]).one()
    uid = row.user_id if row else None
    if uid:
        for table, column in (('sessions', 'session_id'), ('password_resets', 'token_hash')):
            for r in db.execute(f'SELECT {column} AS key, user_id FROM {table}'):
                if r.user_id == uid:
                    db.execute(f'DELETE FROM {table} WHERE {column} = %s', [r.key])
    for r in db.execute('SELECT link_hash, email FROM email_links'):
        if r.email == new_member:
            db.execute('DELETE FROM email_links WHERE link_hash = %s', [r.link_hash])


@pytest.fixture
def joined(visitor, mail):
    """A member who joined by email: (client, address, id, their header)."""
    client, email = visitor
    assert client.post('/api/register', json={'name': 'Test Joiner', 'email': email}).status_code == 200
    token = token_in(mail.to(email)[-1], 'join')
    r = client.post('/api/register/confirm', json={'token': token, 'password': PASSWORD})
    assert r.status_code == 200, r.get_json()
    uid = r.get_json()['user_id']
    r = client.post('/api/login', json={'email': email, 'password': PASSWORD})
    assert r.status_code == 200
    mail.sent.clear()
    return client, email, uid, {'Authorization': f"Bearer {r.get_json()['session_id']}"}


# -- Joining -----------------------------------------------------------------
def test_no_account_until_the_link_is_used(db, visitor, mail):
    client, email = visitor
    r = client.post('/api/register', json={'name': 'Test Joiner', 'email': email.upper(), 'password': 'ignored-1234'})
    assert r.status_code == 200 and r.get_json()['confirm_email'] is True and 'user_id' not in r.get_json()
    assert not db.execute('SELECT user_id FROM user_credentials WHERE email = %s', [email]).one()

    message, = mail.to(email)
    assert message['o:tracking-clicks'] == message['o:tracking'] == 'no'
    assert message['o:require-tls'] == 'yes' and message['url'].endswith('/v3/mg.example.com/messages')
    token = token_in(message, 'join')
    assert token not in str([tuple(row) for row in db.execute('SELECT * FROM email_links')])     # hashes only

    assert client.post('/api/register/confirm', json={'token': token, 'password': 'short'}).status_code == 400
    r = client.post('/api/register/confirm', json={'token': token, 'password': PASSWORD})
    assert r.status_code == 200, r.get_json()
    assert client.post('/api/register/confirm', json={'token': token, 'password': PASSWORD}).status_code == 400
    assert client.post('/api/login', json={'email': email, 'password': 'ignored-1234'}).status_code == 401
    r = client.post('/api/login', json={'email': email, 'password': PASSWORD})
    assert r.status_code == 200
    mine = client.get('/api/account/email', headers={'Authorization': f"Bearer {r.get_json()['session_id']}"}).get_json()
    assert mine['confirmed'] is True and mine['topics'] == []       # opt-in: nothing on


def test_joining_never_tells_who_has_an_account(joined, mail):
    client, email, _, _ = joined
    again = client.post('/api/register', json={'name': 'Someone Else', 'email': email})
    fresh = client.post('/api/register', json={'name': 'Someone Else', 'email': f'nobody-{uuid.uuid4().hex[:8]}@elsewhere.invalid'})
    assert again.status_code == 200 and fresh.status_code == 400       # (an address nothing can reach is refused)
    message, = mail.to(email)
    assert '/join#' not in message['text'] and 'already' in message['subject']


def test_same_answer_for_a_new_and_a_known_address(db, joined, mail):
    client, email, _, _ = joined
    other = f'test-fresh-{uuid.uuid4().hex[:8]}@example.com'
    try:
        one = client.post('/api/register', json={'name': 'Someone', 'email': email})
        two = client.post('/api/register', json={'name': 'Someone', 'email': other})
        assert (one.status_code, one.get_json()) == (two.status_code, two.get_json())
    finally:
        for r in db.execute('SELECT link_hash, email FROM email_links'):
            if r.email == other:
                db.execute('DELETE FROM email_links WHERE link_hash = %s', [r.link_hash])


def test_a_name_never_reaches_the_sign_up_email(visitor, mail):
    client, email = visitor
    client.post('/api/register', json={'name': 'Your prize waits at http://bad.invalid/win', 'email': email})
    message, = mail.to(email)
    assert 'prize' not in message['text'] + message['html'] + message['subject']


# -- Forgotten passwords -------------------------------------------------------
def test_forgot_then_a_new_password(db, joined, mail):
    client, email, uid, _ = joined
    nobody = client.post('/api/password/forgot', json={'email': f'none-{uuid.uuid4().hex}@example.com'})
    known = client.post('/api/password/forgot', json={'email': f' {email.upper()} '})
    assert (nobody.status_code, nobody.get_json()) == (known.status_code, known.get_json())
    assert len(mail.sent) == 1
    token = token_in(mail.to(email)[0], 'reset-password')

    db.execute('UPDATE users SET email_confirmed_at = null WHERE user_id = %s', [uuid.UUID(uid)])
    r = client.post('/api/password/reset', json={'token': token, 'password': 'second-password-2'})
    assert r.status_code == 200, r.get_json()
    assert client.post('/api/password/reset', json={'token': token, 'password': 'third-password-3'}).status_code == 400
    assert client.post('/api/login', json={'email': email, 'password': PASSWORD}).status_code == 401
    assert client.post('/api/login', json={'email': email, 'password': 'second-password-2'}).status_code == 200
    assert db.execute('SELECT email_confirmed_at FROM users WHERE user_id = %s', [uuid.UUID(uid)]).one().email_confirmed_at
    assert 'changed' in mail.to(email)[-1]['subject']


def test_an_older_link_dies_with_a_new_password(joined, mail):
    client, email, _, _ = joined
    for _ in range(2):
        client.post('/api/password/forgot', json={'email': email})
    older, newer = [token_in(m, 'reset-password') for m in mail.to(email)]
    assert client.post('/api/password/reset', json={'token': newer, 'password': 'second-password-2'}).status_code == 200
    assert client.post('/api/password/reset', json={'token': older, 'password': 'third-password-3'}).status_code == 400


def test_personas_get_no_mail(app, mail):
    r = app.test_client().post('/api/password/forgot', json={'email': 'marie.konda@example.com'})
    assert r.status_code == 200 and mail.sent == []


def test_asking_again_and_again_is_capped(joined, mail):
    client, email, _, _ = joined        # (joining took one of the three)
    answers = {client.post('/api/password/forgot', json={'email': email}).status_code for _ in range(5)}
    assert answers == {200} and len(mail.to(email)) == 2


def test_one_connection_cant_ask_endlessly(app, mail, monkeypatch):
    from app.routes import email as routes
    monkeypatch.setattr(routes, 'ASKS_PER_NETWORK_HOUR', 2)
    client = app.test_client()
    ask = lambda ip: client.post('/api/password/forgot', json={'email': 'none@example.com'},
                                 headers={'X-Real-IP': ip}).status_code
    assert [ask('203.0.113.7'), ask('203.0.113.7'), ask('203.0.113.7'), ask('203.0.113.8')] == [200, 200, 429, 200]
    assert mailer.network('2001:db8:1:2:aaaa::1') == mailer.network('2001:db8:1:2:bbbb::9')


# -- Notifications by email -----------------------------------------------------
def test_notifications_are_opt_in_and_stop_with_one_press(app, db, api, joined, mail):
    client, email, uid, hdr = joined
    tell = lambda **kw: Notification.create(**{**dict(
        user_id=uid, actor_id=None, actor_name='A neighbour', type_='receipt_received',
        message='A neighbour left you a receipt', link='/exchange?id=x1'), **kw})

    tell()
    assert mail.sent == []          # off until chosen
    assert client.post('/api/account/email', headers=hdr, json={'topics': ['everything']}).status_code == 400
    r = client.post('/api/account/email', headers=hdr, json={'topics': ['exchanges']})
    assert r.status_code == 200 and r.get_json()['topics'] == ['exchanges'] and r.get_json()['confirmation_sent'] is False

    tell(type_='new_follower', message='A neighbour started following you')
    assert mail.sent == []          # another topic
    tell(actor_id=api.uid('marie'))
    assert mail.sent == []          # a persona, and they didn't ask for those
    tell(message='Evil <b>bold</b> left you a receipt, see https://bad.invalid/x or bad.example/claim')
    message, = mail.to(email)
    assert f'{SITE}/exchange?id=x1' in message['text'] and '/claim' not in message['text']
    assert 'bad.invalid' not in message['text'] + message['html'] and '<b>' not in message['html']
    assert message['subject'] == 'You were left a receipt'
    assert message['h:List-Unsubscribe-Post'] == 'List-Unsubscribe=One-Click'

    stop = re.fullmatch(f'<{re.escape(SITE)}(/api/email/unsubscribe/[0-9a-f.]+)>', message['h:List-Unsubscribe']).group(1)
    mailbox = app.test_client()
    assert mailbox.get(stop).status_code == 302
    assert client.get('/api/account/email', headers=hdr).get_json()['topics'] == ['exchanges']     # looking changes nothing
    assert mailbox.post(stop[:-1] + ('0' if stop[-1] != '0' else '1')).status_code == 400
    assert mailbox.post(stop, data={'List-Unsubscribe': 'One-Click'}, content_type='multipart/form-data').status_code == 200
    assert client.get('/api/account/email', headers=hdr).get_json()['topics'] == []
    tell()
    assert len(mail.sent) == 1


def test_nothing_goes_to_an_unconfirmed_address(app, db, joined, mail):
    client, email, uid, hdr = joined
    db.execute('UPDATE users SET email_confirmed_at = null WHERE user_id = %s', [uuid.UUID(uid)])
    r = client.post('/api/account/email', headers=hdr, json={'topics': ['exchanges']})
    assert r.get_json()['confirmation_sent'] is True and r.get_json()['confirmed'] is False
    token = token_in(mail.to(email)[0], 'confirm-email')
    mail.sent.clear()
    Notification.create(user_id=uid, actor_id=None, actor_name='A', type_='receipt_received', message='A receipt', link='/')
    assert mail.sent == []
    assert app.test_client().post('/api/email/confirm', json={'token': token}).status_code == 200
    assert app.test_client().post('/api/email/confirm', json={'token': token}).status_code == 400
    Notification.create(user_id=uid, actor_id=None, actor_name='A', type_='receipt_received', message='A receipt', link='/')
    assert len(mail.to(email)) == 1


def test_every_kind_of_notification_is_decided():
    routes = Path(__file__).resolve().parents[1] / 'routes'
    made = {kind for f in routes.glob('*.py') for kind in re.findall(r"type_='(\w+)'", f.read_text(encoding='utf-8'))}
    from app.routes.demo import INVITE_TYPE
    made.add(INVITE_TYPE)
    assert made <= set(email_news.KINDS), f'decide whether these are emailed: {made - set(email_news.KINDS)}'
    assert all(value is None or value[0] in email_news.KEYS for value in email_news.KINDS.values())


def test_export_says_what_is_emailed(joined):
    client, _, _, hdr = joined
    profile = client.get('/api/account/export', headers=hdr).get_json(force=True)['profile']
    assert profile['email_confirmed'] is True and profile['email_notifications'] == []


# -- The mailer itself -----------------------------------------------------------
def test_one_address_and_no_tricks(monkeypatch):
    assert mailer.deliverable('sam.field+garden@mail.somewhere.io')
    for bad in ('a@b.io,c@d.io', 'victim,@b.io', 'a b@c.io', '<a@b.io>', 'a@b', 'a@-b.io', 'jo.rodan@example.com',
                'x@sub.example.org', 'x@thing.test', 'a..b@c.io', 'a@b.io\nBcc: c@d.io', '', None, 'ä@b.io'):
        assert not mailer.deliverable(bad), bad


def test_retries_what_may_pass_and_not_what_wont(mail):
    letter = mails.letter('Hello', ['Words'])
    mail.statuses = [429, 500]
    assert mailer.send('a@example.com', letter, 'test') is True and mail.calls == 3
    mail.statuses, mail.calls = [401], 0
    assert mailer.send('a@example.com', letter, 'test') is False and mail.calls == 1


def test_the_key_only_goes_to_mailgun(mail, monkeypatch):
    monkeypatch.setenv('MAILGUN_BASE', 'https://api.mailgun.net.evil.invalid')
    assert not mailer.enabled()
    monkeypatch.setenv('MAILGUN_BASE', 'https://api.eu.mailgun.net')
    assert mailer.enabled()
    monkeypatch.setenv('MAIL', 'off')
    assert not mailer.enabled()


def test_off_means_the_old_way(app, monkeypatch, tmp_path):
    monkeypatch.setenv('MAIL_ENV_FILE', str(tmp_path / 'none.env'))
    client = app.test_client()
    assert client.get('/api/mail').get_json() == {'on': False}
    assert client.post('/api/password/forgot', json={'email': 'someone@example.com'}).status_code == 503
