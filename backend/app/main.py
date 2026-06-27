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
from app.routes.profile import get_user, get_profile, update_user, get_public_user
from app.routes.registration import register
from app.routes.trusttrail import get_trusttrail, add_transaction
from app.models.user import User
from app.routes.spheres import create_sphere, get_spheres
from app.routes.unions import create_union, get_unions
from app.routes.projects import create_project, get_projects
from app.routes.marketplace import create_service, get_services

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
    PERMANENT_SESSION_LIFETIME=timedelta(hours=24)
)



# Initialize session interface
session_interface = CassandraSessionInterface(
    cluster_nodes=os.environ.get('CASSANDRA_HOST', '127.0.0.1').split(','),
    keyspace='trustsphere',
    session_lifetime=timedelta(hours=24)
)
app.session_interface = session_interface   


# Enable CORS for all routes before defining any routes
CORS(app, resources={r"/api/*": {
    "origins": ["http://localhost:3000", "http://172.236.62.11:3000"],
    "allow_headers": ["Content-Type", "Authorization", "X-Requested-With", "session_id"],
    "expose_headers": ["Content-Type", "Authorization", "session_id"],
    "supports_credentials": True,
    "allow_credentials": True,
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
}})


@app.before_request
def handle_preflight():
    if request.method == "OPTIONS":
        response = app.make_default_options_response()
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, session_id')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers.add('Access-Control-Max-Age', '3600')
        origin = request.headers.get('Origin')
        if origin in ['http://localhost:3000', 'http://172.236.62.11:3000']:
            response.headers['Access-Control-Allow-Origin'] = origin
        return response

@app.after_request
def after_request(response):
    origin = request.headers.get('Origin')
    if origin in ['http://localhost:3000', 'http://172.236.62.11:3000']:
        response.headers['Access-Control-Allow-Origin'] = origin
        response.headers['Access-Control-Allow-Credentials'] = 'true'
        response.headers.add('Access-Control-Allow-Headers', 'Content-Type, Authorization, session_id')
        response.headers.add('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        response.headers.add('Access-Control-Expose-Headers', 'Content-Type, Authorization, session_id')
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
app.add_url_rule('/api/updateuser', view_func=update_user, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/register', view_func=register, methods=['POST'])
app.add_url_rule('/api/trusttrail', view_func=get_trusttrail, methods=['GET', 'POST', 'OPTIONS'])
app.add_url_rule('/api/trusttrail/add_transaction', view_func=add_transaction, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/spheres', view_func=create_sphere, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/spheres', view_func=get_spheres, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/unions', view_func=create_union, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/unions', view_func=get_unions, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/projects', view_func=create_project, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/projects', view_func=get_projects, methods=['GET', 'OPTIONS'])
app.add_url_rule('/api/marketplace', view_func=create_service, methods=['POST', 'OPTIONS'])
app.add_url_rule('/api/marketplace', view_func=get_services, methods=['GET', 'OPTIONS'])

@app.errorhandler(500)
def internal_error(error):
    response = jsonify({"error": "Internal Server Error"})
    response.status_code = 500
    origin = request.headers.get('Origin')
    if origin in ['http://localhost:3000', 'http://172.236.62.11:3000']:
        response.headers.add('Access-Control-Allow-Origin', origin)
        response.headers.add('Access-Control-Allow-Credentials', 'true')
    return response

if __name__ == '__main__':
    context = ('/home/igor/TrustSphere/backend/app/localhost.crt', '/home/igor/TrustSphere/backend/app/localhost.key') 
    with app.app_context():
        #app.run(debug=True, ssl_context=context, host="0.0.0.0")
        app.run(debug=True, host="0.0.0.0")