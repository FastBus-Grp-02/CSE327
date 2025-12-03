from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.trip import Trip, Seat, TripStatus, SeatStatus, SeatClass
from app.models.booking import Booking, BookingStatus
from app.utils.decorators import admin_required
from app.utils.validators import validate_required_fields
from datetime import datetime
from sqlalchemy import func

admin_trips_bp = Blueprint('admin_trips', __name__)


@admin_trips_bp.route('/', methods=['POST'])
@jwt_required()
@admin_required
def create_trip():
    """
    Create a new trip
    ---
    Request body:
    {
        "trip_number": "string",
        "origin": "string",
        "destination": "string",
        "departure_time": "ISO datetime",
        "arrival_time": "ISO datetime",
        "base_fare": float,
        "total_seats": int,
        "operator_name": "string",
        "vehicle_type": "string" (optional),
        "amenities": "string" (optional)
    }
    """
    try:
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['trip_number', 'origin', 'destination', 'departure_time', 
                          'arrival_time', 'base_fare', 'total_seats', 'operator_name']
        is_valid, message = validate_required_fields(data, required_fields)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        # Extract data
        trip_number = data['trip_number'].strip().upper()
        origin = data['origin'].strip()
        destination = data['destination'].strip()
        base_fare = float(data['base_fare'])
        total_seats = int(data['total_seats'])
        operator_name = data['operator_name'].strip()
        vehicle_type = data.get('vehicle_type', '').strip()
        amenities = data.get('amenities', '').strip()
        
        # Parse datetimes
        try:
            departure_time = datetime.fromisoformat(data['departure_time'].replace('Z', '+00:00'))
            arrival_time = datetime.fromisoformat(data['arrival_time'].replace('Z', '+00:00'))
        except ValueError:
            return jsonify({'error': 'Invalid datetime format. Use ISO format'}), 400
        
        # Validate business logic
        if departure_time >= arrival_time:
            return jsonify({'error': 'Arrival time must be after departure time'}), 400
        
        if base_fare <= 0:
            return jsonify({'error': 'Base fare must be positive'}), 400
        
        if total_seats <= 0 or total_seats > 500:
            return jsonify({'error': 'Total seats must be between 1 and 500'}), 400
        
        # Check if trip number already exists
        existing_trip = Trip.query.filter_by(trip_number=trip_number).first()
        if existing_trip:
            return jsonify({'error': 'Trip number already exists'}), 409
        
        # Calculate duration
        duration_minutes = int((arrival_time - departure_time).total_seconds() / 60)
        
        # Create trip
        trip = Trip(
            trip_number=trip_number,
            origin=origin,
            destination=destination,
            departure_time=departure_time,
            arrival_time=arrival_time,
            duration_minutes=duration_minutes,
            base_fare=base_fare,
            total_seats=total_seats,
            available_seats=total_seats,
            operator_name=operator_name,
            vehicle_type=vehicle_type if vehicle_type else None,
            amenities=amenities if amenities else None,
            status=TripStatus.SCHEDULED
        )
        
        db.session.add(trip)
        db.session.commit()
        
        return jsonify({
            'message': 'Trip created successfully',
            'trip': trip.to_dict(include_seats=False)
        }), 201
        
    except ValueError as e:
        return jsonify({'error': 'Invalid data type provided', 'message': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create trip', 'message': str(e)}), 500


@admin_trips_bp.route('/', methods=['GET'])
@jwt_required()
@admin_required
def get_all_trips():
    """
    Get all trips with filtering and pagination
    ---
    Query parameters:
    - status: Filter by status (optional)
    - origin: Filter by origin (optional)
    - destination: Filter by destination (optional)
    - date_from: Filter trips from date (YYYY-MM-DD)
    - date_to: Filter trips to date (YYYY-MM-DD)
    - limit: Number of results (default: 50)
    - offset: Pagination offset (default: 0)
    - sort_by: Sort field (departure_time, created_at, base_fare)
    - sort_order: Sort order (asc, desc)
    """
    try:
        # Get query parameters
        status = request.args.get('status', '').lower()
        origin = request.args.get('origin', '').strip()
        destination = request.args.get('destination', '').strip()
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        sort_by = request.args.get('sort_by', 'departure_time').lower()
        sort_order = request.args.get('sort_order', 'asc').lower()
        
        # Build query
        query = Trip.query
        
        # Apply filters
        if status:
            try:
                trip_status = TripStatus(status)
                query = query.filter_by(status=trip_status)
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        if origin:
            query = query.filter(Trip.origin.ilike(f'%{origin}%'))
        
        if destination:
            query = query.filter(Trip.destination.ilike(f'%{destination}%'))
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Trip.departure_time >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format. Use YYYY-MM-DD'}), 400
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(Trip.departure_time <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format. Use YYYY-MM-DD'}), 400
        
        # Apply sorting
        if sort_by == 'base_fare':
            sort_column = Trip.base_fare
        elif sort_by == 'created_at':
            sort_column = Trip.created_at
        else:
            sort_column = Trip.departure_time
        
        if sort_order == 'desc':
            query = query.order_by(sort_column.desc())
        else:
            query = query.order_by(sort_column.asc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        trips = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'trips': [trip.to_dict(include_seats=False) for trip in trips],
            'count': len(trips),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get trips', 'message': str(e)}), 500


@admin_trips_bp.route('/<int:trip_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_trip(trip_id):
    """
    Get detailed trip information including all seats
    """
    try:
        trip = Trip.query.get(trip_id)
        
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404
        
        return jsonify({
            'trip': trip.to_dict(include_seats=True)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get trip', 'message': str(e)}), 500


@admin_trips_bp.route('/<int:trip_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_trip(trip_id):
    """
    Update trip information
    ---
    Allowed fields: origin, destination, departure_time, arrival_time,
                   base_fare, operator_name, vehicle_type, amenities, status
    """
    try:
        trip = Trip.query.get(trip_id)
        
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        updated_fields = []
        
        # Update origin
        if 'origin' in data:
            trip.origin = data['origin'].strip()
            updated_fields.append('origin')
        
        # Update destination
        if 'destination' in data:
            trip.destination = data['destination'].strip()
            updated_fields.append('destination')
        
        # Update departure time
        if 'departure_time' in data:
            try:
                trip.departure_time = datetime.fromisoformat(data['departure_time'].replace('Z', '+00:00'))
                updated_fields.append('departure_time')
            except ValueError:
                return jsonify({'error': 'Invalid departure_time format'}), 400
        
        # Update arrival time
        if 'arrival_time' in data:
            try:
                trip.arrival_time = datetime.fromisoformat(data['arrival_time'].replace('Z', '+00:00'))
                updated_fields.append('arrival_time')
            except ValueError:
                return jsonify({'error': 'Invalid arrival_time format'}), 400
        
        # Recalculate duration if times changed
        if 'departure_time' in updated_fields or 'arrival_time' in updated_fields:
            if trip.departure_time >= trip.arrival_time:
                return jsonify({'error': 'Arrival time must be after departure time'}), 400
            trip.duration_minutes = int((trip.arrival_time - trip.departure_time).total_seconds() / 60)
        
        # Update base fare
        if 'base_fare' in data:
            base_fare = float(data['base_fare'])
            if base_fare <= 0:
                return jsonify({'error': 'Base fare must be positive'}), 400
            trip.base_fare = base_fare
            updated_fields.append('base_fare')
        
        # Update operator name
        if 'operator_name' in data:
            trip.operator_name = data['operator_name'].strip()
            updated_fields.append('operator_name')
        
        # Update vehicle type
        if 'vehicle_type' in data:
            trip.vehicle_type = data['vehicle_type'].strip()
            updated_fields.append('vehicle_type')
        
        # Update amenities
        if 'amenities' in data:
            trip.amenities = data['amenities'].strip()
            updated_fields.append('amenities')
        
        # Update status
        if 'status' in data:
            try:
                trip.status = TripStatus(data['status'].lower())
                updated_fields.append('status')
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        if not updated_fields:
            return jsonify({'error': 'No valid fields provided for update'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': 'Trip updated successfully',
            'updated_fields': updated_fields,
            'trip': trip.to_dict(include_seats=False)
        }), 200
        
    except ValueError as e:
        return jsonify({'error': 'Invalid data type provided', 'message': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update trip', 'message': str(e)}), 500


@admin_trips_bp.route('/<int:trip_id>', methods=['DELETE'])
@jwt_required()
@admin_required
def delete_trip(trip_id):
    """
    Delete a trip (only if no confirmed bookings exist)
    """
    try:
        trip = Trip.query.get(trip_id)
        
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404
        
        # Check for confirmed bookings
        from app.models.booking import BookingStatus
        confirmed_bookings = trip.bookings.filter(
            (Booking.booking_status == BookingStatus.CONFIRMED) |
            (Booking.booking_status == BookingStatus.PENDING)
        ).count()
        
        if confirmed_bookings > 0:
            return jsonify({
                'error': 'Cannot delete trip with confirmed or pending bookings',
                'confirmed_bookings': confirmed_bookings
            }), 409
        
        db.session.delete(trip)
        db.session.commit()
        
        return jsonify({
            'message': 'Trip deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete trip', 'message': str(e)}), 500


@admin_trips_bp.route('/<int:trip_id>/seats', methods=['POST'])
@jwt_required()
@admin_required
def create_seats_for_trip(trip_id):
    """
    Bulk create seats for a trip
    ---
    Request body:
    {
        "seats": [
            {
                "seat_number": "string",
                "seat_class": "economy|business|first_class",
                "price_multiplier": float (optional, default: 1.0)
            },
            ...
        ]
    }
    """
    try:
        trip = Trip.query.get(trip_id)
        
        if not trip:
            return jsonify({'error': 'Trip not found'}), 404
        
        data = request.get_json()
        
        if not data or 'seats' not in data:
            return jsonify({'error': 'Seats data is required'}), 400
        
        seats_data = data['seats']
        
        if not isinstance(seats_data, list) or len(seats_data) == 0:
            return jsonify({'error': 'Seats must be a non-empty array'}), 400
        
        # Validate seat count
        if len(seats_data) > trip.total_seats:
            return jsonify({
                'error': f'Cannot create more seats than trip capacity ({trip.total_seats})'
            }), 400
        
        created_seats = []
        seat_numbers = set()
        
        for seat_data in seats_data:
            seat_number = seat_data.get('seat_number', '').strip()
            seat_class_str = seat_data.get('seat_class', 'economy').lower()
            price_multiplier = seat_data.get('price_multiplier', 1.0)
            
            if not seat_number:
                return jsonify({'error': 'Seat number is required for all seats'}), 400
            
            # Check for duplicate seat numbers in request
            if seat_number in seat_numbers:
                return jsonify({'error': f'Duplicate seat number: {seat_number}'}), 400
            seat_numbers.add(seat_number)
            
            # Check if seat already exists
            existing_seat = Seat.query.filter_by(
                trip_id=trip_id,
                seat_number=seat_number
            ).first()
            
            if existing_seat:
                return jsonify({'error': f'Seat {seat_number} already exists for this trip'}), 409
            
            # Validate seat class
            try:
                seat_class = SeatClass(seat_class_str)
            except ValueError:
                return jsonify({'error': f'Invalid seat class: {seat_class_str}'}), 400
            
            # Validate price multiplier
            if price_multiplier <= 0 or price_multiplier > 10:
                return jsonify({'error': 'Price multiplier must be between 0 and 10'}), 400
            
            # Create seat
            seat = Seat(
                seat_number=seat_number,
                seat_class=seat_class,
                price_multiplier=price_multiplier,
                status=SeatStatus.AVAILABLE,
                trip_id=trip_id
            )
            
            db.session.add(seat)
            created_seats.append(seat)
        
        db.session.commit()
        
        return jsonify({
            'message': f'{len(created_seats)} seats created successfully',
            'seats': [seat.to_dict() for seat in created_seats]
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create seats', 'message': str(e)}), 500


@admin_trips_bp.route('/<int:trip_id>/seats/<int:seat_id>', methods=['PUT'])
@jwt_required()
@admin_required
def update_seat(trip_id, seat_id):
    """
    Update a seat's details
    ---
    Allowed fields: seat_class, price_multiplier, status
    """
    try:
        seat = Seat.query.filter_by(id=seat_id, trip_id=trip_id).first()
        
        if not seat:
            return jsonify({'error': 'Seat not found'}), 404
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        updated_fields = []
        
        # Update seat class
        if 'seat_class' in data:
            try:
                seat.seat_class = SeatClass(data['seat_class'].lower())
                updated_fields.append('seat_class')
            except ValueError:
                return jsonify({'error': 'Invalid seat class'}), 400
        
        # Update price multiplier
        if 'price_multiplier' in data:
            price_multiplier = float(data['price_multiplier'])
            if price_multiplier <= 0 or price_multiplier > 10:
                return jsonify({'error': 'Price multiplier must be between 0 and 10'}), 400
            seat.price_multiplier = price_multiplier
            updated_fields.append('price_multiplier')
        
        # Update status
        if 'status' in data:
            try:
                new_status = SeatStatus(data['status'].lower())
                
                # Prevent changing status of booked seat without proper booking cancellation
                if seat.status == SeatStatus.BOOKED and seat.booking_id:
                    return jsonify({
                        'error': 'Cannot change status of booked seat. Cancel booking first.'
                    }), 400
                
                seat.status = new_status
                updated_fields.append('status')
            except ValueError:
                return jsonify({'error': 'Invalid seat status'}), 400
        
        if not updated_fields:
            return jsonify({'error': 'No valid fields provided for update'}), 400
        
        db.session.commit()
        
        return jsonify({
            'message': 'Seat updated successfully',
            'updated_fields': updated_fields,
            'seat': seat.to_dict()
        }), 200
        
    except ValueError as e:
        return jsonify({'error': 'Invalid data type provided', 'message': str(e)}), 400
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update seat', 'message': str(e)}), 500


@admin_trips_bp.route('/statistics', methods=['GET'])
@jwt_required()
@admin_required
def get_trip_statistics():
    """
    Get statistics about trips
    """
    try:
        # Total trips
        total_trips = Trip.query.count()
        
        # Trips by status
        trips_by_status = {}
        for status in TripStatus:
            count = Trip.query.filter_by(status=status).count()
            trips_by_status[status.value] = count
        
        # Upcoming trips (scheduled and in future)
        upcoming_trips = Trip.query.filter(
            Trip.status == TripStatus.SCHEDULED,
            Trip.departure_time > datetime.utcnow()
        ).count()
        
        # Past trips
        past_trips = Trip.query.filter(
            Trip.departure_time < datetime.utcnow()
        ).count()
        
        # Average occupancy rate
        trips_with_bookings = Trip.query.filter(Trip.total_seats > 0).all()
        total_occupancy = 0
        trip_count = 0
        
        for trip in trips_with_bookings:
            booked_seats = trip.total_seats - trip.available_seats
            occupancy_rate = (booked_seats / trip.total_seats) * 100
            total_occupancy += occupancy_rate
            trip_count += 1
        
        avg_occupancy = round(total_occupancy / trip_count, 2) if trip_count > 0 else 0
        
        # Top routes
        top_routes = db.session.query(
            Trip.origin,
            Trip.destination,
            func.count(Trip.id).label('trip_count')
        ).group_by(Trip.origin, Trip.destination).order_by(
            func.count(Trip.id).desc()
        ).limit(10).all()
        
        return jsonify({
            'statistics': {
                'total_trips': total_trips,
                'trips_by_status': trips_by_status,
                'upcoming_trips': upcoming_trips,
                'past_trips': past_trips,
                'average_occupancy_rate': avg_occupancy,
                'top_routes': [
                    {
                        'origin': route[0],
                        'destination': route[1],
                        'trip_count': route[2]
                    }
                    for route in top_routes
                ]
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get statistics', 'message': str(e)}), 500

