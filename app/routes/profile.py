from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.user import User
from app.utils.validators import (
    validate_email, validate_password, 
    validate_username, validate_required_fields
)

profile_bp = Blueprint('profile', __name__)


@profile_bp.route('/', methods=['GET'])
@jwt_required()
def get_profile():
    """
    Get current user's profile information
    """
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 403
        
        return jsonify({
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get profile', 'message': str(e)}), 500


@profile_bp.route('/', methods=['PUT'])
@jwt_required()
def update_profile():
    """
    Update user profile information (full update)
    ---
    Allowed fields: first_name, last_name, username, email
    Note: Password changes should use the dedicated password endpoint
    """
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Track what was updated
        updated_fields = []
        
        # Update first name
        if 'first_name' in data:
            first_name = data['first_name'].strip()
            if not first_name:
                return jsonify({'error': 'First name cannot be empty'}), 400
            if len(first_name) > 100:
                return jsonify({'error': 'First name must be 100 characters or less'}), 400
            user.first_name = first_name
            updated_fields.append('first_name')
        
        # Update last name
        if 'last_name' in data:
            last_name = data['last_name'].strip()
            if not last_name:
                return jsonify({'error': 'Last name cannot be empty'}), 400
            if len(last_name) > 100:
                return jsonify({'error': 'Last name must be 100 characters or less'}), 400
            user.last_name = last_name
            updated_fields.append('last_name')
        
        # Update username
        if 'username' in data:
            username = data['username'].strip()
            
            # Validate username format
            is_valid, message = validate_username(username)
            if not is_valid:
                return jsonify({'error': message}), 400
            
            # Check if username is already taken by another user
            existing_user = User.query.filter_by(username=username).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Username already taken'}), 409
            
            user.username = username
            updated_fields.append('username')
        
        # Update email
        if 'email' in data:
            email = data['email'].lower().strip()
            
            # Validate email format
            if not validate_email(email):
                return jsonify({'error': 'Invalid email format'}), 400
            
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Email already registered'}), 409
            
            user.email = email
            updated_fields.append('email')
        
        # Prevent password changes through this endpoint
        if 'password' in data or 'password_hash' in data:
            return jsonify({
                'error': 'Password cannot be changed through this endpoint. Use /profile/password instead'
            }), 400
        
        if not updated_fields:
            return jsonify({'error': 'No valid fields provided for update'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'updated_fields': updated_fields,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile', 'message': str(e)}), 500


@profile_bp.route('/', methods=['PATCH'])
@jwt_required()
def partial_update_profile():
    """
    Partially update user profile information
    ---
    Allowed fields: first_name, last_name, username, email
    Only provided fields will be updated
    """
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Track what was updated
        updated_fields = []
        
        # Update first name
        if 'first_name' in data:
            first_name = data['first_name'].strip()
            if not first_name:
                return jsonify({'error': 'First name cannot be empty'}), 400
            if len(first_name) > 100:
                return jsonify({'error': 'First name must be 100 characters or less'}), 400
            user.first_name = first_name
            updated_fields.append('first_name')
        
        # Update last name
        if 'last_name' in data:
            last_name = data['last_name'].strip()
            if not last_name:
                return jsonify({'error': 'Last name cannot be empty'}), 400
            if len(last_name) > 100:
                return jsonify({'error': 'Last name must be 100 characters or less'}), 400
            user.last_name = last_name
            updated_fields.append('last_name')
        
        # Update username
        if 'username' in data:
            username = data['username'].strip()
            
            # Validate username format
            is_valid, message = validate_username(username)
            if not is_valid:
                return jsonify({'error': message}), 400
            
            # Check if username is already taken by another user
            existing_user = User.query.filter_by(username=username).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Username already taken'}), 409
            
            user.username = username
            updated_fields.append('username')
        
        # Update email
        if 'email' in data:
            email = data['email'].lower().strip()
            
            # Validate email format
            if not validate_email(email):
                return jsonify({'error': 'Invalid email format'}), 400
            
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({'error': 'Email already registered'}), 409
            
            user.email = email
            updated_fields.append('email')
        
        # Prevent password changes through this endpoint
        if 'password' in data or 'password_hash' in data:
            return jsonify({
                'error': 'Password cannot be changed through this endpoint. Use /profile/password instead'
            }), 400
        
        if not updated_fields:
            return jsonify({'error': 'No valid fields provided for update'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': 'Profile updated successfully',
            'updated_fields': updated_fields,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update profile', 'message': str(e)}), 500


@profile_bp.route('/password', methods=['PUT'])
@jwt_required()
def change_password():
    """
    Change user password
    ---
    Required fields: current_password, new_password
    Security: Requires current password verification
    """
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['current_password', 'new_password']
        is_valid, message = validate_required_fields(data, required_fields)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        current_password = data['current_password']
        new_password = data['new_password']
        
        # Verify current password
        if not user.check_password(current_password):
            return jsonify({'error': 'Current password is incorrect'}), 401
        
        # Ensure new password is different
        if current_password == new_password:
            return jsonify({'error': 'New password must be different from current password'}), 400
        
        # Validate new password strength
        is_valid, message = validate_password(new_password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Update password
        user.set_password(new_password)
        db.session.commit()
        
        return jsonify({
            'message': 'Password changed successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to change password', 'message': str(e)}), 500


@profile_bp.route('/name', methods=['PUT'])
@jwt_required()
def update_name():
    """
    Update user's first and last name
    ---
    Required fields: first_name, last_name
    Convenience endpoint for name-only updates
    """
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 403
        
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['first_name', 'last_name']
        is_valid, message = validate_required_fields(data, required_fields)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        
        # Validate name lengths
        if len(first_name) > 100:
            return jsonify({'error': 'First name must be 100 characters or less'}), 400
        
        if len(last_name) > 100:
            return jsonify({'error': 'Last name must be 100 characters or less'}), 400
        
        # Update names
        user.first_name = first_name
        user.last_name = last_name
        
        db.session.commit()
        
        return jsonify({
            'message': 'Name updated successfully',
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update name', 'message': str(e)}), 500

