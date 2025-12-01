import pytest
import os
from flask import Flask
from app import db, jwt
from app.models.user import User, UserRole
from app.models.trip import Trip, Seat, SeatStatus, TripStatus
from app.models.booking import Booking, PromoCode, BookingStatus, PaymentStatus
from datetime import datetime, timedelta
from flask_jwt_extended import create_access_token, create_refresh_token


@pytest.fixture(scope='function')
def app():
    os.environ['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    
    from app import create_app
    app = create_app('testing')
    
    test_config = {
        'TESTING': True,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SQLALCHEMY_TRACK_MODIFICATIONS': False,
        'JWT_SECRET_KEY': 'test-secret-key',
        'SECRET_KEY': 'test-secret-key',
        'JWT_ACCESS_TOKEN_EXPIRES': False,
        'WTF_CSRF_ENABLED': False,
    }
    
    app.config.update(test_config)
    
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()
    
    if 'SQLALCHEMY_DATABASE_URI' in os.environ:
        del os.environ['SQLALCHEMY_DATABASE_URI']


@pytest.fixture(scope='function')
def client(app):
    return app.test_client()


@pytest.fixture(scope='function')
def runner(app):
    return app.test_cli_runner()


@pytest.fixture
def sample_customer(app):
    with app.app_context():
        user = User(
            email='customer@test.com',
            username='testcustomer',
            first_name='Test',
            last_name='Customer',
            role=UserRole.CUSTOMER
        )
        user.set_password('TestPass123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def sample_admin(app):
    with app.app_context():
        user = User(
            email='admin@test.com',
            username='testadmin',
            first_name='Admin',
            last_name='User',
            role=UserRole.ADMIN
        )
        user.set_password('AdminPass123')
        db.session.add(user)
        db.session.commit()
        db.session.refresh(user)
        return user


@pytest.fixture
def customer_token(app, sample_customer):
    with app.app_context():
        return create_access_token(identity=str(sample_customer.id))


@pytest.fixture
def admin_token(app, sample_admin):
    with app.app_context():
        return create_access_token(identity=str(sample_admin.id))


@pytest.fixture
def customer_refresh_token(app, sample_customer):
    with app.app_context():
        return create_refresh_token(identity=str(sample_customer.id))


@pytest.fixture
def sample_trip(app):
    with app.app_context():
        trip = Trip(
            trip_number='TEST123',
            origin='New York',
            destination='Boston',
            departure_time=datetime.utcnow() + timedelta(days=7),
            arrival_time=datetime.utcnow() + timedelta(days=7, hours=4),
            duration_minutes=240,
            base_fare=50.00,
            total_seats=40,
            available_seats=40,
            status=TripStatus.SCHEDULED,
            operator_name='Test Bus Company',
            vehicle_type='Standard Bus'
        )
        db.session.add(trip)
        db.session.flush()
        
        for i in range(1, 41):
            seat = Seat(
                trip_id=trip.id,
                seat_number=str(i),
                status=SeatStatus.AVAILABLE
            )
            db.session.add(seat)
        
        db.session.commit()
        db.session.refresh(trip)
        return trip


@pytest.fixture
def sample_booking(app, sample_customer, sample_trip):
    with app.app_context():
        seats = Seat.query.filter_by(trip_id=sample_trip.id).limit(2).all()
        
        booking = Booking(
            booking_reference=Booking.generate_booking_reference(),
            user_id=sample_customer.id,
            trip_id=sample_trip.id,
            passenger_name='Test Passenger',
            passenger_email='passenger@test.com',
            passenger_phone='+1234567890',
            subtotal=100.00,
            discount_amount=0.00,
            total_amount=100.00,
            booking_status=BookingStatus.CONFIRMED,
            payment_status=PaymentStatus.UNPAID,
            num_seats=2
        )
        db.session.add(booking)
        db.session.flush()
        
        for seat in seats:
            seat.status = SeatStatus.BOOKED
            seat.booking_id = booking.id
        
        sample_trip.available_seats -= 2
        
        db.session.commit()
        db.session.refresh(booking)
        return booking


@pytest.fixture
def sample_promo_code(app):
    with app.app_context():
        from decimal import Decimal
        promo = PromoCode(
            code='TESTPROMO10',
            description='10% off for testing',
            discount_percentage=Decimal('10.0'),
            valid_from=datetime.utcnow() - timedelta(days=1),
            valid_until=datetime.utcnow() + timedelta(days=30),
            usage_limit=100,
            used_count=0,
            min_purchase_amount=Decimal('50.0'),
            is_active=True
        )
        db.session.add(promo)
        db.session.commit()
        db.session.refresh(promo)
        return promo

