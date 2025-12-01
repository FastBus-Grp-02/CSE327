from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.trip import Trip, Seat, TripStatus, SeatStatus
from app.models.booking import PromoCode
from datetime import datetime, timedelta
from sqlalchemy import and_, or_

trips_bp = Blueprint('trips', __name__)


@trips_bp.route('/cities', methods=['GET'])
def get_cities():
    """
    Get list of unique cities (origins and destinations) from trips
    ---
    Query parameters:
    - search: Optional search term to filter cities (case-insensitive)
    """
    try:
        search_term = request.args.get('search', '').strip()
        
        # Get distinct origins and destinations
        origins = db.session.query(Trip.origin).distinct().all()
        destinations = db.session.query(Trip.destination).distinct().all()
        
        # Combine and deduplicate
        cities_set = set()
        for (origin,) in origins:
            if origin:
                cities_set.add(origin.strip())
        for (destination,) in destinations:
            if destination:
                cities_set.add(destination.strip())
        
        # Convert to sorted list
        cities = sorted(list(cities_set))
        
        # Filter by search term if provided
        if search_term:
            cities = [city for city in cities if search_term.lower() in city.lower()]
        
        return jsonify({
            'cities': cities,
            'count': len(cities)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get cities', 'message': str(e)}), 500


@trips_bp.route('/search', methods=['GET'])
def search_trips():
    """
    Search for available trips
    ---
    Query parameters:
    - origin (required): Starting location
    - destination (required): Destination location
    - date (required): Travel date (YYYY-MM-DD)
    - seats: Number of seats needed (default: 1)
    - seat_class: Seat class filter (economy, business, first_class)
    - sort_by: Sort criteria (price, departure_time, duration)
    - sort_order: Sort order (asc, desc)
    """
    try:
        # Get query parameters
        origin = request.args.get('origin', '').strip()
        destination = request.args.get('destination', '').strip()
        travel_date = request.args.get('date', '').strip()
        seats_needed = request.args.get('seats', 1, type=int)
        seat_class = request.args.get('seat_class', '').lower()
        sort_by = request.args.get('sort_by', 'departure_time').lower()
        sort_order = request.args.get('sort_order', 'asc').lower()
        
        # Validate required parameters
        if not origin:
            return jsonify({'error': 'Origin is required'}), 400
        
        if not destination:
            return jsonify({'error': 'Destination is required'}), 400
        
        if not travel_date:
            return jsonify({'error': 'Travel date is required'}), 400
        
        # Parse and validate date
        try:
            date_obj = datetime.strptime(travel_date, '%Y-%m-%d')
            start_datetime = date_obj.replace(hour=0, minute=0, second=0)
            end_datetime = date_obj.replace(hour=23, minute=59, second=59)
        except ValueError:
            return jsonify({'error': 'Invalid date format. Use YYYY-MM-DD'}), 400
        
        # Validate seats_needed
        if seats_needed < 1:
            return jsonify({'error': 'Number of seats must be at least 1'}), 400
        
        # Build query
        query = Trip.query.filter(
            Trip.origin.ilike(f'%{origin}%'),
            Trip.destination.ilike(f'%{destination}%'),
            Trip.departure_time >= start_datetime,
            Trip.departure_time <= end_datetime,
            Trip.status == TripStatus.SCHEDULED,
            Trip.available_seats >= seats_needed
        )
        
        # Apply sorting
        if sort_by == 'price':
            if sort_order == 'desc':
                query = query.order_by(Trip.base_fare.desc())
            else:
                query = query.order_by(Trip.base_fare.asc())
        elif sort_by == 'duration':
            if sort_order == 'desc':
                query = query.order_by(Trip.duration_minutes.desc())
            else:
                query = query.order_by(Trip.duration_minutes.asc())
        else:  # Default: departure_time
            if sort_order == 'desc':
                query = query.order_by(Trip.departure_time.desc())
            else:
                query = query.order_by(Trip.departure_time.asc())
        
        trips = query.all()
        
        # Format results
        results = []
        for trip in trips:
            trip_data = trip.to_dict(include_seats=False)
            
            # Calculate estimated fare for requested seats
            estimated_fare = float(trip.base_fare) * seats_needed
            trip_data['estimated_fare'] = round(estimated_fare, 2)
            
            results.append(trip_data)
        
        return jsonify({
            'trips': results,
            'count': len(results),
            'search_criteria': {
                'origin': origin,
                'destination': destination,
                'date': travel_date,
                'seats': seats_needed
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to search trips', 'message': str(e)}), 500


@trips_bp.route('/<int:trip_id>', methods=['GET'])
def get_trip_details(trip_id):
    """
    Get detailed trip information including available seats
    ---
    Path parameters:
    - trip_id: ID of the trip
    """
    try:
        trip = Trip.query.get(trip_id)
        
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404
        
        # Get trip data with seats
        trip_data = trip.to_dict(include_seats=True)
        
        # Group seats by class
        seats_by_class = {}
        for seat in trip.seats.all():
            seat_class = seat.seat_class.value
            if seat_class not in seats_by_class:
                seats_by_class[seat_class] = {
                    'available': 0,
                    'booked': 0,
                    'blocked': 0,
                    'total': 0,
                    'base_price': float(trip.base_fare),
                    'seats': []
                }
            
            seats_by_class[seat_class]['total'] += 1
            seats_by_class[seat_class]['seats'].append(seat.to_dict())
            
            if seat.status == SeatStatus.AVAILABLE:
                seats_by_class[seat_class]['available'] += 1
            elif seat.status == SeatStatus.BOOKED:
                seats_by_class[seat_class]['booked'] += 1
            elif seat.status == SeatStatus.BLOCKED:
                seats_by_class[seat_class]['blocked'] += 1
        
        trip_data['seats_by_class'] = seats_by_class
        
        return jsonify({
            'trip': trip_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get trip details', 'message': str(e)}), 500


@trips_bp.route('/<int:trip_id>/seats/available', methods=['GET'])
def get_available_seats(trip_id):
    """
    Get available seats for a specific trip
    ---
    Path parameters:
    - trip_id: ID of the trip
    
    Query parameters:
    - seat_class: Filter by seat class (optional)
    """
    try:
        trip = Trip.query.get(trip_id)
        
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404
        
        # Build query for available seats
        query = Seat.query.filter_by(
            trip_id=trip_id,
            status=SeatStatus.AVAILABLE
        )
        
        # Filter by seat class if provided
        seat_class = request.args.get('seat_class', '').lower()
        if seat_class:
            from app.models.trip import SeatClass
            try:
                seat_class_enum = SeatClass(seat_class)
                query = query.filter_by(seat_class=seat_class_enum)
            except ValueError:
                return jsonify({'error': 'Invalid seat class'}), 400
        
        available_seats = query.all()
        
        return jsonify({
            'trip_id': trip_id,
            'available_seats': [seat.to_dict() for seat in available_seats],
            'count': len(available_seats)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get available seats', 'message': str(e)}), 500


@trips_bp.route('/fare/calculate', methods=['POST'])
def calculate_fare():
    """
    Calculate fare for selected trip and seats
    ---
    Request body:
    {
        "trip_id": int,
        "seat_ids": [int, ...],
        "promo_code": "string" (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        trip_id = data.get('trip_id')
        seat_ids = data.get('seat_ids', [])
        promo_code_str = data.get('promo_code', '').strip().upper()
        
        if not trip_id:
            return jsonify({'error': 'trip_id is required'}), 400
        
        if not seat_ids or not isinstance(seat_ids, list):
            return jsonify({'error': 'seat_ids must be a non-empty list'}), 400
        
        # Get trip
        trip = Trip.query.get(trip_id)
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404
        
        # Get seats
        seats = Seat.query.filter(
            Seat.id.in_(seat_ids),
            Seat.trip_id == trip_id
        ).all()
        
        if len(seats) != len(seat_ids):
            return jsonify({'error': 'One or more seats not found or invalid'}), 404
        
        # Check if all seats are available
        unavailable_seats = [s.seat_number for s in seats if s.status != SeatStatus.AVAILABLE]
        if unavailable_seats:
            return jsonify({
                'error': 'Some seats are not available',
                'unavailable_seats': unavailable_seats
            }), 409
        
        # Calculate subtotal
        subtotal = 0.0
        seat_details = []
        
        for seat in seats:
            seat_price = seat.calculate_price()
            subtotal += seat_price
            seat_details.append({
                'seat_id': seat.id,
                'seat_number': seat.seat_number,
                'seat_class': seat.seat_class.value,
                'price': seat_price
            })
        
        subtotal = round(subtotal, 2)
        
        # Initialize discount variables
        discount_amount = 0.0
        promo_code_info = None
        
        # Apply promo code if provided
        if promo_code_str:
            promo_code = PromoCode.query.filter_by(code=promo_code_str).first()
            
            if not promo_code:
                return jsonify({'error': 'Invalid promo code'}), 400
            
            # Validate promo code
            is_valid, message = promo_code.is_valid()
            if not is_valid:
                return jsonify({'error': message}), 400
            
            # Check minimum purchase amount
            if promo_code.min_purchase_amount and subtotal < promo_code.min_purchase_amount:
                return jsonify({
                    'error': f'Minimum purchase amount of {float(promo_code.min_purchase_amount)} required for this promo code'
                }), 400
            
            # Calculate discount
            discount_amount = promo_code.calculate_discount(subtotal)
            
            promo_code_info = {
                'code': promo_code.code,
                'description': promo_code.description,
                'discount_percentage': float(promo_code.discount_percentage),
                'discount_amount': discount_amount
            }
        
        # Calculate total
        total_amount = round(subtotal - discount_amount, 2)
        
        return jsonify({
            'trip': trip.to_dict(include_seats=False),
            'seats': seat_details,
            'num_seats': len(seats),
            'subtotal': subtotal,
            'discount_amount': discount_amount,
            'total_amount': total_amount,
            'promo_code': promo_code_info,
            'breakdown': {
                'base_fare': float(trip.base_fare),
                'seats_selected': len(seats),
                'subtotal': subtotal,
                'discount': discount_amount,
                'total': total_amount
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to calculate fare', 'message': str(e)}), 500


@trips_bp.route('/promo-codes/validate', methods=['POST'])
@jwt_required()
def validate_promo_code():
    """
    Validate a promo code for the current user
    ---
    Request body:
    {
        "code": "string",
        "amount": float (optional - for checking min purchase requirement)
    }
    """
    try:
        current_user_id = int(get_jwt_identity())
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        code = data.get('code', '').strip().upper()
        amount = data.get('amount', 0.0)
        
        if not code:
            return jsonify({'error': 'Promo code is required'}), 400
        
        # Find promo code
        promo_code = PromoCode.query.filter_by(code=code).first()
        
        if not promo_code:
            return jsonify({'error': 'Invalid promo code'}), 404
        
        # Check if promo code is valid
        is_valid, message = promo_code.is_valid()
        if not is_valid:
            return jsonify({'error': message, 'valid': False}), 400
        
        # Check user eligibility
        is_eligible, eligibility_message = promo_code.check_user_eligibility(current_user_id)
        if not is_eligible:
            return jsonify({'error': eligibility_message, 'valid': False}), 400
        
        # Check minimum purchase amount if amount provided
        discount_amount = 0.0
        if amount > 0:
            if promo_code.min_purchase_amount and amount < promo_code.min_purchase_amount:
                return jsonify({
                    'error': f'Minimum purchase amount of {float(promo_code.min_purchase_amount)} required',
                    'valid': False,
                    'min_purchase_amount': float(promo_code.min_purchase_amount)
                }), 400
            
            discount_amount = promo_code.calculate_discount(amount)
        
        return jsonify({
            'valid': True,
            'message': 'Promo code is valid',
            'promo_code': {
                'code': promo_code.code,
                'description': promo_code.description,
                'discount_percentage': float(promo_code.discount_percentage),
                'max_discount_amount': float(promo_code.max_discount_amount) if promo_code.max_discount_amount else None,
                'min_purchase_amount': float(promo_code.min_purchase_amount) if promo_code.min_purchase_amount else None,
                'valid_until': promo_code.valid_until.isoformat(),
                'discount_amount': discount_amount if amount > 0 else None
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to validate promo code', 'message': str(e)}), 500


@trips_bp.route('/promo-codes', methods=['GET'])
def get_active_promo_codes():
    """
    Get all currently active promo codes
    ---
    Public endpoint to view available promotions
    """
    try:
        now = datetime.utcnow()
        
        promo_codes = PromoCode.query.filter(
            PromoCode.is_active == True,
            PromoCode.valid_from <= now,
            PromoCode.valid_until >= now
        ).all()
        
        # Filter out codes that have reached usage limit
        available_codes = []
        for code in promo_codes:
            if code.usage_limit is None or code.used_count < code.usage_limit:
                available_codes.append({
                    'code': code.code,
                    'description': code.description,
                    'discount_percentage': float(code.discount_percentage),
                    'max_discount_amount': float(code.max_discount_amount) if code.max_discount_amount else None,
                    'min_purchase_amount': float(code.min_purchase_amount) if code.min_purchase_amount else None,
                    'valid_until': code.valid_until.isoformat()
                })
        
        return jsonify({
            'promo_codes': available_codes,
            'count': len(available_codes)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get promo codes', 'message': str(e)}), 500


@trips_bp.route('/promo-codes/<string:code>', methods=['GET'])
def get_promo_code_details(code):
    """
    Get details of a specific promo code
    ---
    Path parameters:
    - code: Promo code string
    """
    try:
        code = code.strip().upper()
        promo_code = PromoCode.query.filter_by(code=code).first()
        
        if not promo_code:
            return jsonify({'error': 'Promo code not found'}), 404
        
        # Check if valid
        is_valid, message = promo_code.is_valid()
        
        return jsonify({
            'promo_code': {
                'code': promo_code.code,
                'description': promo_code.description,
                'discount_percentage': float(promo_code.discount_percentage),
                'max_discount_amount': float(promo_code.max_discount_amount) if promo_code.max_discount_amount else None,
                'min_purchase_amount': float(promo_code.min_purchase_amount) if promo_code.min_purchase_amount else None,
                'valid_from': promo_code.valid_from.isoformat(),
                'valid_until': promo_code.valid_until.isoformat(),
                'is_active': promo_code.is_active,
                'is_valid': is_valid,
                'validity_message': message
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get promo code details', 'message': str(e)}), 500

