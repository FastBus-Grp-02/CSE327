from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.user import User, UserRole
from app.models.booking import Booking, PaymentStatus
from app.utils.decorators import admin_required
from app.utils.validators import validate_required_fields, validate_email, validate_username, validate_password
from datetime import datetime
from sqlalchemy import func, desc

admin_users_bp = Blueprint('admin_users', __name__)


@admin_users_bp.route('/', methods=['GET'])
@jwt_required()
@admin_required
def get_all_users():
    """
    Get all users with filtering and pagination
    ---
    Query parameters:
    - role: Filter by role (customer/admin)
    - is_active: Filter by active status (true/false)
    - search: Search by username, email, first_name, or last_name
    - date_from: Filter users created from date (YYYY-MM-DD)
    - date_to: Filter users created to date (YYYY-MM-DD)
    - limit: Number of results (default: 50)
    - offset: Pagination offset (default: 0)
    - sort_by: Sort field (created_at, username, email, last_login_at)
    - sort_order: Sort order (asc, desc)
    """
    try:
        # Get query parameters
        role = request.args.get('role', '').lower()
        is_active = request.args.get('is_active', '').lower()
        search = request.args.get('search', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        sort_by = request.args.get('sort_by', 'created_at').lower()
        sort_order = request.args.get('sort_order', 'desc').lower()
        
        # Build query
        query = User.query
        
        # Apply filters
        if role:
            try:
                user_role = UserRole(role)
                query = query.filter_by(role=user_role)
            except ValueError:
                return jsonify({'error': 'Invalid role'}), 400
        
        if is_active == 'true':
            query = query.filter_by(is_active=True)
        elif is_active == 'false':
            query = query.filter_by(is_active=False)
        
        if search:
            search_filter = f'%{search}%'
            query = query.filter(
                (User.username.ilike(search_filter)) |
                (User.email.ilike(search_filter)) |
                (User.first_name.ilike(search_filter)) |
                (User.last_name.ilike(search_filter))
            )
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(User.created_at >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format. Use YYYY-MM-DD'}), 400
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(User.created_at <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format. Use YYYY-MM-DD'}), 400
        
        # Apply sorting
        if sort_by == 'username':
            sort_column = User.username
        elif sort_by == 'email':
            sort_column = User.email
        elif sort_by == 'last_login_at':
            sort_column = User.last_login_at
        else:
            sort_column = User.created_at
        
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        users = query.limit(limit).offset(offset).all()
        
        # Add user statistics
        users_data = []
        for user in users:
            user_dict = user.to_dict()
            
            # Get booking count
            booking_count = Booking.query.filter_by(user_id=user.id).count()
            user_dict['booking_count'] = booking_count
            
            # Get total spent (only paid bookings)
            total_spent = db.session.query(func.sum(Booking.total_amount)).filter(
                Booking.user_id == user.id,
                Booking.payment_status == PaymentStatus.PAID
            ).scalar() or 0
            user_dict['total_spent'] = float(total_spent)
            
            users_data.append(user_dict)
        
        return jsonify({
            'users': users_data,
            'count': len(users),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get users', 'message': str(e)}), 500


@admin_users_bp.route('/<int:user_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_user(user_id):
    """
    Get detailed user information including booking history
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user_data = user.to_dict()
        
        # Get booking statistics
        bookings = Booking.query.filter_by(user_id=user_id).all()
        user_data['booking_count'] = len(bookings)
        
        # Total spent
        total_spent = db.session.query(func.sum(Booking.total_amount)).filter(
            Booking.user_id == user_id,
            Booking.payment_status == PaymentStatus.PAID
        ).scalar() or 0
        user_data['total_spent'] = float(total_spent)
        
        # Recent bookings
        recent_bookings = Booking.query.filter_by(user_id=user_id).order_by(
            Booking.created_at.desc()
        ).limit(10).all()
        user_data['recent_bookings'] = [booking.to_dict(include_relationships=True) for booking in recent_bookings]
        
        return jsonify({
            'user': user_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get user', 'message': str(e)}), 500


@admin_users_bp.route('/', methods=['POST'])
@jwt_required()
@admin_required
def create_user():
    """
    Create a new user (admin or customer)
    ---
    Request body:
    {
        "email": "string",
        "username": "string",
        "password": "string",
        "first_name": "string",
        "last_name": "string",
        "role": "customer|admin",
        "is_active": boolean (optional, default: true)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['email', 'username', 'password', 'first_name', 'last_name', 'role']
        is_valid, message = validate_required_fields(data, required_fields)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Extract data
        email = data['email'].lower().strip()
        username = data['username'].strip()
        password = data['password']
        first_name = data['first_name'].strip()
        last_name = data['last_name'].strip()
        role = data['role'].lower()
        is_active = data.get('is_active', True)
        
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
            return jsonify({'error': 'Invalid role. Must be "customer" or "admin"'}), 400
        
        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 409
        
        if User.query.filter_by(username=username).first():
            return jsonify({'error': 'Username already exists'}), 409
        
        # Create user
        user = User(
            email=email,
            username=username,
            first_name=first_name,
            last_name=last_name,
            role=user_role,
            is_active=is_active
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User created successfully',
            'user': user.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create user', 'message': str(e)}), 500


@admin_users_bp.route('/<int:user_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_user(user_id):
    """
    Update user information
    ---
    Allowed fields: email, username, first_name, last_name, role, is_active
    Note: Password update should be done through a separate endpoint
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        updated_fields = []
        
        # Update email
        if 'email' in data:
            email = data['email'].lower().strip()
            if not validate_email(email):
                return jsonify({'error': 'Invalid email format'}), 400
            
            # Check if email is already taken by another user
            existing_user = User.query.filter_by(email=email).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({'error': 'Email already exists'}), 409
            
            user.email = email
            updated_fields.append('email')
        
        # Update username
        if 'username' in data:
            username = data['username'].strip()
            is_valid, message = validate_username(username)
            if not is_valid:
                return jsonify({'error': message}), 400
            
            # Check if username is already taken by another user
            existing_user = User.query.filter_by(username=username).first()
            if existing_user and existing_user.id != user_id:
                return jsonify({'error': 'Username already exists'}), 409
            
            user.username = username
            updated_fields.append('username')
        
        # Update first name
        if 'first_name' in data:
            user.first_name = data['first_name'].strip()
            updated_fields.append('first_name')
        
        # Update last name
        if 'last_name' in data:
            user.last_name = data['last_name'].strip()
            updated_fields.append('last_name')
        
        # Update role
        if 'role' in data:
            try:
                user.role = UserRole(data['role'].lower())
                updated_fields.append('role')
            except ValueError:
                return jsonify({'error': 'Invalid role'}), 400
        
        # Update is_active
        if 'is_active' in data:
            user.is_active = bool(data['is_active'])
            updated_fields.append('is_active')
        
        if not updated_fields:
            return jsonify({'error': 'No valid fields provided for update'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': 'User updated successfully',
            'updated_fields': updated_fields,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update user', 'message': str(e)}), 500


@admin_users_bp.route('/<int:user_id>/password', methods=['PUT'])
@jwt_required()
@admin_required
def reset_user_password(user_id):
    """
    Reset user password
    ---
    Request body:
    {
        "password": "string"
    }
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        data = request.get_json()
        
        if not data or 'password' not in data:
            return jsonify({'error': 'Password is required'}), 400
        
        password = data['password']
        
        # Validate password
        is_valid, message = validate_password(password)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        user.set_password(password)
        db.session.commit()
        
        return jsonify({
            'message': 'Password reset successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to reset password', 'message': str(e)}), 500


@admin_users_bp.route('/<int:user_id>/toggle', methods=['PUT'])
@jwt_required()
@admin_required
def toggle_user_status(user_id):
    """
    Toggle user active/inactive status
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        user.is_active = not user.is_active
        db.session.commit()
        
        return jsonify({
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully',
            'is_active': user.is_active,
            'user': user.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to toggle user status', 'message': str(e)}), 500


@admin_users_bp.route('/<int:user_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_user(user_id):
    """
    Delete a user
    Note: This will also delete all associated bookings, payments, and tickets
    Use with extreme caution!
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        # Check if user has any bookings
        booking_count = Booking.query.filter_by(user_id=user_id).count()
        
        if booking_count > 0:
            return jsonify({
                'error': f'Cannot delete user with existing bookings ({booking_count} bookings). Consider deactivating instead.',
                'suggestion': 'Use PUT /admin/users/{id}/toggle to deactivate'
            }), 409
        
        db.session.delete(user)
        db.session.commit()
        
        return jsonify({
            'message': 'User deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete user', 'message': str(e)}), 500


@admin_users_bp.route('/statistics', methods=['GET'])
@jwt_required()
@admin_required
def get_user_statistics():
    """
    Get user statistics
    """
    try:
        now = datetime.utcnow()
        
        # Total users by role
        total_customers = User.query.filter_by(role=UserRole.CUSTOMER).count()
        total_admins = User.query.filter_by(role=UserRole.ADMIN).count()
        
        # Active vs inactive
        active_users = User.query.filter_by(is_active=True).count()
        inactive_users = User.query.filter_by(is_active=False).count()
        
        # New users this month
        first_day_of_month = now.replace(day=1, hour=0, minute=0, second=0)
        new_users_this_month = User.query.filter(
            User.created_at >= first_day_of_month
        ).count()
        
        # Users with bookings
        users_with_bookings = db.session.query(func.count(func.distinct(Booking.user_id))).scalar()
        
        # Top customers by bookings
        top_customers_bookings = db.session.query(
            User.id,
            User.username,
            User.email,
            func.count(Booking.id).label('booking_count')
        ).join(Booking).group_by(User.id, User.username, User.email).order_by(
            desc('booking_count')
        ).limit(10).all()
        
        # Top customers by revenue
        top_customers_revenue = db.session.query(
            User.id,
            User.username,
            User.email,
            func.sum(Booking.total_amount).label('total_spent')
        ).join(Booking).filter(
            Booking.payment_status == PaymentStatus.PAID
        ).group_by(User.id, User.username, User.email).order_by(
            desc('total_spent')
        ).limit(10).all()
        
        return jsonify({
            'statistics': {
                'total_users': total_customers + total_admins,
                'total_customers': total_customers,
                'total_admins': total_admins,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'new_users_this_month': new_users_this_month,
                'users_with_bookings': users_with_bookings,
                'top_customers_by_bookings': [
                    {
                        'user_id': customer[0],
                        'username': customer[1],
                        'email': customer[2],
                        'booking_count': customer[3]
                    }
                    for customer in top_customers_bookings
                ],
                'top_customers_by_revenue': [
                    {
                        'user_id': customer[0],
                        'username': customer[1],
                        'email': customer[2],
                        'total_spent': float(customer[3])
                    }
                    for customer in top_customers_revenue
                ]
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get statistics', 'message': str(e)}), 500


@admin_users_bp.route('/<int:user_id>/bookings', methods=['GET'])
@jwt_required()
@admin_required
def get_user_bookings(user_id):
    """
    Get all bookings for a specific user
    ---
    Query parameters:
    - limit: Number of results (default: 50)
    - offset: Pagination offset (default: 0)
    """
    try:
        user = User.query.get(user_id)
        
        if not user:
            return jsonify({'error': 'User not found'}), 404
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = Booking.query.filter_by(user_id=user_id).order_by(Booking.created_at.desc())
        
        total_count = query.count()
        bookings = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email
            },
            'bookings': [booking.to_dict(include_relationships=True) for booking in bookings],
            'count': len(bookings),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get user bookings', 'message': str(e)}), 500


