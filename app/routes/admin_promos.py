from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.booking import PromoCode
from app.utils.decorators import admin_required
from app.utils.validators import validate_required_fields
from datetime import datetime
from sqlalchemy import func

admin_promos_bp = Blueprint('admin_promos', __name__)


@admin_promos_bp.route('/', methods=['POST'])
@jwt_required()
@admin_required
def create_promo_code():
    """
    Create a new promo code
    ---
    Request body:
    {
        "code": "string",
        "description": "string",
        "discount_percentage": float,
        "max_discount_amount": float (optional),
        "min_purchase_amount": float (optional),
        "usage_limit": int (optional, null for unlimited),
        "usage_per_user": int (optional, default: 1),
        "valid_from": "ISO datetime",
        "valid_until": "ISO datetime"
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['code', 'description', 'discount_percentage', 
                          'valid_from', 'valid_until']
        is_valid, message = validate_required_fields(data, required_fields)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Extract data
        code = data['code'].strip().upper()
        description = data['description'].strip()
        discount_percentage = float(data['discount_percentage'])
        max_discount_amount = data.get('max_discount_amount')
        min_purchase_amount = data.get('min_purchase_amount', 0.0)
        usage_limit = data.get('usage_limit')
        usage_per_user = data.get('usage_per_user', 1)
        
        # Parse datetimes
        try:
            valid_from = datetime.fromisoformat(data['valid_from'].replace('Z', '+00:00'))
            valid_until = datetime.fromisoformat(data['valid_until'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid datetime format. Use ISO format'}), 400
        
        # Validate business logic
        if discount_percentage <= 0 or discount_percentage > 100:
            return jsonify({'error': 'Discount percentage must be between 0 and 100'}), 400
        
        if valid_from >= valid_until:
            return jsonify({'error': 'valid_until must be after valid_from'}), 400
        
        if max_discount_amount is not None:
            max_discount_amount = float(max_discount_amount)
            if max_discount_amount <= 0:
                return jsonify({'error': 'Max discount amount must be positive'}), 400
        
        if min_purchase_amount:
            min_purchase_amount = float(min_purchase_amount)
            if min_purchase_amount < 0:
                return jsonify({'error': 'Min purchase amount cannot be negative'}), 400
        
        if usage_limit is not None:
            usage_limit = int(usage_limit)
            if usage_limit <= 0:
                return jsonify({'error': 'Usage limit must be positive'}), 400
        
        if usage_per_user is not None:
            usage_per_user = int(usage_per_user)
            if usage_per_user <= 0:
                return jsonify({'error': 'Usage per user must be positive'}), 400
        
        # Check if code already exists
        existing_code = PromoCode.query.filter_by(code=code).first()
        if existing_code:
            return jsonify({'error': 'Promo code already exists'}), 409
        
        # Create promo code
        promo_code = PromoCode(
            code=code,
            description=description,
            discount_percentage=discount_percentage,
            max_discount_amount=max_discount_amount,
            min_purchase_amount=min_purchase_amount,
            usage_limit=usage_limit,
            used_count=0,
            usage_per_user=usage_per_user,
            valid_from=valid_from,
            valid_until=valid_until,
            is_active=True
        )
        
        db.session.add(promo_code)
        db.session.commit()
        
        return jsonify({
            'message': 'Promo code created successfully',
            'promo_code': promo_code.to_dict()
        }), 201
        
    except ValueError as e:
        return jsonify({'error': 'Invalid data type provided', 'message': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create promo code', 'message': str(e)}), 500


@admin_promos_bp.route('/', methods=['GET'])
@jwt_required()
@admin_required
def get_all_promo_codes():
    """
    Get all promo codes with filtering and pagination
    ---
    Query parameters:
    - is_active: Filter by active status (true/false)
    - status: Filter by validity status (active/expired/upcoming)
    - limit: Number of results (default: 50)
    - offset: Pagination offset (default: 0)
    - sort_by: Sort field (created_at, valid_from, valid_until, used_count)
    - sort_order: Sort order (asc, desc)
    """
    try:
        # Get query parameters
        is_active = request.args.get('is_active', '').lower()
        status = request.args.get('status', '').lower()
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        sort_by = request.args.get('sort_by', 'created_at').lower()
        sort_order = request.args.get('sort_order', 'desc').lower()
        
        # Build query
        query = PromoCode.query
        
        # Apply filters
        if is_active == 'true':
            query = query.filter_by(is_active=True)
        elif is_active == 'false':
            query = query.filter_by(is_active=False)
        
        now = datetime.utcnow()
        
        if status == 'active':
            query = query.filter(
                PromoCode.is_active == True,
                PromoCode.valid_from <= now,
                PromoCode.valid_until >= now
            )
        elif status == 'expired':
            query = query.filter(PromoCode.valid_until < now)
        elif status == 'upcoming':
            query = query.filter(PromoCode.valid_from > now)
        
        # Apply sorting
        if sort_by == 'valid_from':
            sort_column = PromoCode.valid_from
        elif sort_by == 'valid_until':
            sort_column = PromoCode.valid_until
        elif sort_by == 'used_count':
            sort_column = PromoCode.used_count
        else:
            sort_column = PromoCode.created_at
        
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        promo_codes = query.limit(limit).offset(offset).all()
        
        # Add usage statistics to each promo code
        promo_data = []
        for promo in promo_codes:
            promo_dict = promo.to_dict()
            is_valid, message = promo.is_valid()
            promo_dict['is_currently_valid'] = is_valid
            promo_dict['validity_message'] = message
            
            # Calculate usage percentage
            if promo.usage_limit:
                usage_percentage = (promo.used_count / promo.usage_limit) * 100
                promo_dict['usage_percentage'] = round(usage_percentage, 2)
            else:
                promo_dict['usage_percentage'] = None
            
            promo_data.append(promo_dict)
        
        return jsonify({
            'promo_codes': promo_data,
            'count': len(promo_codes),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get promo codes', 'message': str(e)}), 500


@admin_promos_bp.route('/<int:promo_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_promo_code(promo_id):
    """
    Get detailed promo code information including usage statistics
    """
    try:
        promo_code = PromoCode.query.get(promo_id)
        
        if not promo_code:
            return jsonify({'error': 'Promo code not found'}), 404
        
        promo_dict = promo_code.to_dict()
        
        # Add validation status
        is_valid, message = promo_code.is_valid()
        promo_dict['is_currently_valid'] = is_valid
        promo_dict['validity_message'] = message
        
        # Calculate usage statistics
        if promo_code.usage_limit:
            remaining_uses = promo_code.usage_limit - promo_code.used_count
            usage_percentage = (promo_code.used_count / promo_code.usage_limit) * 100
        else:
            remaining_uses = None
            usage_percentage = None
        
        promo_dict['remaining_uses'] = remaining_uses
        promo_dict['usage_percentage'] = round(usage_percentage, 2) if usage_percentage else None
        
        # Get bookings using this promo code
        from app.models.booking import Booking
        total_bookings = Booking.query.filter_by(promo_code_id=promo_id).count()
        total_discount_given = db.session.query(
            func.sum(Booking.discount_amount)
        ).filter_by(promo_code_id=promo_id).scalar() or 0
        
        promo_dict['usage_statistics'] = {
            'total_bookings': total_bookings,
            'total_discount_given': float(total_discount_given)
        }
        
        return jsonify({
            'promo_code': promo_dict
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get promo code', 'message': str(e)}), 500


@admin_promos_bp.route('/<int:promo_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_promo_code(promo_id):
    """
    Update promo code
    ---
    Allowed fields: description, discount_percentage, max_discount_amount,
                   min_purchase_amount, usage_limit, usage_per_user,
                   valid_from, valid_until, is_active
    Note: Code cannot be changed once created
    """
    try:
        promo_code = PromoCode.query.get(promo_id)
        
        if not promo_code:
            return jsonify({'error': 'Promo code not found'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        updated_fields = []
        
        # Update description
        if 'description' in data:
            promo_code.description = data['description'].strip()
            updated_fields.append('description')
        
        # Update discount percentage
        if 'discount_percentage' in data:
            discount_percentage = float(data['discount_percentage'])
            if discount_percentage <= 0 or discount_percentage > 100:
                return jsonify({'error': 'Discount percentage must be between 0 and 100'}), 400
            promo_code.discount_percentage = discount_percentage
            updated_fields.append('discount_percentage')
        
        # Update max discount amount
        if 'max_discount_amount' in data:
            if data['max_discount_amount'] is None:
                promo_code.max_discount_amount = None
            else:
                max_discount = float(data['max_discount_amount'])
                if max_discount <= 0:
                    return jsonify({'error': 'Max discount amount must be positive'}), 400
                promo_code.max_discount_amount = max_discount
            updated_fields.append('max_discount_amount')
        
        # Update min purchase amount
        if 'min_purchase_amount' in data:
            if data['min_purchase_amount'] is None:
                promo_code.min_purchase_amount = None
            else:
                min_purchase = float(data['min_purchase_amount'])
                if min_purchase < 0:
                    return jsonify({'error': 'Min purchase amount cannot be negative'}), 400
                promo_code.min_purchase_amount = min_purchase
            updated_fields.append('min_purchase_amount')
        
        # Update usage limit
        if 'usage_limit' in data:
            if data['usage_limit'] is None:
                promo_code.usage_limit = None
            else:
                usage_limit = int(data['usage_limit'])
                if usage_limit <= 0:
                    return jsonify({'error': 'Usage limit must be positive'}), 400
                if usage_limit < promo_code.used_count:
                    return jsonify({
                        'error': f'Usage limit cannot be less than current usage ({promo_code.used_count})'
                    }), 400
                promo_code.usage_limit = usage_limit
            updated_fields.append('usage_limit')
        
        # Update usage per user
        if 'usage_per_user' in data:
            if data['usage_per_user'] is None:
                promo_code.usage_per_user = None
            else:
                usage_per_user = int(data['usage_per_user'])
                if usage_per_user <= 0:
                    return jsonify({'error': 'Usage per user must be positive'}), 400
                promo_code.usage_per_user = usage_per_user
            updated_fields.append('usage_per_user')
        
        # Update valid from
        if 'valid_from' in data:
            try:
                promo_code.valid_from = datetime.fromisoformat(data['valid_from'].replace('Z', '+00:00'))
                updated_fields.append('valid_from')
            except ValueError:
                return jsonify({'error': 'Invalid valid_from format'}), 400
        
        # Update valid until
        if 'valid_until' in data:
            try:
                promo_code.valid_until = datetime.fromisoformat(data['valid_until'].replace('Z', '+00:00'))
                updated_fields.append('valid_until')
            except ValueError:
                return jsonify({'error': 'Invalid valid_until format'}), 400
        
        # Validate date range if either date was updated
        if 'valid_from' in updated_fields or 'valid_until' in updated_fields:
            if promo_code.valid_from >= promo_code.valid_until:
                return jsonify({'error': 'valid_until must be after valid_from'}), 400
        
        # Update is_active
        if 'is_active' in data:
            promo_code.is_active = bool(data['is_active'])
            updated_fields.append('is_active')
        
        if not updated_fields:
            return jsonify({'error': 'No valid fields provided for update'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': 'Promo code updated successfully',
            'updated_fields': updated_fields,
            'promo_code': promo_code.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({'error': 'Invalid data type provided', 'message': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update promo code', 'message': str(e)}), 500


@admin_promos_bp.route('/<int:promo_id>/toggle', methods=['PUT'])
@jwt_required()
@admin_required
def toggle_promo_code(promo_id):
    """
    Toggle promo code active status
    """
    try:
        promo_code = PromoCode.query.get(promo_id)
        
        if not promo_code:
            return jsonify({'error': 'Promo code not found'}), 404
        
        promo_code.is_active = not promo_code.is_active
        db.session.commit()
        
        return jsonify({
            'message': f'Promo code {"activated" if promo_code.is_active else "deactivated"} successfully',
            'is_active': promo_code.is_active,
            'promo_code': promo_code.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to toggle promo code', 'message': str(e)}), 500


@admin_promos_bp.route('/<int:promo_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_promo_code(promo_id):
    """
    Delete a promo code
    Note: Bookings that used this promo code will retain their discount,
    but the promo_code_id reference will be removed
    """
    try:
        promo_code = PromoCode.query.get(promo_id)
        
        if not promo_code:
            return jsonify({'error': 'Promo code not found'}), 404
        
        # Check if promo code has been used
        from app.models.booking import Booking
        usage_count = Booking.query.filter_by(promo_code_id=promo_id).count()
        
        if usage_count > 0:
            return jsonify({
                'error': f'Cannot delete promo code that has been used ({usage_count} bookings). Consider deactivating instead.',
                'suggestion': 'Use PUT /admin/promo-codes/{id}/toggle to deactivate'
            }), 409
        
        db.session.delete(promo_code)
        db.session.commit()
        
        return jsonify({
            'message': 'Promo code deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete promo code', 'message': str(e)}), 500


@admin_promos_bp.route('/statistics', methods=['GET'])
@jwt_required()
@admin_required
def get_promo_statistics():
    """
    Get statistics about promo codes
    """
    try:
        now = datetime.utcnow()
        
        # Total promo codes
        total_promos = PromoCode.query.count()
        
        # Active promo codes
        active_promos = PromoCode.query.filter(
            PromoCode.is_active == True,
            PromoCode.valid_from <= now,
            PromoCode.valid_until >= now
        ).count()
        
        # Expired promo codes
        expired_promos = PromoCode.query.filter(
            PromoCode.valid_until < now
        ).count()
        
        # Upcoming promo codes
        upcoming_promos = PromoCode.query.filter(
            PromoCode.valid_from > now
        ).count()
        
        # Total discount given
        from app.models.booking import Booking
        total_discount = db.session.query(
            func.sum(Booking.discount_amount)
        ).filter(Booking.promo_code_id.isnot(None)).scalar() or 0
        
        # Total bookings with promo
        bookings_with_promo = Booking.query.filter(
            Booking.promo_code_id.isnot(None)
        ).count()
        
        # Most used promo codes
        most_used_promos = db.session.query(
            PromoCode.id,
            PromoCode.code,
            PromoCode.description,
            PromoCode.used_count,
            func.sum(Booking.discount_amount).label('total_discount')
        ).outerjoin(Booking).group_by(
            PromoCode.id,
            PromoCode.code,
            PromoCode.description,
            PromoCode.used_count
        ).order_by(PromoCode.used_count.desc()).limit(10).all()
        
        # Average discount per booking
        avg_discount = db.session.query(
            func.avg(Booking.discount_amount)
        ).filter(Booking.promo_code_id.isnot(None)).scalar() or 0
        
        return jsonify({
            'statistics': {
                'total_promo_codes': total_promos,
                'active_promo_codes': active_promos,
                'expired_promo_codes': expired_promos,
                'upcoming_promo_codes': upcoming_promos,
                'total_discount_given': float(total_discount),
                'bookings_with_promo': bookings_with_promo,
                'average_discount_per_booking': float(avg_discount),
                'most_used_promo_codes': [
                    {
                        'id': promo[0],
                        'code': promo[1],
                        'description': promo[2],
                        'used_count': promo[3],
                        'total_discount': float(promo[4]) if promo[4] else 0
                    }
                    for promo in most_used_promos
                ]
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get statistics', 'message': str(e)}), 500


@admin_promos_bp.route('/<int:promo_id>/usage', methods=['GET'])
@jwt_required()
@admin_required
def get_promo_usage(promo_id):
    """
    Get detailed usage information for a specific promo code
    ---
    Query parameters:
    - limit: Number of results (default: 50)
    - offset: Pagination offset (default: 0)
    """
    try:
        promo_code = PromoCode.query.get(promo_id)
        
        if not promo_code:
            return jsonify({'error': 'Promo code not found'}), 404
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Get bookings using this promo code
        from app.models.booking import Booking
        query = Booking.query.filter_by(promo_code_id=promo_id).order_by(
            Booking.created_at.desc()
        )
        
        total_count = query.count()
        bookings = query.limit(limit).offset(offset).all()
        
        # Calculate statistics
        total_discount = db.session.query(
            func.sum(Booking.discount_amount)
        ).filter_by(promo_code_id=promo_id).scalar() or 0
        
        total_revenue = db.session.query(
            func.sum(Booking.total_amount)
        ).filter_by(promo_code_id=promo_id).scalar() or 0
        
        return jsonify({
            'promo_code': {
                'id': promo_code.id,
                'code': promo_code.code,
                'description': promo_code.description
            },
            'usage': {
                'total_uses': total_count,
                'total_discount_given': float(total_discount),
                'total_revenue_generated': float(total_revenue),
                'bookings': [
                    {
                        'booking_id': booking.id,
                        'booking_reference': booking.booking_reference,
                        'user_id': booking.user_id,
                        'username': booking.user.username,
                        'booking_date': booking.created_at.isoformat(),
                        'subtotal': float(booking.subtotal),
                        'discount': float(booking.discount_amount),
                        'total': float(booking.total_amount),
                        'booking_status': booking.booking_status.value,
                        'payment_status': booking.payment_status.value
                    }
                    for booking in bookings
                ]
            },
            'count': len(bookings),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get promo usage', 'message': str(e)}), 500

