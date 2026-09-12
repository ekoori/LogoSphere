# File: ./backend/app/main.py
# Description: This file is the main entry point of the backend Flask application. It sets up and configures the Flask app, initializes LoginManager,
#              configures CORS, defines route handlers, sets up error handling, and starts the server.
# Classes: None
# Properties: None
# Methods: 
#    [+] load_user(user_id): Fetches the user with the given user_id from the User model, used by Flask-Login to manage user sessions.
#    [+] login(): Handles the POST request for user login, invokes the login() method from the User model, and starts a new user session.
#    [+] logout(): Handles the POST request for user logout, invokes the logout() method from the User model, and ends the current user session.
#    [+] check_session(): Checks the validity of a session.
#    [+] get_user(): Handles the GET request to fetch user profile details, it calls the get() method from the User model.
#    [+] register(): Handles the POST request for new user registration, it calls the register() method from the User model.
#    [+] internal_error(error): Custom error handler for 500 Internal Server Error.
#    [x] app.run(): The application is not currently configured to run inside a WSGI container. It can be started using this method in a development environment.

from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_login import LoginManager
import logging
import os
from datetime import timedelta

# Configured before any app module is imported: app.db opens the Cassandra
# connection at import time and logs it, and without a root handler yet in
# place Python's last-resort handler would drop everything below WARNING.
# Logging: INFO by default (DEBUG used to be the default, which also logged
# request bodies and bearer tokens). Override with LOG_LEVEL=DEBUG locally.
logging.basicConfig(level=getattr(logging, os.environ.get('LOG_LEVEL', 'INFO').upper(), logging.INFO))
# The driver is very chatty at DEBUG; keep it at WARNING unless asked for.
logging.getLogger('cassandra').setLevel(os.environ.get('CASSANDRA_LOG_LEVEL', 'WARNING').upper())
logger = logging.getLogger(__name__)

from app.routes.cassandra import CassandraSessionInterface
from app.routes.login import login, logout, check_session
from app.routes.profile import get_user, get_profile, update_user, get_public_user, get_user_avatar, toggle_follow, get_following
from app.routes.registration import register
from app.routes.meaning_trail import get_meaning_trail, get_meaning_trail_by_project, add_exchange, get_exchange, update_xc_status, add_xc_comment, like_exchange, edit_exchange, get_exchange_image, upload_receipt_photos, get_receipt_photo
from app.models.user import User
from app.routes.spheres import create_sphere, get_spheres, update_sphere_governance, get_public_sphere
from app.routes import entities as entity_routes
from app.routes import governance as governance_routes
from app.models.governance import ensure_tables as ensure_governance_tables
from app.routes.alliances import create_alliance, get_alliances
from app.routes.projects import create_project, get_projects
from app.routes.openings import create_service, get_services, get_service, accept_service, confirm_service, reject_service, like_service, update_service_image, get_service_image, edit_opening, cancel_service
from app.routes import admin as admin_routes
from app.routes.search import search, search_vicinity
from app.routes.value_cards import get_value_cards, create_value_card, edit_value_card, delete_value_card, create_entity_value_card, edit_entity_value_card, delete_entity_value_card, clone_value_card, endorse_value_card, review_value_card, endorse_entity_value_card, review_entity_value_card
from app.routes.notifications import get_notifications, mark_notification_read, mark_all_notifications_read

app = Flask(__name__)
# The secret key must come from the environment. A dev fallback is only allowed
# when the app is explicitly not in production, so a misconfigured deploy fails
# loudly instead of signing sessions with a public string.
_secret = os.environ.get('SECRET_KEY')
if not _secret:
    if os.environ.get('LOGOSPHERE_ENV', 'development') == 'production' or             os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true':
        raise RuntimeError('SECRET_KEY must be set in production')
    logger.warning('SECRET_KEY not set - using an insecure development default')
    _secret = 'dev-secret-change-me'
app.config['SECRET_KEY'] = _secret
app.config['SESSION_COOKIE_NAME'] = 'session_id'


app.config.update(
    # Enable secure cookies in production by setting SESSION_COOKIE_SECURE=true
    # (requires HTTPS). Defaults to False for local HTTP development.
    SESSION_COOKIE_SECURE=os.environ.get('SESSION_COOKIE_SECURE', 'false').lower() == 'true',
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_NAME='session_id',
    PERMANENT_SESSION_LIFETIME=timedelta(days=30)
)



# Initialize session interface
session_interface = CassandraSessionInterface(session_lifetime=timedelta(days=30))
app.session_interface = session_interface   


# CORS - one source of truth. In production the SPA is served same-origin by
# nginx (so CORS never applies); in development CRA proxies /api, so this only
# matters for non-proxied clients. Origins come from CORS_ORIGINS (comma-sep).
# `Authorization` (standard `Bearer <session_id>`) is the documented API auth
# header; the browser SPA relies on the httpOnly session cookie instead.
CORS_ORIGINS = [o.strip() for o in os.environ.get('CORS_ORIGINS', 'http://localhost:3000').split(',') if o.strip()]
CORS(app, resources={r"/api/*": {
    "origins": CORS_ORIGINS,
    "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
    "expose_headers": ["Content-Type", "Authorization"],
    "supports_credentials": True,
    "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    "max_age": 3600,
}})


login_manager = LoginManager()
login_manager.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    logging.info(f'Loading user with user_id: {user_id}')
    return User.get(user_id)

# Route definitions
app.add_url_rule('/api/login', view_func=login, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/logout', view_func=logout, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/check_session', view_func=check_session, methods=['POST', 'GET', 'OPTIONS'])
app.add_url_rule('/api/user', view_func=get_user, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/user/profile', view_func=get_profile, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/users/<target_id>', view_func=get_public_user, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/users/<target_id>/avatar', view_func=get_user_avatar, methods=['GET'])
app.add_url_rule('/api/users/<target_id>/follow', view_func=toggle_follow, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/following', view_func=get_following, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/updateuser', view_func=update_user, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/register', view_func=register, methods=['POST'])
app.add_url_rule('/api/meaning_trail', view_func=get_meaning_trail, methods=['GET', 'POST', 'OPTIONS'])
app.add_url_rule('/api/meaning_trail/add_exchange', view_func=add_exchange, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/meaning_trail/by_project/<project_id>', view_func=get_meaning_trail_by_project, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/exchange/<exchange_id>', view_func=get_exchange, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/exchange/<exchange_id>/status', view_func=update_xc_status, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/exchange/<exchange_id>/comment', view_func=add_xc_comment, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/exchange/<exchange_id>/like', view_func=like_exchange, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/exchange/<exchange_id>/edit', view_func=edit_exchange, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/exchange/<exchange_id>/image', view_func=get_exchange_image, methods=['GET'])
app.add_url_rule('/api/exchange/<exchange_id>/receipt_photos', view_func=upload_receipt_photos, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/exchange/<exchange_id>/receipt_photo/<idx>', view_func=get_receipt_photo, methods=['GET'])
app.add_url_rule('/api/spheres', view_func=create_sphere, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/spheres', view_func=get_spheres, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/spheres/<sphere_id>/governance', view_func=update_sphere_governance, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/public/spheres/<sphere_id>', view_func=get_public_sphere, methods=['GET'])
app.add_url_rule('/api/alliances', view_func=create_alliance, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/alliances', view_func=get_alliances, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/projects', view_func=create_project, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/projects', view_func=get_projects, methods=['GET', 'OPTIONS'])
# Detail / edit / join / roles / banner for spheres, alliances and projects.
entity_routes.register(app)
# Liquid democracy: proposals, votes, delegation - for every entity kind.
governance_routes.register(app)
ensure_governance_tables()
app.add_url_rule('/api/openings', view_func=create_service, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings', view_func=get_services, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>', view_func=get_service, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>', view_func=edit_opening, methods=['PATCH'])
app.add_url_rule('/api/openings/<service_id>/accept', view_func=accept_service, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>/confirm', view_func=confirm_service, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>/reject', view_func=reject_service, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>/cancel', view_func=cancel_service, methods=['POST', 'OPTIONS'])
# Platform administration (platform admins only) and search.
admin_routes.register(app)
app.add_url_rule('/api/search', view_func=search, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/search/vicinity', view_func=search_vicinity, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>/like', view_func=like_service, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>/image', view_func=update_service_image, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>/image', view_func=get_service_image, methods=['GET'])
app.add_url_rule('/api/value_cards/clone', view_func=clone_value_card, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/value_cards/<target_user_id>', view_func=get_value_cards, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/value_cards', view_func=create_value_card, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/value_cards/<card_id>', view_func=delete_value_card, methods=['DELETE', 'OPTIONS'])
app.add_url_rule('/api/value_cards/<card_id>', view_func=edit_value_card, methods=['PATCH', 'OPTIONS'])
app.add_url_rule('/api/value_cards/<card_id>/endorse', view_func=endorse_value_card, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/value_cards/<card_id>/review', view_func=review_value_card, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/entity_value_cards/<entity_id>', view_func=create_entity_value_card, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/notifications', view_func=get_notifications, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/notifications/read', view_func=mark_notification_read, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/notifications/read_all', view_func=mark_all_notifications_read, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/entity_value_cards/<entity_id>/<card_id>', view_func=delete_entity_value_card, methods=['DELETE', 'OPTIONS'])
app.add_url_rule('/api/entity_value_cards/<entity_id>/<card_id>', view_func=edit_entity_value_card, methods=['PATCH', 'OPTIONS'])
app.add_url_rule('/api/entity_value_cards/<entity_id>/<card_id>/endorse', view_func=endorse_entity_value_card, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/entity_value_cards/<entity_id>/<card_id>/review', view_func=review_entity_value_card, methods=['POST', 'OPTIONS'])

# Uniform JSON error envelope: every error the API emits is {"message": ...}.
@app.errorhandler(404)
def not_found(error):
    if request.path.startswith('/api/'):
        return jsonify({'message': 'Not found'}), 404
    return error, 404


@app.errorhandler(405)
def method_not_allowed(error):
    return jsonify({'message': 'Method not allowed'}), 405


@app.errorhandler(500)
def internal_error(error):
    logger.exception('Unhandled error')
    return jsonify({'message': 'Internal server error'}), 500


if __name__ == '__main__':
    # Development only - production runs under gunicorn (see run_local.py).
    app.run(debug=os.environ.get('FLASK_DEBUG', 'false').lower() == 'true', host='0.0.0.0')
