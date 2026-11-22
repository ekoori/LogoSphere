"""Email (app/utils/mailer, email_accounts, email_news):

  GET  /api/mail                       whether LogoSphere can send email
  POST /api/register/confirm           finish joining: the link and a password
  POST /api/password/forgot            a reset link, by email
  POST /api/email/confirm              confirm an address with its link
  GET  /api/account/email              your email settings
  POST /api/account/email              which notifications are emailed
  POST /api/account/email/confirm      send yourself the confirmation again
  POST /api/email/unsubscribe/<token>  stop notification emails, signed out too

Joining itself starts at POST /api/register (app/routes/registration.py).
"""
from flask import current_app as app, jsonify, redirect, request

from app.middleware.session_middleware import validate_session
from app.models.user import normalize_email
from app.routes.invites import arrived
from app.routes.registration import welcome
from app.utils import email_accounts, email_news, groups, invites, mailer
from app.utils.accounts import MIN_PASSWORD_LEN

ASKS_PER_NETWORK_HOUR = 30      # a hall of people joining together share one
NOT_YET = "LogoSphere can't send email yet. Ask a platform administrator for a password reset link."


def _options():
    return app.make_default_options_response(), 200


def _body():
    data = request.get_json(silent=True)
    return data if isinstance(data, dict) else {}


def _said(value):
    return value if isinstance(value, str) else ''


def too_many_asks():
    # nginx sets X-Real-IP itself and the backend listens only locally.
    who = mailer.network(request.headers.get('X-Real-IP') or request.remote_addr)
    if mailer.take(f'asks:{who}', ASKS_PER_NETWORK_HOUR, mailer.HOUR):
        return None
    return jsonify({'message': 'Too many tries from this connection. Please wait an hour.'}), 429


def begin_sign_up(data):
    """POST /api/register while email works. The answer never tells who has an account."""
    name = ' '.join(_said(data.get('name')).split())
    email = normalize_email(_said(data.get('email')))
    if not name:
        return jsonify({'message': 'Please enter your name.'}), 400
    if len(name) > email_accounts.NAME_MAX:
        return jsonify({'message': f'Keep the name under {email_accounts.NAME_MAX} characters.'}), 400
    if not mailer.deliverable(email):
        return jsonify({'message': 'Please enter an email address we can write to.'}), 400
    refused = too_many_asks()
    if refused:
        return refused
    mailer.queue(email_accounts.send_sign_up, email, name, invites.hashed(data.get('invite')))
    return jsonify({'reg_success': True, 'confirm_email': True,
                    'message': 'Check your email: there is a link to finish joining.'}), 200


def mail_status():
    return jsonify({'on': mailer.enabled()}), 200


def finish_sign_up():
    if request.method == 'OPTIONS':
        return _options()
    data = _body()
    password = _said(data.get('password'))
    if len(password) < MIN_PASSWORD_LEN:
        return jsonify({'message': f'A password needs at least {MIN_PASSWORD_LEN} characters.'}), 400
    user, why, invite = email_accounts.finish_sign_up(data.get('token'), password)
    if why == 'taken':
        return jsonify({'message': 'There is an account with this email already. Log in with it.'}), 400
    if why:
        return jsonify({'message': 'This link has expired or was already used. Sign up again for a new one.'}), 400
    welcome(user.user_id)
    joined = arrived(invite, user.user_id)
    return jsonify({'reg_success': True, 'user_id': str(user.user_id), 'email': user.email,
                    'invited_to': groups.summary(joined[1]) if joined else None,
                    'message': 'Your account is ready.'}), 200


def forgot_password():
    if request.method == 'OPTIONS':
        return _options()
    if not mailer.enabled():
        return jsonify({'message': NOT_YET}), 503
    email = normalize_email(_said(_body().get('email')))
    if '@' not in email or len(email) > 254:
        return jsonify({'message': 'Please enter your email address.'}), 400
    refused = too_many_asks()
    if refused:
        return refused
    mailer.queue(email_accounts.send_reset, email)
    return jsonify({'message': 'If that address has an account, a link is on its way. '
                               'It can take a few minutes: look in spam too.'}), 200


def confirm_email():
    if request.method == 'OPTIONS':
        return _options()
    if not email_accounts.confirm(_body().get('token')):
        return jsonify({'message': 'This link has expired or was already used. Send a new one from Settings.'}), 400
    return jsonify({'message': 'Your email is confirmed.'}), 200


@validate_session
def email_settings(user_id=None):
    found = email_news.settings_of(user_id)
    return (jsonify(found), 200) if found else (jsonify({'message': 'User not found'}), 404)


@validate_session
def choose_topics(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    topics = _body().get('topics')
    if not isinstance(topics, list) or any(t not in email_news.KEYS for t in topics):
        return jsonify({'message': 'Choose from the topics offered.'}), 400
    before = email_news.settings_of(user_id)
    if not before:
        return jsonify({'message': 'User not found'}), 404
    email_news.choose(user_id, topics)
    # First switched on: the address has to be confirmed before anything is sent.
    asking = bool(topics and not before['topics'] and before['on'] and before['can_receive'] and not before['confirmed'])
    if asking:
        mailer.queue(email_accounts.send_confirmation, user_id)
    return jsonify({**email_news.settings_of(user_id), 'confirmation_sent': asking}), 200


@validate_session
def send_confirmation(user_id=None):
    if request.method == 'OPTIONS':
        return _options()
    found = email_news.settings_of(user_id)
    if not found:
        return jsonify({'message': 'User not found'}), 404
    if found['confirmed']:
        return jsonify({'message': 'Your email is confirmed already.'}), 200
    if not found['on']:
        return jsonify({'message': "LogoSphere can't send email yet."}), 503
    if not found['can_receive']:
        return jsonify({'message': "This account's address can't receive email."}), 400
    mailer.queue(email_accounts.send_confirmation, user_id)
    return jsonify({'message': 'A link is on its way. Look in spam too.'}), 200


def unsubscribe(token):
    if request.method == 'OPTIONS':
        return _options()
    if request.method == 'GET':
        # A person following the header's link. Nothing changes until they press.
        return redirect(f'/unsubscribe#{token}')
    if not email_news.stop(token):
        return jsonify({'message': "That link isn't one of ours."}), 400
    return jsonify({'message': 'Done. LogoSphere will not email you notifications.'}), 200


def register(app_):
    mailer.ensure_tables()
    email_accounts.ensure_tables()
    email_news.ensure_tables()
    app_.add_url_rule('/api/mail', view_func=mail_status, methods=['GET'])
    app_.add_url_rule('/api/register/confirm', view_func=finish_sign_up, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/password/forgot', view_func=forgot_password, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/email/confirm', view_func=confirm_email, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/account/email', view_func=email_settings, methods=['GET'])
    app_.add_url_rule('/api/account/email', view_func=choose_topics, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/account/email/confirm', view_func=send_confirmation, methods=['POST', 'OPTIONS'])
    app_.add_url_rule('/api/email/unsubscribe/<token>', view_func=unsubscribe, methods=['GET', 'POST', 'OPTIONS'])
