import pytest
from datetime import datetime, timedelta
from app.models.booking import BookingStatus, PaymentStatus
from app.models.trip import SeatStatus


class TestCreateBooking:
    def test_create_booking_success(self, client, customer_token, sample_trip, app):
        with app.app_context():
            from app.models.trip import Seat
            seats = Seat.query.filter_by(trip_id=sample_trip.id, status=SeatStatus.AVAILABLE).limit(2).all()
            seat_ids = [seat.id for seat in seats]
        
        response = client.post('/api/bookings/',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'trip_id': sample_trip.id,
                                 'seat_ids': seat_ids,
                                 'passenger_name': 'John Doe',
                                 'passenger_email': 'john@test.com',
                                 'passenger_phone': '+1234567890'
                             })
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'booking' in data
        assert data['booking']['num_seats'] == 2
        assert data['booking']['booking_status'] == 'confirmed'
        assert data['booking']['payment_status'] == 'unpaid'
    
    def test_create_booking_with_promo_code(self, client, customer_token, sample_trip, sample_promo_code, app):
        with app.app_context():
            from app.models.trip import Seat
            seats = Seat.query.filter_by(trip_id=sample_trip.id, status=SeatStatus.AVAILABLE).limit(2).all()
            seat_ids = [seat.id for seat in seats]
        
        response = client.post('/api/bookings/',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'trip_id': sample_trip.id,
                                 'seat_ids': seat_ids,
                                 'passenger_name': 'John Doe',
                                 'passenger_email': 'john@test.com',
                                 'passenger_phone': '+1234567890',
                                 'promo_code': 'TESTPROMO10'
                             })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['booking']['discount_amount'] > 0
        assert data['booking']['total_amount'] < data['booking']['subtotal']
    
    def test_create_booking_missing_fields(self, client, customer_token, sample_trip):
        response = client.post('/api/bookings/',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'trip_id': sample_trip.id,
                                 'passenger_name': 'John Doe'
                             })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_create_booking_invalid_email(self, client, customer_token, sample_trip, app):
        with app.app_context():
            from app.models.trip import Seat
            seats = Seat.query.filter_by(trip_id=sample_trip.id, status=SeatStatus.AVAILABLE).limit(2).all()
            seat_ids = [seat.id for seat in seats]
        
        response = client.post('/api/bookings/',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'trip_id': sample_trip.id,
                                 'seat_ids': seat_ids,
                                 'passenger_name': 'John Doe',
                                 'passenger_email': 'invalid-email',
                                 'passenger_phone': '+1234567890'
                             })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'email' in data['error'].lower()
    
    def test_create_booking_invalid_phone(self, client, customer_token, sample_trip, app):
        with app.app_context():
            from app.models.trip import Seat
            seats = Seat.query.filter_by(trip_id=sample_trip.id, status=SeatStatus.AVAILABLE).limit(2).all()
            seat_ids = [seat.id for seat in seats]
        
        response = client.post('/api/bookings/',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'trip_id': sample_trip.id,
                                 'seat_ids': seat_ids,
                                 'passenger_name': 'John Doe',
                                 'passenger_email': 'john@test.com',
                                 'passenger_phone': '123'
                             })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'phone' in data['error'].lower()
    
    def test_create_booking_nonexistent_trip(self, client, customer_token):
        response = client.post('/api/bookings/',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'trip_id': 9999,
                                 'seat_ids': [1, 2],
                                 'passenger_name': 'John Doe',
                                 'passenger_email': 'john@test.com',
                                 'passenger_phone': '+1234567890'
                             })
        
        assert response.status_code == 404
    
    def test_create_booking_unavailable_seats(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app.models.trip import Seat
            booked_seats = Seat.query.filter_by(booking_id=sample_booking.id).all()
            seat_ids = [seat.id for seat in booked_seats]
        
        response = client.post('/api/bookings/',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'trip_id': sample_booking.trip_id,
                                 'seat_ids': seat_ids,
                                 'passenger_name': 'John Doe',
                                 'passenger_email': 'john@test.com',
                                 'passenger_phone': '+1234567890'
                             })
        
        assert response.status_code == 409
        data = response.get_json()
        assert 'not available' in data['error'].lower()
    
    def test_create_booking_without_auth(self, client, sample_trip):
        response = client.post('/api/bookings/',
                             json={
                                 'trip_id': sample_trip.id,
                                 'seat_ids': [1, 2],
                                 'passenger_name': 'John Doe',
                                 'passenger_email': 'john@test.com',
                                 'passenger_phone': '+1234567890'
                             })
        
        assert response.status_code == 401
    
    def test_create_booking_empty_seat_list(self, client, customer_token, sample_trip):
        response = client.post('/api/bookings/',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'trip_id': sample_trip.id,
                                 'seat_ids': [],
                                 'passenger_name': 'John Doe',
                                 'passenger_email': 'john@test.com',
                                 'passenger_phone': '+1234567890'
                             })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'seat' in data['error'].lower()


class TestGetUserBookings:
    def test_get_bookings_success(self, client, customer_token, sample_booking):
        response = client.get('/api/bookings/',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'bookings' in data
        assert len(data['bookings']) > 0
        assert data['total_count'] > 0
    
    def test_get_bookings_with_status_filter(self, client, customer_token, sample_booking):
        response = client.get('/api/bookings/?status=confirmed',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'bookings' in data
    
    def test_get_bookings_with_pagination(self, client, customer_token, sample_booking):
        response = client.get('/api/bookings/?limit=10&offset=0',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['limit'] == 10
        assert data['offset'] == 0
    
    def test_get_bookings_without_auth(self, client):
        response = client.get('/api/bookings/')
        
        assert response.status_code == 401


class TestGetBookingDetails:
    def test_get_booking_success(self, client, customer_token, sample_booking):
        response = client.get(f'/api/bookings/{sample_booking.id}',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'booking' in data
        assert data['booking']['id'] == sample_booking.id
    
    def test_get_booking_nonexistent(self, client, customer_token):
        response = client.get('/api/bookings/9999',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 404
    
    def test_get_booking_unauthorized(self, client, admin_token, sample_booking):
        response = client.get(f'/api/bookings/{sample_booking.id}',
                            headers={'Authorization': f'Bearer {admin_token}'})
        
        assert response.status_code == 403


class TestCancelBooking:
    def test_cancel_booking_success(self, client, customer_token, sample_booking, app):
        response = client.put(f'/api/bookings/{sample_booking.id}/cancel',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['booking']['booking_status'] == 'cancelled'
        
        with app.app_context():
            from app.models.trip import Seat
            seats = Seat.query.filter_by(booking_id=sample_booking.id).all()
            for seat in seats:
                assert seat.status == SeatStatus.AVAILABLE
    
    def test_cancel_already_cancelled_booking(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.booking import Booking
            booking = Booking.query.get(sample_booking.id)
            booking.booking_status = BookingStatus.CANCELLED
            db.session.commit()
        
        response = client.put(f'/api/bookings/{sample_booking.id}/cancel',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'already cancelled' in data['error'].lower()
    
    def test_cancel_booking_unauthorized(self, client, admin_token, sample_booking):
        response = client.put(f'/api/bookings/{sample_booking.id}/cancel',
                            headers={'Authorization': f'Bearer {admin_token}'})
        
        assert response.status_code == 403
    
    def test_cancel_nonexistent_booking(self, client, customer_token):
        response = client.put('/api/bookings/9999/cancel',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 404


class TestUpdatePaymentStatus:
    def test_update_payment_status_to_paid(self, client, customer_token, sample_booking):
        response = client.put(f'/api/bookings/{sample_booking.id}/payment',
                            headers={'Authorization': f'Bearer {customer_token}'},
                            json={'payment_status': 'paid'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['booking']['payment_status'] == 'paid'
    
    def test_update_payment_status_to_failed(self, client, customer_token, sample_booking):
        response = client.put(f'/api/bookings/{sample_booking.id}/payment',
                            headers={'Authorization': f'Bearer {customer_token}'},
                            json={'payment_status': 'failed'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['booking']['payment_status'] == 'failed'
    
    def test_update_payment_status_invalid(self, client, customer_token, sample_booking):
        response = client.put(f'/api/bookings/{sample_booking.id}/payment',
                            headers={'Authorization': f'Bearer {customer_token}'},
                            json={'payment_status': 'invalid_status'})
        
        assert response.status_code == 400
    
    def test_update_payment_status_cancelled_booking(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.booking import Booking
            booking = Booking.query.get(sample_booking.id)
            booking.booking_status = BookingStatus.CANCELLED
            db.session.commit()
        
        response = client.put(f'/api/bookings/{sample_booking.id}/payment',
                            headers={'Authorization': f'Bearer {customer_token}'},
                            json={'payment_status': 'paid'})
        
        assert response.status_code == 400

