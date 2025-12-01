from flask import Blueprint, request, jsonify, current_app, redirect, url_for
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity, get_jwt
)
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests
from app import db
from app.models.user import User, UserRole
from app.utils.validators import (
    validate_email, validate_password, 
    validate_username, validate_required_fields
)
import secrets
import string

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/signup', methods=['POST'])
def signup():
    """
    User registration endpoint
    ---
    Required fields: email, username, password, first_name, last_name
    Optional fields: role (defaults to 'customer')
    """
    try:
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['email', 'username', 'password', 'first_name', 'last_name']
        is_valid, message = validate_required_fields(data, required_fields)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Extract data
        email = data['email'].lower().strip()
        username = data['username'].strip()
        password = data['password']
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        role = data.get('role', 'customer').lower()
        
        # Validate email
        if not validate_email(email):
            return jsonify({'error': 'Invalid email format'}), 400
        
        # Validate username
        is_valid, message = validate_username(username)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Validate password
        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Validate role
        try:
            user_role = UserRole(role)
        except ValueError:
            return jsonify({'error': 'Invalid role. Must be either "customer" or "admin"'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already registered'}), 409
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already taken'}), 409
        
        # Create new user
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=user_role
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        # Generate tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        return jsonify({
            'message': 'User registered successfully',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Registration failed', 'message': str(e)}), 500


@auth_bp.route('/login', methods=['POST'])
def login():
    """
    User login endpoint
    ---
    Required fields: email or username, password
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Get credentials
        email_or_username = data.get('email') or data.get('username')
        password = data.get('password')
        
        if not email_or_username or not password:
            return jsonify({'error': 'Email/username and password are required'}), 400
        
        # Find user by email or username
        email_or_username = email_or_username.lower().strip()
        user = User.query.filter(
            (User.email == email_or_username) | (User.username == email_or_username)
        ).first()
        
        if not user or not user.check_password(password):
            return jsonify({'error': 'Invalid credentials'}), 401
        
        if not user.is_active:
            return jsonify({'error': 'Account is inactive'}), 403
        
        # Generate tokens
        access_token = create_access_token(identity=str(user.id))
        refresh_token = create_refresh_token(identity=str(user.id))
        
        return jsonify({
            'message': 'Login successful',
            'user': user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Login failed', 'message': str(e)}), 500


@auth_bp.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    """
    Refresh access token using refresh token
    """
    try:
        current_user_id = get_jwt_identity()  # This is now a string
        access_token = create_access_token(identity=current_user_id)
        
        return jsonify({
            'access_token': access_token
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Token refresh failed', 'message': str(e)}), 500


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    """
    Get current authenticated user information
    """
    try:
        current_user_id = int(get_jwt_identity())  # Convert string back to int
        user = User.query.get(current_user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify({
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get user', 'message': str(e)}), 500


@auth_bp.route('/verify-token', methods=['GET'])
@jwt_required()
def verify_token():
    """
    Verify and get information about the current token
    """
    try:
        current_user_id = int(get_jwt_identity())  # Convert string back to int
        jwt_data = get_jwt()
        token_type = jwt_data.get('type', 'access')
        
        return jsonify({
            'valid': True,
            'user_id': current_user_id,
            'token_type': token_type,
            'message': f'This is a valid {token_type} token'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Token verification failed', 'message': str(e)}), 500


@auth_bp.route('/logout', methods=['POST'])
@jwt_required()
def logout():
    """
    Logout endpoint (client should delete tokens)
    Note: For production, implement token blacklisting
    """
    return jsonify({
        'message': 'Logout successful. Please delete your tokens.'
    }), 200


@auth_bp.route('/google/login', methods=['POST'])
def google_login():
    """
    Google OAuth login endpoint
    Expects: { "credential": "google_id_token" }
    """
    try:
        data = request.get_json()
        
        if not data or 'credential' not in data:
            return jsonify({'error': 'Google credential is required'}), 400
        
        google_token = data['credential']
        
        # Verify the Google token
        try:
            idinfo = id_token.verify_oauth2_token(
                google_token,
                google_requests.Request(),
                current_app.config['GOOGLE_CLIENT_ID']
            )
            
            # Get user info from Google token
            google_user_id = idinfo['sub']
            email = idinfo.get('email', '').lower().strip()
            email_verified = idinfo.get('email_verified', False)
            first_name = idinfo.get('given_name', '')
            last_name = idinfo.get('family_name', '')
            profile_picture = idinfo.get('picture', '')
            
            if not email_verified:
                return jsonify({'error': 'Email not verified by Google'}), 400
            
        except ValueError as e:
            return jsonify({'error': 'Invalid Google token', 'message': str(e)}), 401
        
        # Check if user exists with this Google ID
        user = User.query.filter_by(oauth_provider='google', oauth_id=google_user_id).first()
        
        if user:
            # Existing Google user - update profile picture if changed
            if user.profile_picture != profile_picture:
                user.profile_picture = profile_picture
                db.session.commit()
            
            # Generate tokens
            access_token = create_access_token(identity=str(user.id))
            refresh_token = create_refresh_token(identity=str(user.id))
            
            return jsonify({
                'message': 'Login successful',
                'user': user.to_dict(),
                'access_token': access_token,
                'refresh_token': refresh_token
            }), 200
        
        # Check if user exists with this email (non-OAuth)
        existing_user = User.query.filter_by(email=email).first()
        if existing_user and not existing_user.is_oauth_user():
            return jsonify({
                'error': 'An account with this email already exists. Please login with your password.'
            }), 409
        
        # Create new user with Google OAuth
        # Generate unique username from email
        base_username = email.split('@')[0]
        username = base_username
        counter = 1
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        new_user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=UserRole.CUSTOMER,
            oauth_provider='google',
            oauth_id=google_user_id,
            profile_picture=profile_picture,
            password_hash=None  # OAuth users don't have passwords
        )
        
        db.session.add(new_user)
        db.session.commit()
        
        # Generate tokens
        access_token = create_access_token(identity=str(new_user.id))
        refresh_token = create_refresh_token(identity=str(new_user.id))
        
        return jsonify({
            'message': 'User registered successfully',
            'user': new_user.to_dict(),
            'access_token': access_token,
            'refresh_token': refresh_token
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Google login failed', 'message': str(e)}), 500


@auth_bp.route('/health', methods=['GET'])
def health():
    """
    Health check endpoint for Docker/Kubernetes
    """
    try:
        # Check database connectivity
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        return jsonify({
            'status': 'healthy',
            'database': 'connected'
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'database': 'disconnected',
            'error': str(e)
        }), 503