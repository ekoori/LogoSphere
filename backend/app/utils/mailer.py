"""Sending email, through Mailgun's HTTP API.

Off until there is a key and a domain. Settings come from the environment, else
from MAIL_ENV_FILE (default backend/mail.env, chmod 600, never in git):

  MAILGUN_API_KEY   a sending key for the domain
  MAILGUN_DOMAIN    the verified sending domain
  MAILGUN_BASE      https://api.mailgun.net (the default) or the EU's
  MAIL_FROM         LogoSphere <no-reply@DOMAIN> (the default)
  SITE_URL          where links lead. Never taken from a request's Host.
  MAIL=off          switches email off whatever else is set
  MAIL_TEST_MODE    yes: Mailgun accepts messages and delivers none

Never to AI personas' or other reserved addresses, never tracked (a tracked
link would pass a password-reset token through Mailgun's redirector), and
never logged: not the address, not the words.
"""
import hashlib
import hmac
import ipaddress
import logging
import os
import re
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.db import session

log = logging.getLogger(__name__)

SETTINGS = ('MAILGUN_API_KEY', 'MAILGUN_DOMAIN', 'MAILGUN_BASE', 'MAIL_FROM', 'SITE_URL', 'MAIL', 'MAIL_TEST_MODE')
# The key goes to these and nowhere else.
BASES = ('https://api.mailgun.net', 'https://api.eu.mailgun.net')
DEFAULT_SITE = 'https://ts.krbavcic.com'
# No mailbox can be there: the personas and test accounts live at example.com.
RESERVED = ('example.com', 'example.net', 'example.org', 'example', 'test', 'invalid', 'localhost', 'local')
HOUR, DAY = 3600, 86400
TRY_AGAIN = (420, 429, 500, 502, 503, 504)      # Mailgun also says 420 for "too fast"
RETRY_WAITS = (2, 6)

COUNTS_DDL = ('CREATE TABLE IF NOT EXISTS mail_counts ('
              'bucket text, sent_at timeuuid, PRIMARY KEY (bucket, sent_at)) '
              'WITH default_time_to_live = 86400')

_DOMAIN = re.compile(r'(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z][a-z0-9-]*[a-z0-9]')
# Stricter than sign-in's shape check: the API reads commas as more recipients.
_LOCAL = re.compile(r"[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*")

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='mail')


def ensure_tables():
    session.execute(COUNTS_DDL)


def _settings():
    found = {}
    path = Path(os.environ.get('MAIL_ENV_FILE') or Path(__file__).resolve().parents[2] / 'mail.env')
    try:
        for line in path.read_text(encoding='utf-8').splitlines():
            name, eq, value = line.strip().partition('=')
            if eq and name in SETTINGS:
                found[name] = value.strip().strip('"\'')
    except OSError:
        pass
    found.update({name: os.environ[name] for name in SETTINGS if os.environ.get(name)})
    return found


def _usable(settings):
    if settings.get('MAIL', '').strip().lower() in ('off', 'false', '0', 'no'):
        return False
    return bool(settings.get('MAILGUN_API_KEY')
                and _DOMAIN.fullmatch(settings.get('MAILGUN_DOMAIN', ''))
                and settings.get('MAILGUN_BASE', BASES[0]).rstrip('/') in BASES)


def enabled():
    return _usable(_settings())


def site(path='/'):
    return _settings().get('SITE_URL', DEFAULT_SITE).rstrip('/') + path


def deliverable(address):
    """One ordinary address that could have a mailbox."""
    if not isinstance(address, str) or len(address) > 254:
        return False
    local, at, domain = address.strip().lower().rpartition('@')
    if not at or len(local) > 64 or not _LOCAL.fullmatch(local) or not _DOMAIN.fullmatch(domain):
        return False
    return not any(domain == bad or domain.endswith('.' + bad) for bad in RESERVED)


def queue(job, *args):
    """Runs after the request: slow mail never holds one up, and how long an
    answer takes doesn't tell whether an address has an account."""
    _pool.submit(_quietly, job, *args)


def _quietly(job, *args):
    try:
        job(*args)
    except Exception as e:  # noqa: BLE001 - only the kind: the text could hold an address
        log.warning('Email job %s failed: %s', getattr(job, '__name__', '?'), type(e).__name__)


def send(to, letter, tag, headers=None):
    """One letter to one address; True once Mailgun has it. Call it from a queued job."""
    settings = _settings()
    if not _usable(settings) or not deliverable(to):
        return False
    domain = settings['MAILGUN_DOMAIN']
    fields = [
        ('from', settings.get('MAIL_FROM') or f'LogoSphere <no-reply@{domain}>'),
        ('to', to.strip()),
        ('subject', ' '.join(letter.subject.split())),
        ('text', letter.text),
        ('html', letter.html),
        ('o:tag', tag),
        ('o:tracking', 'no'),
        ('o:tracking-clicks', 'no'),
        ('o:tracking-opens', 'no'),
        ('o:require-tls', 'yes'),
    ]
    if settings.get('MAIL_TEST_MODE', '').strip().lower() == 'yes':
        fields.append(('o:testmode', 'yes'))
    fields += [(f'h:{name}', value) for name, value in (headers or {}).items()]
    url = f"{settings.get('MAILGUN_BASE', BASES[0]).rstrip('/')}/v3/{domain}/messages"
    status = None
    for wait in (0, *RETRY_WAITS):
        if wait:
            time.sleep(wait)
        try:
            status = _post(url, settings['MAILGUN_API_KEY'], fields)
        except Exception as e:  # noqa: BLE001
            status = type(e).__name__
            continue
        if status == 200:
            return True
        if status not in TRY_AGAIN:
            break
    log.warning('Email (%s) was not sent: %s', tag, status)
    return False


def _post(url, key, fields):
    import urllib3
    response = urllib3.PoolManager().request(
        'POST', url, fields=fields, headers=urllib3.make_headers(basic_auth=f'api:{key}'),
        timeout=10.0, retries=False)
    return response.status


# -- How much ----------------------------------------------------------------
def signed(text):
    secret = os.environ.get('SECRET_KEY') or 'dev-secret-change-me'
    return hmac.new(secret.encode(), text.encode(), hashlib.sha256).hexdigest()


def _bucket(name):
    """Keyed, so the table holds no address, member or IP."""
    return signed(f'count:{name}')[:40]


def take(name, most, seconds=DAY):
    """Counts one against `name`'s allowance; False when that is used up."""
    key = _bucket(name)
    if session.execute('SELECT count(*) AS n FROM mail_counts WHERE bucket = %s', [key]).one().n >= most:
        return False
    session.execute(f'INSERT INTO mail_counts (bucket, sent_at) VALUES (%s, now()) USING TTL {int(seconds)}', [key])
    return True


def network(address):
    """Who is asking, for limits: an IPv4 address, or an IPv6 /64 (a household gets that many)."""
    try:
        ip = ipaddress.ip_address((address or '').strip())
    except ValueError:
        return 'unknown'
    return str(ipaddress.ip_network(f'{ip}/64', strict=False)) if ip.version == 6 else str(ip)
