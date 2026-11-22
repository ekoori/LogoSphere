# File: ./backend/app/routes/profile.py
# Description: This is the Flask route file handling User Profile operations.
# Methods: 
#    [+] get_user(): Handles the GET and POST requests to fetch or update user profile details, calling the relevant methods in the User model.
#    [+] update_user(): Handles the update of user profile data using the User model's update method.

import logging
import uuid
from html import escape
from flask import request, jsonify, current_app as app, Response
from app.models.user import User
from app.models.follow import Follow
from app.models.notification import Notification
from app.utils.validation import is_supported_image
from app.utils.pictures import picture_response
from app.utils.permissions import is_platform_admin
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)


_AVATAR_SIDE = 80
_INITIALS_SIZE = 34
# Half a capital's height, as a share of the font size (Roboto .356, Segoe .35,
# San Francisco .352). Renderers don't agree on `dominant-baseline` (Android's
# ignores it, which left the initials riding high), so the baseline itself is
# placed that far below the middle.
_HALF_CAPITAL = 0.354
INITIALS_BASELINE = round(_AVATAR_SIDE / 2 + _HALF_CAPITAL * _INITIALS_SIZE, 1)


def _initials_avatar_svg(name):
    """A small SVG avatar (initials on the brand's moss gradient), returned in
    place of a 404 when a user has no uploaded photo — so <img> tags never log a
    console 404 and everyone gets a consistent placeholder. Mirrors the frontend
    Avatar component's initials look."""
    # Words that start with a letter or digit: "Bruce (AI)" is B, not "B(".
    parts = [p for p in (name or '').split() if p[0].isalnum()]
    initials = escape(''.join(p[0] for p in parts[:2]).upper() or '?')
    return (
        '<svg xmlns="http://www.w3.org/2000/svg" width="80" height="80" viewBox="0 0 80 80">'
        '<defs><radialGradient id="g" cx="30%" cy="25%" r="90%">'
        '<stop offset="0%" stop-color="#7a9a56"/><stop offset="100%" stop-color="#5f7a4f"/>'
        '</radialGradient></defs>'
        '<rect width="80" height="80" rx="40" fill="url(#g)"/>'
        f'<text x="40" y="{INITIALS_BASELINE}" font-family="system-ui,-apple-system,Segoe UI,sans-serif" '
        f'font-size="{_INITIALS_SIZE}" font-weight="600" fill="#f7f4e8" text-anchor="middle">'
        f'{initials}</text></svg>'
    )


@validate_session
def toggle_follow(target_id, user_id=None):
    """Follow/unfollow another user. Returns the new {following} state."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        if str(target_id) == str(user_id):
            return jsonify({'message': "You can't follow yourself"}), 400
        # Following an id that is nobody stored a follow row and a notification
        # for a person who doesn't exist.
        if not User.get(str(target_id)):
            return jsonify({'message': 'User not found'}), 404
        following = Follow.toggle(user_id, target_id)
        if following:
            follower = User.get(str(user_id))
            follower_name = (f"{follower.name or ''} {follower.surname or ''}".strip() or follower.email) if follower else 'Someone'
            Notification.create(
                user_id=target_id, actor_id=user_id, actor_name=follower_name,
                type_='new_follower',
                message=f'{follower_name} started following you',
                link=f'/user?id={user_id}',
            )
        return jsonify({'following': following}), 200
    except ValueError:
        return jsonify({'message': 'Invalid user id'}), 400
    except Exception as e:
        logger.error(f"Error in toggle_follow: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def get_following(user_id=None):
    """List the users the current user follows: [{id, name}]."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        ids = Follow.following_ids(user_id)
        out = []
        for uid in ids:
            u = User.get(str(uid))
            if u:
                name = f"{u.name or ''} {u.surname or ''}".strip() or u.email
                out.append({'id': str(uid), 'name': name})
        return jsonify(out), 200
    except Exception as e:
        logger.error(f"Error in get_following: {e}")
        return jsonify({'message': 'Internal server error'}), 500


def get_user_avatar(target_id):
    """Serve a user's avatar image for <img src> tags. Public (no session) and
    cacheable — avatars aren't sensitive and this keeps blob bytes out of JSON
    payloads and lets the browser cache each one. When the user has no uploaded
    photo we return a generated initials SVG (HTTP 200) rather than a 404, so
    the browser console isn't spammed with 404s for every avatar-less user."""
    try:
        user = User.get(str(target_id))
        data = User.get_picture(target_id) if user and user.has_picture else None
        if not data:
            name = (f"{user.name or ''} {user.surname or ''}".strip() if user else '')
            return picture_response(_initials_avatar_svg(name).encode('utf-8'), ctype='image/svg+xml')
        return picture_response(data)
    except Exception as e:
        logger.error(f"Error in get_user_avatar: {e}")
        # Last-resort placeholder so the <img> still resolves without a console error.
        resp = Response(_initials_avatar_svg(''), mimetype='image/svg+xml')
        resp.headers['Cache-Control'] = 'no-cache'
        return resp

@validate_session
def get_user(user_id=None):
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response, 200

    try:
        logger.info(f"Fetching basic user data for user_id: {user_id}")
        
        # Ensure user_id is a string
        user_id = str(user_id)
        
        # Get user data
        user = User.get(user_id)
        if user:
            user_data = {
                'user_id': str(user.user_id),
                'email': user.email,
                'name': user.name
            }
            logger.info(f"Successfully retrieved basic user data for user_id: {user_id}")
            
            response = jsonify(user_data)
            return response, 200
        else:
            logger.error(f'User not found with user_id: {user_id}')
            response = jsonify({'message': 'User not found'})
            return response, 404

    except Exception as e:
        logger.error(f"Error in get_user: {str(e)}")
        response = jsonify({'message': 'Internal server error'})
        return response, 500

@validate_session
def get_public_user(target_id, user_id=None):
    """Fetch any user's public profile by id (for /user?id=... pages).
    `target_id` is the path param; `user_id` is the authenticated session user."""
    if request.method == 'OPTIONS':
        return app.make_default_options_response(), 200
    try:
        user = User.get(str(target_id))
        if not user:
            return jsonify({'message': 'User not found'}), 404
        d = user.to_dict()
        # Email addresses are private: any signed-in member could otherwise read
        # every member's address by walking user ids. Only the person themself
        # and platform admins (who already see it in the admin console) get it.
        if str(target_id) != str(user_id) and not is_platform_admin(user_id):
            d.pop('email', None)
        # Whether the viewer follows this user, + their follower/following counts.
        d['is_following'] = (str(target_id) != str(user_id)) and Follow.is_following(user_id, target_id)
        d['following_count'] = Follow.following_count(target_id)
        return jsonify(d), 200
    except Exception as e:
        logger.error(f"Error in get_public_user: {e}")
        return jsonify({'message': 'Internal server error'}), 500


@validate_session
def get_profile(user_id=None):
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response, 200

    try:
        logger.info(f"Fetching user profile data for user_id: {user_id}")
        
        # Ensure user_id is a string
        user_id = str(user_id)
        
        # Get user profile data
        user = User.get(user_id)
        if user:
            user_data = user.to_dict()
            logger.info(f"Successfully retrieved user profile data for user_id: {user_id}")
            
            response = jsonify(user_data)
            return response, 200
        else:
            logger.error(f'User not found with user_id: {user_id}')
            response = jsonify({'message': 'User not found'})
            return response, 404

    except Exception as e:
        logger.error(f"Error in get_profile: {str(e)}")
        response = jsonify({'message': 'Internal server error'})
        return response, 500

@validate_session
def update_user(user_id=None):
    if request.method == 'OPTIONS':
        response = app.make_default_options_response()
        return response, 200

    try:
        if 'multipart/form-data' in request.content_type:
            data = request.form
            profile_picture = request.files.get('profile_picture')
            if profile_picture:
                profile_picture = profile_picture.read()
                if not is_supported_image(profile_picture):
                    return jsonify({'message': 'Unsupported image format (use JPEG, PNG, GIF or WebP)'}), 400
        else:
            data = request.get_json(silent=True)
            # A picture only arrives as a validated multipart upload; a JSON
            # value would go into the blob column unchecked.
            profile_picture = None

        logger.debug(f"Received update data: {data}")
        if not data:
            logger.error("No data provided for update")
            response = jsonify({'message': 'No data provided'})
            return response, 400

        logger.info(f"Updating user profile for user_id: {user_id}")
        
        # Ensure user_id is a string
        user_id = str(user_id)
        
        # Extract fields from the request data
        name = data.get('name')
        surname = data.get('surname')
        location = data.get('location')

        # Update user profile
        updated_user = User.update(
            user_id,
            name=name,
            surname=surname,
            location=location,
            profile_picture=profile_picture
        )
        
        if updated_user:
            logger.info(f"Successfully updated profile for user_id: {user_id}")
            response = jsonify(updated_user.to_dict())
            return response, 200
        else:
            logger.error(f"Failed to update profile for user_id: {user_id}")
            response = jsonify({'message': 'Failed to update user profile'})
            return response, 400

    except Exception as e:
        logger.error(f"Error in update_user: {str(e)}")
        response = jsonify({'message': 'Internal server error'})
        return response, 500