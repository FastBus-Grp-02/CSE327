from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.trip import Trip, Seat, SeatStatus, TripStatus
from app.models.booking import Booking, PromoCode, BookingStatus, PaymentStatus
from app.models.user import User
from app.utils.validators import validate_required_fields, validate_email, validate_phone_number, validate_seat_selection
from datetime import datetime

bookings_bp = Blueprint('bookings', __name__)


@bookings_bp.route('/', methods=['OPTIONS'])
def handle_options():
    """Handle OPTIONS preflight request for CORS"""
    return '', 204


@bookings_bp.route('/', methods=['POST'])
@jwt_required()
def create_booking():
    """
    Create a new booking
    ---
    Request body:
    {
        "trip_id": int,
        "seat_ids": [int, ...],
        "passenger_name": "string",
        "passenger_email": "string",
        "passenger_phone": "string",
        "promo_code": "string" (optional),
        "special_requests": "string" (optional)
    }
    """
    try:
        current_user_id = int(get_jwt_identity())
        user = User.query.get(current_user_id)
        
        if not user or not user.is_active:
            return jsonify({'error': 'User account not found or inactive'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['trip_id', 'seat_ids', 'passenger_name', 'passenger_email', 'passenger_phone']
        is_valid, message = validate_required_fields(data, required_fields)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Extract data
        trip_id = data['trip_id']
        seat_ids = data['seat_ids']
        passenger_name = data['passenger_name'].strip()
        passenger_email = data['passenger_email'].lower().strip()
        passenger_phone = data['passenger_phone'].strip()
        promo_code_str = (data.get('promo_code') or '').strip().upper()
        special_requests = (data.get('special_requests') or '').strip()
        
        # Validate seat selection
        is_valid, message = validate_seat_selection(seat_ids)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Validate passenger email
        if not validate_email(passenger_email):
            return jsonify({'error': 'Invalid passenger email format'}), 400
        
        # Validate passenger phone
        is_valid, message = validate_phone_number(passenger_phone)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Validate passenger name
        if len(passenger_name) < 2 or len(passenger_name) > 200:
            return jsonify({'error': 'Passenger name must be between 2 and 200 characters'}), 400
        
        # Get trip
        trip = Trip.query.get(trip_id)
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404
        
        # Check if trip is bookable
        if trip.status != TripStatus.SCHEDULED:
            return jsonify({'error': f'Trip is not available for booking. Status: {trip.status.value}'}), 400
        
        # Check if trip is in the past
        if trip.departure_time < datetime.utcnow():
            return jsonify({'error': 'Cannot book trips in the past'}), 400
        
        # Get and validate seats
        seats = Seat.query.filter(
            Seat.id.in_(seat_ids),
            Seat.trip_id == trip_id
        ).all()
        
        if len(seats) != len(seat_ids):
            # Find which seats are missing
            found_seat_ids = [s.id for s in seats]
            missing_seat_ids = [sid for sid in seat_ids if sid not in found_seat_ids]
            return jsonify({
                'error': 'One or more seats not found or invalid',
                'missing_seat_ids': missing_seat_ids,
                'trip_id': trip_id
            }), 404
        
        # Check if all seats are available
        unavailable_seats = []
        for seat in seats:
            if seat.status != SeatStatus.AVAILABLE:
                unavailable_seats.append({
                    'seat_number': seat.seat_number,
                    'status': seat.status.value
                })
        
        if unavailable_seats:
            return jsonify({
                'error': 'Some seats are not available',
                'unavailable_seats': unavailable_seats
            }), 409
        
        # Check if enough seats available on trip
        if trip.available_seats < len(seat_ids):
            return jsonify({'error': 'Not enough seats available on this trip'}), 409
        
        # Calculate subtotal
        subtotal = sum(seat.calculate_price() for seat in seats)
        subtotal = round(subtotal, 2)
        
        # Initialize discount and promo code
        discount_amount = 0.0
        promo_code = None
        
        # Apply promo code if provided
        if promo_code_str:
            promo_code = PromoCode.query.filter_by(code=promo_code_str).first()
            
            if not promo_code:
                return jsonify({'error': 'Invalid promo code'}), 400
            
            # Validate promo code
            is_valid, validation_message = promo_code.is_valid()
            if not is_valid:
                return jsonify({'error': validation_message}), 400
            
            # Check user eligibility
            is_eligible, eligibility_message = promo_code.check_user_eligibility(current_user_id)
            if not is_eligible:
                return jsonify({'error': eligibility_message}), 400
            
            # Check minimum purchase amount
            if promo_code.min_purchase_amount and subtotal < promo_code.min_purchase_amount:
                return jsonify({
                    'error': f'Minimum purchase amount of {float(promo_code.min_purchase_amount)} required for this promo code'
                }), 400
            
            # Calculate discount
            discount_amount = promo_code.calculate_discount(subtotal)
        
        # Calculate total
        total_amount = round(subtotal - discount_amount, 2)
        
        # Create booking
        booking = Booking(
            booking_reference=Booking.generate_booking_reference(),
            user_id=current_user_id,
            trip_id=trip_id,
            promo_code_id=promo_code.id if promo_code else None,
            passenger_name=passenger_name,
            passenger_email=passenger_email,
            passenger_phone=passenger_phone,
            subtotal=subtotal,
            discount_amount=discount_amount,
            total_amount=total_amount,
            booking_status=BookingStatus.CONFIRMED,
            payment_status=PaymentStatus.UNPAID,
            num_seats=len(seat_ids),
            special_requests=special_requests if special_requests else None
        )
        
        db.session.add(booking)
        db.session.flush()  # Get booking ID
        
        # Update seats
        for seat in seats:
            seat.status = SeatStatus.BOOKED
            seat.booking_id = booking.id
        
        # Update trip available seats
        trip.available_seats -= len(seat_ids)
        
        # Update promo code usage if applied
        if promo_code:
            promo_code.used_count += 1
        
        db.session.commit()
        
        return jsonify({
            'message': 'Booking created successfully',
            'booking': booking.to_dict(include_relationships=True)
        }), 201
        
    except Exception as e:
        db.session.rollback()
        import traceback
        error_trace = traceback.format_exc()
        print(f"Error creating booking: {error_trace}")
        return jsonify({'error': 'Failed to create booking', 'message': str(e)}), 500


@bookings_bp.route('/', methods=['GET'])
@jwt_required()
def get_user_bookings():
    """
    Get all bookings for the current user
    ---
    Query parameters:
    - status: Filter by booking status (optional)
    - limit: Number of results to return (default: 50)
    - offset: Number of results to skip (default: 0)
    """
    try:
        current_user_id = int(get_jwt_identity())
        
        # Get query parameters
        status = request.args.get('status', '').lower()
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        # Validate limit and offset
        if limit < 1 or limit > 100:
            return jsonify({'error': 'Limit must be between 1 and 100'}), 400
        
        if offset < 0:
            return jsonify({'error': 'Offset must be non-negative'}), 400
        
        # Build query
        query = Booking.query.filter_by(user_id=current_user_id)
        
        # Filter by status if provided
        if status:
            try:
                booking_status = BookingStatus(status)
                query = query.filter_by(booking_status=booking_status)
            except ValueError:
                return jsonify({'error': 'Invalid booking status'}), 400
        
        # Order by creation date (newest first)
        query = query.order_by(Booking.created_at.desc())
        
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


@bookings_bp.route('/<int:booking_id>', methods=['GET'])
@jwt_required()
def get_booking_details(booking_id):
    """
    Get details of a specific booking
    ---
    Path parameters:
    - booking_id: ID of the booking
    """
    try:
        current_user_id = int(get_jwt_identity())
        
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Check if user owns this booking
        if booking.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized access to this booking'}), 403
        
        return jsonify({
            'booking': booking.to_dict(include_relationships=True)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get booking details', 'message': str(e)}), 500


@bookings_bp.route('/reference/<string:booking_reference>', methods=['GET'])
@jwt_required()
def get_booking_by_reference(booking_reference):
    """
    Get booking details by booking reference
    ---
    Path parameters:
    - booking_reference: Booking reference code
    """
    try:
        current_user_id = int(get_jwt_identity())
        
        booking = Booking.query.filter_by(booking_reference=booking_reference.upper()).first()
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Check if user owns this booking
        if booking.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized access to this booking'}), 403
        
        return jsonify({
            'booking': booking.to_dict(include_relationships=True)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get booking details', 'message': str(e)}), 500


@bookings_bp.route('/<int:booking_id>/cancel', methods=['PUT'])
@jwt_required()
def cancel_booking(booking_id):
    """
    Cancel a booking
    ---
    Path parameters:
    - booking_id: ID of the booking
    """
    try:
        current_user_id = int(get_jwt_identity())
        
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Check if user owns this booking
        if booking.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized access to this booking'}), 403
        
        # Check if booking is already cancelled
        if booking.booking_status == BookingStatus.CANCELLED:
            return jsonify({'error': 'Booking is already cancelled'}), 400
        
        # Check if booking is completed
        if booking.booking_status == BookingStatus.COMPLETED:
            return jsonify({'error': 'Cannot cancel a completed booking'}), 400
        
        # Check if trip has already departed
        if booking.trip.departure_time < datetime.utcnow():
            return jsonify({'error': 'Cannot cancel booking for a trip that has already departed'}), 400
        
        # Cancel booking
        booking.booking_status = BookingStatus.CANCELLED
        
        # Free up seats
        for seat in booking.seats:
            seat.status = SeatStatus.AVAILABLE
            seat.booking_id = None
        
        # Update trip available seats
        booking.trip.available_seats += booking.num_seats
        
        # Update payment status
        if booking.payment_status == PaymentStatus.PAID:
            booking.payment_status = PaymentStatus.REFUNDED
        
        # Decrease promo code usage count if applicable
        if booking.promo_code_id:
            promo_code = PromoCode.query.get(booking.promo_code_id)
            if promo_code:
                promo_code.used_count = max(0, promo_code.used_count - 1)
        
        db.session.commit()
        
        return jsonify({
            'message': 'Booking cancelled successfully',
            'booking': booking.to_dict(include_relationships=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to cancel booking', 'message': str(e)}), 500


@bookings_bp.route('/<int:booking_id>/payment', methods=['PUT'])
@jwt_required()
def update_payment_status(booking_id):
    """
    Update payment status for a booking
    ---
    Path parameters:
    - booking_id: ID of the booking
    
    Request body:
    {
        "payment_status": "paid" | "failed"
    }
    """
    try:
        current_user_id = int(get_jwt_identity())
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        payment_status_str = data.get('payment_status', '').lower()
        
        if not payment_status_str:
            return jsonify({'error': 'payment_status is required'}), 400
        
        # Validate payment status
        if payment_status_str not in ['paid', 'failed']:
            return jsonify({'error': 'payment_status must be either "paid" or "failed"'}), 400
        
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Check if user owns this booking
        if booking.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized access to this booking'}), 403
        
        # Check if booking is cancelled
        if booking.booking_status == BookingStatus.CANCELLED:
            return jsonify({'error': 'Cannot update payment for a cancelled booking'}), 400
        
        # Update payment status
        if payment_status_str == 'paid':
            booking.payment_status = PaymentStatus.PAID
        else:
            booking.payment_status = PaymentStatus.FAILED
        
        db.session.commit()
        
        return jsonify({
            'message': 'Payment status updated successfully',
            'booking': booking.to_dict(include_relationships=True)
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update payment status', 'message': str(e)}), 500

