from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.trip import Trip, Seat, TripStatus, SeatStatus
from app.models.booking import Booking, PromoCode, BookingStatus, PaymentStatus
from app.models.user import User, UserRole
from app.utils.decorators import admin_required
from datetime import datetime, timedelta
from sqlalchemy import func, and_, or_, extract

admin_analytics_bp = Blueprint('admin_analytics', __name__)


@admin_analytics_bp.route('/dashboard', methods=['GET'])
@jwt_required()
@admin_required
def get_dashboard_overview():
    """
    Get comprehensive dashboard overview with key metrics
    ---
    Query parameters:
    - date_from: Start date for metrics (YYYY-MM-DD, default: 30 days ago)
    - date_to: End date for metrics (YYYY-MM-DD, default: today)
    """
    try:
        # Parse date range
        date_to_str = request.args.get('date_to', '').strip()
        date_from_str = request.args.get('date_from', '').strip()
        
        if date_to_str:
            try:
                date_to = datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format'}), 400
        else:
            date_to = datetime.utcnow()
        
        if date_from_str:
            try:
                date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
            except ValueError:
                return jsonify({'error': 'Invalid date_from format'}), 400
        else:
            date_from = date_to - timedelta(days=30)
        
        # === BOOKING METRICS ===
        bookings_query = Booking.query.filter(
            Booking.created_at >= date_from,
            Booking.created_at <= date_to
        )
        
        total_bookings = bookings_query.count()
        confirmed_bookings = bookings_query.filter_by(booking_status=BookingStatus.CONFIRMED).count()
        cancelled_bookings = bookings_query.filter_by(booking_status=BookingStatus.CANCELLED).count()
        
        # Revenue metrics
        paid_bookings = bookings_query.filter_by(payment_status=PaymentStatus.PAID)
        total_revenue = db.session.query(func.sum(Booking.total_amount)).filter(
            Booking.id.in_([b.id for b in paid_bookings.all()])
        ).scalar() or 0
        
        pending_revenue = db.session.query(func.sum(Booking.total_amount)).filter(
            Booking.id.in_([b.id for b in bookings_query.filter_by(payment_status=PaymentStatus.UNPAID).all()])
        ).scalar() or 0
        
        # Average booking value
        avg_booking_value = db.session.query(func.avg(Booking.total_amount)).filter(
            Booking.id.in_([b.id for b in bookings_query.all()])
        ).scalar() or 0
        
        # === TRIP METRICS ===
        upcoming_trips = Trip.query.filter(
            Trip.departure_time >= datetime.utcnow(),
            Trip.status == TripStatus.SCHEDULED
        ).count()
        
        trips_today = Trip.query.filter(
            Trip.departure_time >= datetime.utcnow().replace(hour=0, minute=0, second=0),
            Trip.departure_time <= datetime.utcnow().replace(hour=23, minute=59, second=59)
        ).count()
        
        # === USER METRICS ===
        total_users = User.query.count()
        new_users = User.query.filter(
            User.created_at >= date_from,
            User.created_at <= date_to
        ).count()
        
        active_customers = User.query.filter_by(
            role=UserRole.CUSTOMER,
            is_active=True
        ).count()
        
        # === PROMO CODE METRICS ===
        total_discount = db.session.query(func.sum(Booking.discount_amount)).filter(
            Booking.id.in_([b.id for b in bookings_query.all()])
        ).scalar() or 0
        
        bookings_with_promo = bookings_query.filter(
            Booking.promo_code_id.isnot(None)
        ).count()
        
        promo_usage_rate = (bookings_with_promo / total_bookings * 100) if total_bookings > 0 else 0
        
        # === SEAT METRICS ===
        total_seats_available = db.session.query(func.sum(Trip.total_seats)).filter(
            Trip.departure_time >= datetime.utcnow()
        ).scalar() or 0
        
        seats_booked = db.session.query(func.sum(Trip.total_seats - Trip.available_seats)).filter(
            Trip.departure_time >= datetime.utcnow()
        ).scalar() or 0
        
        occupancy_rate = (seats_booked / total_seats_available * 100) if total_seats_available > 0 else 0
        
        # === GROWTH METRICS ===
        # Compare with previous period
        previous_period_start = date_from - (date_to - date_from)
        previous_bookings = Booking.query.filter(
            Booking.created_at >= previous_period_start,
            Booking.created_at < date_from
        ).count()
        
        booking_growth = ((total_bookings - previous_bookings) / previous_bookings * 100) if previous_bookings > 0 else 0
        
        previous_revenue = db.session.query(func.sum(Booking.total_amount)).filter(
            Booking.created_at >= previous_period_start,
            Booking.created_at < date_from,
            Booking.payment_status == PaymentStatus.PAID
        ).scalar() or 0
        
        revenue_growth = ((float(total_revenue) - float(previous_revenue)) / float(previous_revenue) * 100) if previous_revenue > 0 else 0
        
        return jsonify({
            'period': {
                'from': date_from.strftime('%Y-%m-%d'),
                'to': date_to.strftime('%Y-%m-%d'),
                'days': (date_to - date_from).days
            },
            'bookings': {
                'total': total_bookings,
                'confirmed': confirmed_bookings,
                'cancelled': cancelled_bookings,
                'cancellation_rate': round((cancelled_bookings / total_bookings * 100), 2) if total_bookings > 0 else 0,
                'growth_percentage': round(booking_growth, 2)
            },
            'revenue': {
                'total': float(total_revenue),
                'pending': float(pending_revenue),
                'average_booking_value': float(avg_booking_value),
                'growth_percentage': round(revenue_growth, 2)
            },
            'trips': {
                'upcoming': upcoming_trips,
                'today': trips_today,
                'average_occupancy_rate': round(occupancy_rate, 2)
            },
            'users': {
                'total': total_users,
                'new_in_period': new_users,
                'active_customers': active_customers
            },
            'promotions': {
                'total_discount_given': float(total_discount),
                'bookings_with_promo': bookings_with_promo,
                'promo_usage_rate': round(promo_usage_rate, 2)
            },
            'seats': {
                'total_available': int(total_seats_available),
                'booked': int(seats_booked),
                'occupancy_rate': round(occupancy_rate, 2)
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get dashboard overview', 'message': str(e)}), 500


@admin_analytics_bp.route('/revenue', methods=['GET'])
@jwt_required()
@admin_required
def get_revenue_analytics():
    """
    Get detailed revenue analytics
    ---
    Query parameters:
    - date_from: Start date (YYYY-MM-DD)
    - date_to: End date (YYYY-MM-DD)
    - group_by: Grouping (day, week, month, year, default: day)
    """
    try:
        # Parse parameters
        date_to_str = request.args.get('date_to', '').strip()
        date_from_str = request.args.get('date_from', '').strip()
        group_by = request.args.get('group_by', 'day').lower()
        
        if date_to_str:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        else:
            date_to = datetime.utcnow()
        
        if date_from_str:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        else:
            date_from = date_to - timedelta(days=30)
        
        # Revenue by payment status
        revenue_by_status = {}
        for status in PaymentStatus:
            revenue = db.session.query(func.sum(Booking.total_amount)).filter(
                Booking.created_at >= date_from,
                Booking.created_at <= date_to,
                Booking.payment_status == status
            ).scalar() or 0
            revenue_by_status[status.value] = float(revenue)
        
        # Revenue trend over time
        if group_by == 'day':
            date_field = func.date(Booking.created_at)
        elif group_by == 'week':
            date_field = func.date_trunc('week', Booking.created_at)
        elif group_by == 'month':
            date_field = func.date_trunc('month', Booking.created_at)
        elif group_by == 'year':
            date_field = func.date_trunc('year', Booking.created_at)
        else:
            return jsonify({'error': 'Invalid group_by parameter'}), 400
        
        revenue_trend = db.session.query(
            date_field.label('date'),
            func.sum(Booking.total_amount).label('revenue'),
            func.count(Booking.id).label('booking_count')
        ).filter(
            Booking.created_at >= date_from,
            Booking.created_at <= date_to,
            Booking.payment_status == PaymentStatus.PAID
        ).group_by('date').order_by('date').all()
        
        # Revenue by route
        revenue_by_route = db.session.query(
            Trip.origin,
            Trip.destination,
            func.sum(Booking.total_amount).label('revenue'),
            func.count(Booking.id).label('bookings')
        ).join(Booking).filter(
            Booking.created_at >= date_from,
            Booking.created_at <= date_to,
            Booking.payment_status == PaymentStatus.PAID
        ).group_by(Trip.origin, Trip.destination).order_by(
            func.sum(Booking.total_amount).desc()
        ).limit(10).all()
        
        return jsonify({
            'period': {
                'from': date_from.strftime('%Y-%m-%d'),
                'to': date_to.strftime('%Y-%m-%d')
            },
            'revenue_by_status': revenue_by_status,
            'revenue_trend': [
                {
                    'date': str(item[0]),
                    'revenue': float(item[1]),
                    'booking_count': item[2]
                }
                for item in revenue_trend
            ],
            'top_routes_by_revenue': [
                {
                    'origin': route[0],
                    'destination': route[1],
                    'revenue': float(route[2]),
                    'bookings': route[3]
                }
                for route in revenue_by_route
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get revenue analytics', 'message': str(e)}), 500


@admin_analytics_bp.route('/users', methods=['GET'])
@jwt_required()
@admin_required
def get_user_analytics():
    """
    Get user-related analytics
    ---
    Query parameters:
    - date_from: Start date (YYYY-MM-DD)
    - date_to: End date (YYYY-MM-DD)
    """
    try:
        date_to_str = request.args.get('date_to', '').strip()
        date_from_str = request.args.get('date_from', '').strip()
        
        if date_to_str:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        else:
            date_to = datetime.utcnow()
        
        if date_from_str:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        else:
            date_from = date_to - timedelta(days=30)
        
        # Total users by role
        users_by_role = {}
        for role in UserRole:
            count = User.query.filter_by(role=role).count()
            users_by_role[role.value] = count
        
        # Active vs inactive users
        active_users = User.query.filter_by(is_active=True).count()
        inactive_users = User.query.filter_by(is_active=False).count()
        
        # New user registrations trend
        new_users_trend = db.session.query(
            func.date(User.created_at).label('date'),
            func.count(User.id).label('user_count')
        ).filter(
            User.created_at >= date_from,
            User.created_at <= date_to
        ).group_by('date').order_by('date').all()
        
        # Top customers by bookings
        top_customers_bookings = db.session.query(
            User.id,
            User.username,
            User.email,
            func.count(Booking.id).label('booking_count')
        ).join(Booking).group_by(User.id, User.username, User.email).order_by(
            func.count(Booking.id).desc()
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
            func.sum(Booking.total_amount).desc()
        ).limit(10).all()
        
        # Users with bookings
        users_with_bookings = db.session.query(func.count(func.distinct(Booking.user_id))).scalar()
        total_users = User.query.filter_by(role=UserRole.CUSTOMER).count()
        conversion_rate = (users_with_bookings / total_users * 100) if total_users > 0 else 0
        
        return jsonify({
            'period': {
                'from': date_from.strftime('%Y-%m-%d'),
                'to': date_to.strftime('%Y-%m-%d')
            },
            'overview': {
                'users_by_role': users_by_role,
                'active_users': active_users,
                'inactive_users': inactive_users,
                'conversion_rate': round(conversion_rate, 2)
            },
            'new_users_trend': [
                {
                    'date': str(item[0]),
                    'user_count': item[1]
                }
                for item in new_users_trend
            ],
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
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get user analytics', 'message': str(e)}), 500


@admin_analytics_bp.route('/performance', methods=['GET'])
@jwt_required()
@admin_required
def get_performance_metrics():
    """
    Get performance metrics (routes, operators, times)
    ---
    Query parameters:
    - date_from: Start date (YYYY-MM-DD)
    - date_to: End date (YYYY-MM-DD)
    """
    try:
        date_to_str = request.args.get('date_to', '').strip()
        date_from_str = request.args.get('date_from', '').strip()
        
        if date_to_str:
            date_to = datetime.strptime(date_to_str, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        else:
            date_to = datetime.utcnow()
        
        if date_from_str:
            date_from = datetime.strptime(date_from_str, '%Y-%m-%d')
        else:
            date_from = date_to - timedelta(days=30)
        
        # Most popular routes
        popular_routes = db.session.query(
            Trip.origin,
            Trip.destination,
            func.count(Booking.id).label('bookings'),
            func.sum(Booking.num_seats).label('seats_sold'),
            func.avg(Trip.base_fare).label('avg_fare')
        ).join(Booking).filter(
            Booking.created_at >= date_from,
            Booking.created_at <= date_to
        ).group_by(Trip.origin, Trip.destination).order_by(
            func.count(Booking.id).desc()
        ).limit(10).all()
        
        # Best performing operators
        top_operators = db.session.query(
            Trip.operator_name,
            func.count(Booking.id).label('bookings'),
            func.sum(Booking.total_amount).label('revenue'),
            func.count(func.distinct(Trip.id)).label('trip_count')
        ).join(Booking).filter(
            Booking.created_at >= date_from,
            Booking.created_at <= date_to,
            Booking.payment_status == PaymentStatus.PAID
        ).group_by(Trip.operator_name).order_by(
            func.sum(Booking.total_amount).desc()
        ).limit(10).all()
        
        # Peak booking hours
        peak_hours = db.session.query(
            extract('hour', Booking.created_at).label('hour'),
            func.count(Booking.id).label('booking_count')
        ).filter(
            Booking.created_at >= date_from,
            Booking.created_at <= date_to
        ).group_by('hour').order_by('hour').all()
        
        # Peak departure times
        peak_departure = db.session.query(
            extract('hour', Trip.departure_time).label('hour'),
            func.count(Booking.id).label('bookings')
        ).join(Booking).filter(
            Booking.created_at >= date_from,
            Booking.created_at <= date_to
        ).group_by('hour').order_by(func.count(Booking.id).desc()).all()
        
        # Average booking lead time (days before departure)
        avg_lead_time = db.session.query(
            func.avg(
                extract('epoch', Trip.departure_time - Booking.created_at) / 86400
            )
        ).join(Trip).filter(
            Booking.created_at >= date_from,
            Booking.created_at <= date_to
        ).scalar() or 0
        
        return jsonify({
            'period': {
                'from': date_from.strftime('%Y-%m-%d'),
                'to': date_to.strftime('%Y-%m-%d')
            },
            'popular_routes': [
                {
                    'origin': route[0],
                    'destination': route[1],
                    'bookings': route[2],
                    'seats_sold': route[3],
                    'avg_fare': float(route[4])
                }
                for route in popular_routes
            ],
            'top_operators': [
                {
                    'operator_name': op[0],
                    'bookings': op[1],
                    'revenue': float(op[2]),
                    'trip_count': op[3]
                }
                for op in top_operators
            ],
            'peak_booking_hours': [
                {
                    'hour': int(hour[0]),
                    'booking_count': hour[1]
                }
                for hour in peak_hours
            ],
            'peak_departure_times': [
                {
                    'hour': int(dep[0]),
                    'bookings': dep[1]
                }
                for dep in peak_departure
            ],
            'average_booking_lead_time_days': round(float(avg_lead_time), 2)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get performance metrics', 'message': str(e)}), 500

