import pytest
from app.models.payment import TransactionStatus
from app.models.booking import PaymentStatus as BookingPaymentStatus


class TestInitiatePayment:
    def test_initiate_credit_card_payment(self, client, customer_token, sample_booking):
        response = client.post('/api/payments/initiate',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'booking_id': sample_booking.id,
                                 'payment_method': 'credit_card',
                                 'payment_details': {
                                     'card_number': '4111111111111111',
                                     'card_holder': 'John Doe',
                                     'expiry_month': '12',
                                     'expiry_year': '2025',
                                     'cvv': '123'
                                 }
                             })
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'payment' in data
        assert data['payment']['status'] == 'initiated'
        assert data['payment']['payment_method'] == 'credit_card'
    
    def test_initiate_upi_payment(self, client, customer_token, sample_booking):
        response = client.post('/api/payments/initiate',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'booking_id': sample_booking.id,
                                 'payment_method': 'upi',
                                 'payment_details': {
                                     'upi_id': 'test@upi'
                                 }
                             })
        
        assert response.status_code == 201
        data = response.get_json()
        assert data['payment']['payment_method'] == 'upi'
    
    def test_initiate_payment_missing_fields(self, client, customer_token, sample_booking):
        response = client.post('/api/payments/initiate',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'booking_id': sample_booking.id
                             })
        
        assert response.status_code == 400
    
    def test_initiate_payment_invalid_method(self, client, customer_token, sample_booking):
        response = client.post('/api/payments/initiate',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'booking_id': sample_booking.id,
                                 'payment_method': 'invalid_method',
                                 'payment_details': {}
                             })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_initiate_payment_nonexistent_booking(self, client, customer_token):
        response = client.post('/api/payments/initiate',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'booking_id': 9999,
                                 'payment_method': 'credit_card',
                                 'payment_details': {
                                     'card_number': '4111111111111111',
                                     'card_holder': 'John Doe',
                                     'expiry_month': '12',
                                     'expiry_year': '2025',
                                     'cvv': '123'
                                 }
                             })
        
        assert response.status_code == 404
    
    def test_initiate_payment_unauthorized_booking(self, client, admin_token, sample_booking):
        response = client.post('/api/payments/initiate',
                             headers={'Authorization': f'Bearer {admin_token}'},
                             json={
                                 'booking_id': sample_booking.id,
                                 'payment_method': 'credit_card',
                                 'payment_details': {
                                     'card_number': '4111111111111111',
                                     'card_holder': 'John Doe',
                                     'expiry_month': '12',
                                     'expiry_year': '2025',
                                     'cvv': '123'
                                 }
                             })
        
        assert response.status_code == 403
    
    def test_initiate_payment_already_paid(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.booking import Booking
            booking = Booking.query.get(sample_booking.id)
            booking.payment_status = BookingPaymentStatus.PAID
            db.session.commit()
        
        response = client.post('/api/payments/initiate',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={
                                 'booking_id': sample_booking.id,
                                 'payment_method': 'credit_card',
                                 'payment_details': {
                                     'card_number': '4111111111111111',
                                     'card_holder': 'John Doe',
                                     'expiry_month': '12',
                                     'expiry_year': '2025',
                                     'cvv': '123'
                                 }
                             })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'already paid' in data['error'].lower()
    
    def test_initiate_payment_without_auth(self, client, sample_booking):
        response = client.post('/api/payments/initiate',
                             json={
                                 'booking_id': sample_booking.id,
                                 'payment_method': 'credit_card',
                                 'payment_details': {}
                             })
        
        assert response.status_code == 401


class TestProcessPayment:
    def test_process_payment_success(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.payment import Payment, PaymentMethod
            payment = Payment(
                transaction_id='TEST123',
                booking_id=sample_booking.id,
                user_id=sample_booking.user_id,
                amount=sample_booking.total_amount,
                currency='USD',
                payment_method=PaymentMethod.CREDIT_CARD,
                status=TransactionStatus.INITIATED,
                gateway_name='DEMO_PAYMENT_GATEWAY',
                is_demo=True
            )
            db.session.add(payment)
            db.session.commit()
            payment_id = payment.id
        
        response = client.post(f'/api/payments/{payment_id}/process',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={'test_scenario': 'success'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['payment']['status'] == 'success'
        assert data['booking_payment_status'] == 'paid'
    
    def test_process_payment_insufficient_funds(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.payment import Payment, PaymentMethod
            payment = Payment(
                transaction_id='TEST124',
                booking_id=sample_booking.id,
                user_id=sample_booking.user_id,
                amount=sample_booking.total_amount,
                currency='USD',
                payment_method=PaymentMethod.CREDIT_CARD,
                status=TransactionStatus.INITIATED,
                gateway_name='DEMO_PAYMENT_GATEWAY',
                is_demo=True
            )
            db.session.add(payment)
            db.session.commit()
            payment_id = payment.id
        
        response = client.post(f'/api/payments/{payment_id}/process',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={'test_scenario': 'insufficient_funds'})
        
        assert response.status_code == 400
        data = response.get_json()
        assert data['payment']['status'] == 'failed'
    
    def test_process_payment_nonexistent(self, client, customer_token):
        response = client.post('/api/payments/9999/process',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={'test_scenario': 'success'})
        
        assert response.status_code == 404
    
    def test_process_payment_unauthorized(self, client, admin_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.payment import Payment, PaymentMethod
            payment = Payment(
                transaction_id='TEST125',
                booking_id=sample_booking.id,
                user_id=sample_booking.user_id,
                amount=sample_booking.total_amount,
                currency='USD',
                payment_method=PaymentMethod.CREDIT_CARD,
                status=TransactionStatus.INITIATED,
                gateway_name='DEMO_PAYMENT_GATEWAY',
                is_demo=True
            )
            db.session.add(payment)
            db.session.commit()
            payment_id = payment.id
        
        response = client.post(f'/api/payments/{payment_id}/process',
                             headers={'Authorization': f'Bearer {admin_token}'},
                             json={'test_scenario': 'success'})
        
        assert response.status_code == 403
    
    def test_process_already_processed_payment(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.payment import Payment, PaymentMethod
            payment = Payment(
                transaction_id='TEST126',
                booking_id=sample_booking.id,
                user_id=sample_booking.user_id,
                amount=sample_booking.total_amount,
                currency='USD',
                payment_method=PaymentMethod.CREDIT_CARD,
                status=TransactionStatus.SUCCESS,
                gateway_name='DEMO_PAYMENT_GATEWAY',
                is_demo=True
            )
            db.session.add(payment)
            db.session.commit()
            payment_id = payment.id
        
        response = client.post(f'/api/payments/{payment_id}/process',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={'test_scenario': 'success'})
        
        assert response.status_code == 400


class TestGetPaymentStatus:
    def test_get_payment_status_success(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.payment import Payment, PaymentMethod
            payment = Payment(
                transaction_id='TEST127',
                booking_id=sample_booking.id,
                user_id=sample_booking.user_id,
                amount=sample_booking.total_amount,
                currency='USD',
                payment_method=PaymentMethod.CREDIT_CARD,
                status=TransactionStatus.SUCCESS,
                gateway_name='DEMO_PAYMENT_GATEWAY',
                is_demo=True
            )
            db.session.add(payment)
            db.session.commit()
            payment_id = payment.id
        
        response = client.get(f'/api/payments/{payment_id}',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'payment' in data
        assert data['payment']['status'] == 'success'
    
    def test_get_payment_status_unauthorized(self, client, admin_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.payment import Payment, PaymentMethod
            payment = Payment(
                transaction_id='TEST128',
                booking_id=sample_booking.id,
                user_id=sample_booking.user_id,
                amount=sample_booking.total_amount,
                currency='USD',
                payment_method=PaymentMethod.CREDIT_CARD,
                status=TransactionStatus.SUCCESS,
                gateway_name='DEMO_PAYMENT_GATEWAY',
                is_demo=True
            )
            db.session.add(payment)
            db.session.commit()
            payment_id = payment.id
        
        response = client.get(f'/api/payments/{payment_id}',
                            headers={'Authorization': f'Bearer {admin_token}'})
        
        assert response.status_code == 403


class TestGetPaymentsForBooking:
    def test_get_payments_for_booking_success(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.payment import Payment, PaymentMethod
            payment = Payment(
                transaction_id='TEST129',
                booking_id=sample_booking.id,
                user_id=sample_booking.user_id,
                amount=sample_booking.total_amount,
                currency='USD',
                payment_method=PaymentMethod.CREDIT_CARD,
                status=TransactionStatus.SUCCESS,
                gateway_name='DEMO_PAYMENT_GATEWAY',
                is_demo=True
            )
            db.session.add(payment)
            db.session.commit()
        
        response = client.get(f'/api/payments/booking/{sample_booking.id}',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'payments' in data
        assert len(data['payments']) > 0


class TestRefundPayment:
    def test_refund_payment_success(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.payment import Payment, PaymentMethod
            payment = Payment(
                transaction_id='TEST130',
                booking_id=sample_booking.id,
                user_id=sample_booking.user_id,
                amount=sample_booking.total_amount,
                currency='USD',
                payment_method=PaymentMethod.CREDIT_CARD,
                status=TransactionStatus.SUCCESS,
                gateway_name='DEMO_PAYMENT_GATEWAY',
                gateway_response='{"status": "success"}',
                is_demo=True
            )
            db.session.add(payment)
            db.session.commit()
            payment_id = payment.id
        
        response = client.post(f'/api/payments/{payment_id}/refund',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={'reason': 'Customer request'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['payment']['status'] == 'refunded'
        assert 'refund_details' in data
    
    def test_refund_payment_partial(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.payment import Payment, PaymentMethod
            payment = Payment(
                transaction_id='TEST131',
                booking_id=sample_booking.id,
                user_id=sample_booking.user_id,
                amount=100.00,
                currency='USD',
                payment_method=PaymentMethod.CREDIT_CARD,
                status=TransactionStatus.SUCCESS,
                gateway_name='DEMO_PAYMENT_GATEWAY',
                gateway_response='{"status": "success"}',
                is_demo=True
            )
            db.session.add(payment)
            db.session.commit()
            payment_id = payment.id
        
        response = client.post(f'/api/payments/{payment_id}/refund',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={'refund_amount': 50.00, 'reason': 'Partial refund'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['refund_details']['refund_amount'] == 50.0
    
    def test_refund_failed_payment(self, client, customer_token, sample_booking, app):
        with app.app_context():
            from app import db
            from app.models.payment import Payment, PaymentMethod
            payment = Payment(
                transaction_id='TEST132',
                booking_id=sample_booking.id,
                user_id=sample_booking.user_id,
                amount=sample_booking.total_amount,
                currency='USD',
                payment_method=PaymentMethod.CREDIT_CARD,
                status=TransactionStatus.FAILED,
                gateway_name='DEMO_PAYMENT_GATEWAY',
                is_demo=True
            )
            db.session.add(payment)
            db.session.commit()
            payment_id = payment.id
        
        response = client.post(f'/api/payments/{payment_id}/refund',
                             headers={'Authorization': f'Bearer {customer_token}'},
                             json={'reason': 'Customer request'})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'successful payments' in data['error'].lower()


class TestGetPaymentMethods:
    def test_get_payment_methods(self, client):
        response = client.get('/api/payments/methods')
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'payment_methods' in data
        assert len(data['payment_methods']) > 0

