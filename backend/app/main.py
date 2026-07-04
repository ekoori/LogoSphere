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

from app.routes.cassandra import CassandraSessionInterface
from app.routes.login import login, logout, check_session
from app.routes.profile import get_user, get_profile, update_user, get_public_user, get_user_avatar, toggle_follow, get_following
from app.routes.registration import register
from app.routes.meaning_trail import get_meaning_trail, get_meaning_trail_by_project, add_exchange, get_exchange, update_xc_status, add_xc_comment, like_exchange, edit_exchange, get_exchange_image, upload_receipt_photos, get_receipt_photo
from app.models.user import User
from app.routes.spheres import create_sphere, get_spheres, join_sphere, update_sphere_image, set_sphere_role
from app.routes.alliances import create_alliance, get_alliances, join_alliance, update_alliance_image, set_alliance_role
from app.routes.projects import create_project, get_projects, join_project, update_project_image, set_project_role
from app.routes.openings import create_service, get_services, get_service, accept_service, confirm_service, reject_service, like_service, update_service_image
from app.routes.value_cards import get_value_cards, create_value_card, delete_value_card, create_entity_value_card, delete_entity_value_card, clone_value_card
from app.routes.notifications import get_notifications, mark_notification_read, mark_all_notifications_read

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

print("Python path:")
import sys
for path in sys.path:
    print(path)

app = Flask(__name__)
# Secret key must come from the environment in production; the fallback is for
# local development only and should never be used with real sessions.
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev-secret-change-me')
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
session_interface = CassandraSessionInterface(
    cluster_nodes=os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(','),
    keyspace='logosphere',
    session_lifetime=timedelta(days=30)
)
app.session_interface = session_interface   


# Enable CORS for all routes before defining any routes.
# `Authorization` (standard `Bearer <session_id>`) is the documented header for
# API auth; the browser SPA instead relies on the httpOnly session cookie sent
# automatically via credentials. There's no other custom auth header — a
# non-standard header carrying a bearer credential is itself a smell (tooling,
# proxies, and log redaction all expect `Authorization`).
CORS(app, resources={r"/api/*": {
    "origins": ["http://localhost:3000"],
    "allow_headers": ["Content-Type", "Authorization", "X-Requested-With"],
    "expose_headers": ["Content-Type", "Authorization"],
    "supports_credentials": True,
    "allow_credentials": True,
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
}})


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers.add('Access-Control-Max-Age', '3600')
        origin = request.headers.get('Origin')
        if origin in ['http://localhost:3000']:
            response.headers['Access-Control-Allow-Origin'] = origin
        return response

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in ['http://localhost:3000']:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Expose-Headers', 'Content-Type, Authorization')
    return response



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
app.add_url_rule('/api/spheres/<sphere_id>/join', view_func=join_sphere, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/spheres/<sphere_id>/image', view_func=update_sphere_image, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/spheres/<sphere_id>/members/<target_id>/role', view_func=set_sphere_role, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/alliances', view_func=create_alliance, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/alliances', view_func=get_alliances, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/alliances/<alliance_id>/join', view_func=join_alliance, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/alliances/<alliance_id>/image', view_func=update_alliance_image, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/alliances/<alliance_id>/members/<target_id>/role', view_func=set_alliance_role, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/projects', view_func=create_project, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/projects', view_func=get_projects, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/projects/<project_id>/join', view_func=join_project, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/projects/<project_id>/image', view_func=update_project_image, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/projects/<project_id>/members/<target_id>/role', view_func=set_project_role, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings', view_func=create_service, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings', view_func=get_services, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>', view_func=get_service, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>/accept', view_func=accept_service, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>/confirm', view_func=confirm_service, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>/reject', view_func=reject_service, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>/like', view_func=like_service, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/openings/<service_id>/image', view_func=update_service_image, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/value_cards/clone', view_func=clone_value_card, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/value_cards/<target_user_id>', view_func=get_value_cards, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/value_cards', view_func=create_value_card, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/value_cards/<card_id>', view_func=delete_value_card, methods=['DELETE', 'OPTIONS'])
app.add_url_rule('/api/entity_value_cards/<entity_id>', view_func=create_entity_value_card, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/notifications', view_func=get_notifications, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/notifications/read', view_func=mark_notification_read, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/notifications/read_all', view_func=mark_all_notifications_read, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/entity_value_cards/<entity_id>/<card_id>', view_func=delete_entity_value_card, methods=['DELETE', 'OPTIONS'])

@app.errorhandler(500)
def internal_error(error):
    response = jsonify({"error": "Internal Server Error"})
    response.status_code = 500
    origin = request.headers.get('Origin')
    if origin in ['http://localhost:3000']:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

if __name__ == '__main__':
    context = ('/home/igor/LogoSphere/backend/app/localhost.crt', '/home/igor/LogoSphere/backend/app/localhost.key') 
    with app.app_context():
        #app.run(debug=True, ssl_context=context, host="0.0.0.0")
        app.run(debug=True, host="0.0.0.0")