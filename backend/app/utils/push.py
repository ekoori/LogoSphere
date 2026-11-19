"""Push notifications to members' phones, through Firebase Cloud Messaging.

Every in-app notification (app/models/notification.Notification.create) is
also pushed to the phones its member is signed in on. The Android app
registers its FCM token at sign-in (POST /api/push/devices) and forgets it at
sign-out; a registration belongs to the session it was made in, so a phone
whose session has ended (expired, revoked, signed out elsewhere) gets nothing
more. Tokens Firebase no longer knows are dropped as they fail.

Sending runs on a small background pool, never inside the request that caused
the notification, and a failure never reaches that request.

Settings: FCM_CREDENTIALS - path to the Firebase project's service-account key
(JSON, chmod 600). Without it devices still register, and nothing is sent.
"""
import json
import logging
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime

from app.db import session as db

log = logging.getLogger(__name__)

SCOPE = 'https://www.googleapis.com/auth/firebase.messaging'
CHANNEL = 'activity'            # the Android app's notification channel
PLATFORMS = ('android',)

_pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix='push')
_http = None                    # (google-auth AuthorizedHttp, project id), made on first send
_http_lock = threading.Lock()


def ensure_tables():
    """push_devices: a member's phones; push_token_owner: whose a phone is,
    so a phone that changes hands stops getting the last member's news."""
    db.execute("""
        CREATE TABLE IF NOT EXISTS push_devices (
            user_id uuid, token text, platform text, session_id uuid, added_at timestamp,
            PRIMARY KEY (user_id, token))""")
    db.execute("""
        CREATE TABLE IF NOT EXISTS push_token_owner (token text PRIMARY KEY, user_id uuid)""")


def enabled():
    return bool(os.environ.get('FCM_CREDENTIALS'))


# ── Devices ─────────────────────────────────────────────────────────────────
def register(user_id, token, session_id, platform='android'):
    """This phone gets `user_id`'s notifications while `session_id` lasts -
    and no longer anyone else's."""
    uid = uuid.UUID(str(user_id))
    owner = db.execute('SELECT user_id FROM push_token_owner WHERE token = %s', [token]).one()
    if owner and owner.user_id != uid:
        db.execute('DELETE FROM push_devices WHERE user_id = %s AND token = %s', [owner.user_id, token])
    db.execute('INSERT INTO push_devices (user_id, token, platform, session_id, added_at) VALUES (%s, %s, %s, %s, %s)',
               [uid, token, platform, uuid.UUID(str(session_id)) if session_id else None, datetime.utcnow()])
    db.execute('INSERT INTO push_token_owner (token, user_id) VALUES (%s, %s)', [token, uid])


def forget(user_id, token):
    uid = uuid.UUID(str(user_id))
    db.execute('DELETE FROM push_devices WHERE user_id = %s AND token = %s', [uid, token])
    owner = db.execute('SELECT user_id FROM push_token_owner WHERE token = %s', [token]).one()
    if owner and owner.user_id == uid:
        db.execute('DELETE FROM push_token_owner WHERE token = %s', [token])


def devices(user_id):
    """[(token, session_id)] of the member's phones."""
    rows = db.execute('SELECT token, session_id FROM push_devices WHERE user_id = %s', [uuid.UUID(str(user_id))])
    return [(r.token, r.session_id) for r in rows]


def _session_lives(session_id):
    if session_id is None:
        return False
    row = db.execute('SELECT expire_at FROM sessions WHERE session_id = %s', [session_id]).one()
    return bool(row and row.expire_at and row.expire_at > datetime.utcnow())


# ── Sending ─────────────────────────────────────────────────────────────────
def notify(user_id, message, link=None, kind=None, notification_id=None):
    """Push one notification to the member's phones, in the background."""
    if not enabled() or not message:
        return
    try:
        phones = devices(user_id)
    except Exception as e:  # noqa: BLE001 - a missed push must never break the action
        log.warning('Push: could not read the devices of %s: %s', user_id, e)
        return
    if phones:
        _pool.submit(_send_all, user_id, phones, message, link, kind, notification_id)


def message_for(token, message, link=None, kind=None, notification_id=None):
    """The FCM v1 message: shown by the system while the app is in the
    background (on the app's channel), handed to the app in the foreground;
    `data.link` is the web path the app opens when it's tapped."""
    data = {'link': link or '', 'type': kind or '', 'notification_id': str(notification_id or '')}
    return {'message': {
        'token': token,
        'notification': {'title': 'LogoSphere', 'body': message},
        'data': data,
        'android': {'priority': 'high', 'notification': {'channel_id': CHANNEL}},
    }}


def _send_all(user_id, phones, message, link, kind, notification_id):
    for token, session_id in phones:
        try:
            if not _session_lives(session_id):
                forget(user_id, token)
                continue
            status, text = _post(message_for(token, message, link, kind, notification_id))
            if status == 404 or (status == 400 and 'registration token' in text.lower()):
                forget(user_id, token)          # uninstalled, or the token was replaced
            elif status >= 300:
                log.warning('Push to a phone of %s refused (%s): %s', user_id, status, text[:300])
        except Exception as e:  # noqa: BLE001
            log.warning('Push to a phone of %s failed: %s', user_id, e)


def _post(body):
    """POST one message to FCM; (status, response text)."""
    http, project = _client()
    resp = http.request('POST', f'https://fcm.googleapis.com/v1/projects/{project}/messages:send',
                        body=json.dumps(body).encode(), headers={'Content-Type': 'application/json'},
                        timeout=10.0)
    return resp.status, resp.data.decode('utf-8', 'replace')


def _client():
    global _http
    if _http is None:
        with _http_lock:
            if _http is None:
                import urllib3
                from google.auth.transport.urllib3 import AuthorizedHttp
                from google.oauth2 import service_account
                creds = service_account.Credentials.from_service_account_file(
                    os.environ['FCM_CREDENTIALS'], scopes=[SCOPE])
                _http = (AuthorizedHttp(creds, http=urllib3.PoolManager()), creds.project_id)
    return _http
