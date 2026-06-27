# File: ./backend/app/routes/profile.py
# Description: This is the Flask route file handling User Profile operations.
# Methods: 
#    [+] get_user(): Handles the GET and POST requests to fetch or update user profile details, calling the relevant methods in the User model.
#    [+] update_user(): Handles the update of user profile data using the User model's update method.

import logging
from flask import request, jsonify, current_app as app
from app.models.user import User
from app.middleware.session_middleware import validate_session

logger = logging.getLogger(__name__)

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
        return jsonify(user.to_dict()), 200
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
        else:
            data = request.get_json()
            profile_picture = data.get('profile_picture')

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