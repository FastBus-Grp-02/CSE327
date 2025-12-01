from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.models.user import User, UserRole


def role_required(*roles):
    """Decorator to check if user has required role"""
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            verify_jwt_in_request()
            current_user_id = int(get_jwt_identity())  # Convert string to int
            user = User.query.get(current_user_id)
            
            if not user:
                return jsonify({'error': 'User not found'}), 404
            
            if not user.is_active:
                return jsonify({'error': 'User account is inactive'}), 403
            
            if user.role not in roles:
                return jsonify({'error': 'Insufficient permissions'}), 403
            
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    """Decorator to require admin role"""
    return role_required(UserRole.ADMIN)(fn)


def get_current_user():
    """Get current authenticated user"""
    verify_jwt_in_request()
    current_user_id = int(get_jwt_identity())  # Convert string to int
    return User.query.get(current_user_id)

