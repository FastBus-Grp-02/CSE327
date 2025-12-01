from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.booking import Booking, BookingStatus, PaymentStatus
from app.models.trip import Trip, Seat, SeatStatus
from app.models.user import User
from app.utils.decorators import admin_required
from datetime import datetime
from sqlalchemy import func, desc

admin_bookings_bp = Blueprint('admin_bookings', __name__)


@admin_bookings_bp.route('/', methods=['GET'])
@jwt_required()
@admin_required
def get_all_bookings():
    """
    Get all bookings with filtering and pagination
    ---
    Query parameters:
    - booking_status: Filter by booking status
    - payment_status: Filter by payment status
    - user_id: Filter by user
    - trip_id: Filter by trip
    - date_from: Filter from date (YYYY-MM-DD)
    - date_to: Filter to date (YYYY-MM-DD)
    - search: Search by booking reference or passenger name
    - limit: Number of results (default: 50)
    - offset: Pagination offset (default: 0)
    - sort_by: Sort field (created_at, total_amount, departure_time)
    - sort_order: Sort order (asc, desc)
    """
    try:
        # Get query parameters
        booking_status = request.args.get('booking_status', '').lower()
        payment_status = request.args.get('payment_status', '').lower()
        user_id = request.args.get('user_id', type=int)
        trip_id = request.args.get('trip_id', type=int)
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        search = request.args.get('search', '').strip()
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        sort_by = request.args.get('sort_by', 'created_at').lower()
        sort_order = request.args.get('sort_order', 'desc').lower()
        
        # Build query
        query = Booking.query
        
        # Apply filters
        if booking_status:
            try:
                status = BookingStatus(booking_status)
                query = query.filter_by(booking_status=status)
            except ValueError:
                return jsonify({'error': 'Invalid booking status'}), 400
        
        if payment_status:
            try:
                status = PaymentStatus(payment_status)
                query = query.filter_by(payment_status=status)
            except ValueError:
                return jsonify({'error': 'Invalid payment status'}), 400
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        if trip_id:
            query = query.filter_by(trip_id=trip_id)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Booking.created_at >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format. Use YYYY-MM-DD'}), 400
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(Booking.created_at <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format. Use YYYY-MM-DD'}), 400
        
        if search:
            query = query.filter(
                (Booking.booking_reference.ilike(f'%{search}%')) |
                (Booking.passenger_name.ilike(f'%{search}%')) |
                (Booking.passenger_email.ilike(f'%{search}%'))
            )
        
        # Apply sorting
        if sort_by == 'total_amount':
            sort_column = Booking.total_amount
        elif sort_by == 'departure_time':
            query = query.join(Booking.trip)
            sort_column = Trip.departure_time
        else:
            sort_column = Booking.created_at
        
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        bookings = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'bookings': [booking.to_dict(include_relationships=True) for booking in bookings],
            'count': len(bookings),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get bookings', 'message': str(e)}), 500


@admin_bookings_bp.route('/<int:booking_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_booking(booking_id):
    """
    Get detailed booking information
    """
    try:
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Include user details
        booking_data = booking.to_dict(include_relationships=True)
        booking_data['user'] = booking.user.to_dict()
        
        return jsonify({
            'booking': booking_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get booking', 'message': str(e)}), 500


@admin_bookings_bp.route('/<int:booking_id>/status', methods=['PUT'])
@jwt_required()
@admin_required
def update_booking_status(booking_id):
    """
    Update booking status
    ---
    Request body:
    {
        "booking_status": "pending|confirmed|cancelled|completed"
    }
    """
    try:
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        data = request.get_json()
        
        if not data or 'booking_status' not in data:
            return jsonify({'error': 'booking_status is required'}), 400
        
        try:
            new_status = BookingStatus(data['booking_status'].lower())
        except ValueError:
            return jsonify({'error': 'Invalid booking status'}), 400
        
        old_status = booking.booking_status
        
        # Handle status transitions
        if new_status == BookingStatus.CANCELLED and old_status != BookingStatus.CANCELLED:
            # Free up seats
            for seat in booking.seats:
                seat.status = SeatStatus.AVAILABLE
                seat.booking_id = None
            
            # Update trip available seats
            booking.trip.available_seats += booking.num_seats
            
            # Update payment status if needed
            if booking.payment_status == PaymentStatus.PAID:
                booking.payment_status = PaymentStatus.REFUNDED
        
        elif old_status == BookingStatus.CANCELLED and new_status != BookingStatus.CANCELLED:
            # Re-book seats if moving from cancelled
            # Check if seats are still available
            seat_ids = [seat.id for seat in booking.seats]
            available_seats = Seat.query.filter(
                Seat.id.in_(seat_ids),
                Seat.status == SeatStatus.AVAILABLE
            ).count()
            
            if available_seats != len(seat_ids):
                return jsonify({
                    'error': 'Some seats are no longer available'
                }), 409
            
            # Re-book seats
            for seat in booking.seats:
                seat.status = SeatStatus.BOOKED
                seat.booking_id = booking.id
            
            # Update trip available seats
            booking.trip.available_seats -= booking.num_seats
        
        booking.booking_status = new_status
        db.session.commit()
        
        return jsonify({
            'message': 'Booking status updated successfully',
            'old_status': old_status.value,
            'new_status': new_status.value,
            'booking': booking.to_dict(include_relationships=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update booking status', 'message': str(e)}), 500


@admin_bookings_bp.route('/<int:booking_id>/payment', methods=['PUT'])
@jwt_required()
@admin_required
def update_payment_status(booking_id):
    """
    Update payment status
    ---
    Request body:
    {
        "payment_status": "unpaid|paid|refunded|failed"
    }
    """
    try:
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        data = request.get_json()
        
        if not data or 'payment_status' not in data:
            return jsonify({'error': 'payment_status is required'}), 400
        
        try:
            new_status = PaymentStatus(data['payment_status'].lower())
        except ValueError:
            return jsonify({'error': 'Invalid payment status'}), 400
        
        old_status = booking.payment_status
        booking.payment_status = new_status
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment status updated successfully',
            'old_status': old_status.value,
            'new_status': new_status.value,
            'booking': booking.to_dict(include_relationships=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update payment status', 'message': str(e)}), 500


@admin_bookings_bp.route('/<int:booking_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_booking(booking_id):
    """
    Delete a booking (use with caution)
    """
    try:
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Free up seats if booking was not cancelled
        if booking.booking_status != BookingStatus.CANCELLED:
            for seat in booking.seats:
                seat.status = SeatStatus.AVAILABLE
                seat.booking_id = None
            
            # Update trip available seats
            booking.trip.available_seats += booking.num_seats
        
        db.session.delete(booking)
        db.session.commit()
        
        return jsonify({
            'message': 'Booking deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete booking', 'message': str(e)}), 500


@admin_bookings_bp.route('/statistics', methods=['GET'])
@jwt_required()
@admin_required
def get_booking_statistics():
    """
    Get statistics about bookings
    ---
    Query parameters:
    - date_from: Filter from date (YYYY-MM-DD)
    - date_to: Filter to date (YYYY-MM-DD)
    """
    try:
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        
        # Build base query
        query = Booking.query
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Booking.created_at >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format'}), 400
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(Booking.created_at <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format'}), 400
        
        # Total bookings
        total_bookings = query.count()
        
        # Bookings by status
        bookings_by_status = {}
        for status in BookingStatus:
            count = query.filter_by(booking_status=status).count()
            bookings_by_status[status.value] = count
        
        # Bookings by payment status
        bookings_by_payment = {}
        for status in PaymentStatus:
            count = query.filter_by(payment_status=status).count()
            bookings_by_payment[status.value] = count
        
        # Total revenue (paid bookings)
        revenue_query = query.filter_by(payment_status=PaymentStatus.PAID)
        total_revenue = db.session.query(
            func.sum(Booking.total_amount)
        ).filter(
            Booking.id.in_([b.id for b in revenue_query.all()])
        ).scalar() or 0
        
        # Average booking value
        avg_booking_value = db.session.query(
            func.avg(Booking.total_amount)
        ).filter(
            Booking.id.in_([b.id for b in query.all()])
        ).scalar() or 0
        
        # Total seats booked
        total_seats = db.session.query(
            func.sum(Booking.num_seats)
        ).filter(
            Booking.id.in_([b.id for b in query.all()])
        ).scalar() or 0
        
        # Top customers
        top_customers = db.session.query(
            Booking.user_id,
            User.username,
            User.email,
            func.count(Booking.id).label('booking_count'),
            func.sum(Booking.total_amount).label('total_spent')
        ).join(User).filter(
            Booking.id.in_([b.id for b in query.all()])
        ).group_by(Booking.user_id, User.username, User.email).order_by(
            desc('total_spent')
        ).limit(10).all()
        
        # Discount usage
        total_discount = db.session.query(
            func.sum(Booking.discount_amount)
        ).filter(
            Booking.id.in_([b.id for b in query.all()])
        ).scalar() or 0
        
        bookings_with_promo = query.filter(Booking.promo_code_id.isnot(None)).count()
        
        return jsonify({
            'statistics': {
                'total_bookings': total_bookings,
                'bookings_by_status': bookings_by_status,
                'bookings_by_payment': bookings_by_payment,
                'total_revenue': float(total_revenue),
                'average_booking_value': float(avg_booking_value),
                'total_seats_booked': int(total_seats),
                'total_discount_given': float(total_discount),
                'bookings_with_promo': bookings_with_promo,
                'promo_usage_rate': round((bookings_with_promo / total_bookings * 100), 2) if total_bookings > 0 else 0,
                'top_customers': [
                    {
                        'user_id': customer[0],
                        'username': customer[1],
                        'email': customer[2],
                        'booking_count': customer[3],
                        'total_spent': float(customer[4]) if customer[4] else 0
                    }
                    for customer in top_customers
                ]
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get statistics', 'message': str(e)}), 500


@admin_bookings_bp.route('/export', methods=['GET'])
@jwt_required()
@admin_required
def export_bookings():
    """
    Export bookings data (returns simplified data for CSV export)
    ---
    Query parameters: Same as get_all_bookings
    """
    try:
        # Get query parameters (reuse filtering logic)
        booking_status = request.args.get('booking_status', '').lower()
        payment_status = request.args.get('payment_status', '').lower()
        user_id = request.args.get('user_id', type=int)
        trip_id = request.args.get('trip_id', type=int)
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        
        # Build query
        query = Booking.query
        
        # Apply filters (same as get_all_bookings)
        if booking_status:
            try:
                status = BookingStatus(booking_status)
                query = query.filter_by(booking_status=status)
            except ValueError:
                return jsonify({'error': 'Invalid booking status'}), 400
        
        if payment_status:
            try:
                status = PaymentStatus(payment_status)
                query = query.filter_by(payment_status=status)
            except ValueError:
                return jsonify({'error': 'Invalid payment status'}), 400
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        if trip_id:
            query = query.filter_by(trip_id=trip_id)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Booking.created_at >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format'}), 400
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(Booking.created_at <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format'}), 400
        
        bookings = query.order_by(Booking.created_at.desc()).limit(1000).all()
        
        # Prepare export data
        export_data = []
        for booking in bookings:
            export_data.append({
                'booking_reference': booking.booking_reference,
                'booking_date': booking.created_at.strftime('%Y-%m-%d %H:%M:%S'),
                'passenger_name': booking.passenger_name,
                'passenger_email': booking.passenger_email,
                'passenger_phone': booking.passenger_phone,
                'trip_number': booking.trip.trip_number,
                'origin': booking.trip.origin,
                'destination': booking.trip.destination,
                'departure_time': booking.trip.departure_time.strftime('%Y-%m-%d %H:%M:%S'),
                'num_seats': booking.num_seats,
                'seat_numbers': ', '.join([seat.seat_number for seat in booking.seats]),
                'subtotal': float(booking.subtotal),
                'discount': float(booking.discount_amount),
                'total': float(booking.total_amount),
                'promo_code': booking.promo_code.code if booking.promo_code else '',
                'booking_status': booking.booking_status.value,
                'payment_status': booking.payment_status.value,
                'username': booking.user.username
            })
        
        return jsonify({
            'bookings': export_data,
            'count': len(export_data),
            'note': 'Limited to 1000 most recent bookings'
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to export bookings', 'message': str(e)}), 500

