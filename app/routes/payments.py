from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
from app.models.booking import Booking, BookingStatus, PaymentStatus as BookingPaymentStatus
from app.models.payment import Payment, PaymentMethod, TransactionStatus
from app.utils.validators import validate_required_fields
from datetime import datetime
import json
import random
import time

payments_bp = Blueprint('payments', __name__)


def mask_card_number(card_number):
    """Mask card number for security (even in demo)"""
    if not card_number:
        return None
    card_str = str(card_number).replace(' ', '')
    if len(card_str) < 4:
        return '****'
    return f"****-****-****-{card_str[-4:]}"


def mask_account_number(account_number):
    """Mask account number"""
    if not account_number:
        return None
    acc_str = str(account_number).replace(' ', '')
    if len(acc_str) < 4:
        return '****'
    return f"****{acc_str[-4:]}"


def simulate_payment_processing(payment_method, amount, test_scenario=None):
    """
    Simulate payment gateway processing
    Returns: (success: bool, response: dict)
    
    test_scenario options:
    - 'success' (default): Payment succeeds
    - 'insufficient_funds': Payment fails due to insufficient funds
    - 'invalid_card': Payment fails due to invalid card
    - 'network_error': Payment fails due to network error
    - 'timeout': Payment times out
    - 'declined': Payment declined by bank
    """
    # Simulate processing delay
    time.sleep(0.5)
    
    # Default to success if no test scenario specified
    if not test_scenario:
        # Random failure rate of 5% for realism
        test_scenario = 'success' if random.random() > 0.05 else random.choice([
            'insufficient_funds', 'network_error', 'declined'
        ])
    
    response = {
        'gateway': 'DEMO_PAYMENT_GATEWAY',
        'gateway_transaction_id': f'GATEWAY_{Payment.generate_transaction_id()}',
        'timestamp': datetime.utcnow().isoformat(),
        'amount': float(amount),
        'payment_method': payment_method.value,
        'demo_notice': '⚠️ THIS IS A MOCK TRANSACTION - NO REAL MONEY PROCESSED'
    }
    
    if test_scenario == 'success':
        response.update({
            'status': 'success',
            'message': 'Payment processed successfully (DEMO)',
            'authorization_code': f'AUTH_{random.randint(100000, 999999)}'
        })
        return True, response
    
    elif test_scenario == 'insufficient_funds':
        response.update({
            'status': 'failed',
            'error_code': 'INSUFFICIENT_FUNDS',
            'message': 'Insufficient funds in account (DEMO)'
        })
        return False, response
    
    elif test_scenario == 'invalid_card':
        response.update({
            'status': 'failed',
            'error_code': 'INVALID_CARD',
            'message': 'Invalid card details (DEMO)'
        })
        return False, response
    
    elif test_scenario == 'network_error':
        response.update({
            'status': 'failed',
            'error_code': 'NETWORK_ERROR',
            'message': 'Network error occurred (DEMO)'
        })
        return False, response
    
    elif test_scenario == 'timeout':
        response.update({
            'status': 'failed',
            'error_code': 'TIMEOUT',
            'message': 'Transaction timed out (DEMO)'
        })
        return False, response
    
    elif test_scenario == 'declined':
        response.update({
            'status': 'failed',
            'error_code': 'DECLINED',
            'message': 'Payment declined by bank (DEMO)'
        })
        return False, response
    
    else:
        # Default to success
        response.update({
            'status': 'success',
            'message': 'Payment processed successfully (DEMO)',
            'authorization_code': f'AUTH_{random.randint(100000, 999999)}'
        })
        return True, response


@payments_bp.route('/initiate', methods=['POST'])
@jwt_required()
def initiate_payment():
    """
    Initiate a payment transaction for a booking
    ---
    Request body:
    {
        "booking_id": int,
        "payment_method": "credit_card|debit_card|digital_wallet|net_banking|upi",
        "payment_details": {
            // For credit_card/debit_card:
            "card_number": "string",
            "card_holder": "string",
            "expiry_month": "string",
            "expiry_year": "string",
            "cvv": "string",
            
            // For digital_wallet:
            "wallet_id": "string",
            
            // For net_banking:
            "bank_code": "string",
            "account_number": "string",
            
            // For UPI:
            "upi_id": "string"
        }
    }
    
    ⚠️ DEMO NOTICE: This is a mock payment system. No real financial processing occurs.
    """
    try:
        current_user_id = int(get_jwt_identity())
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Validate required fields
        required_fields = ['booking_id', 'payment_method', 'payment_details']
        is_valid, message = validate_required_fields(data, required_fields)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        booking_id = data['booking_id']
        payment_method_str = data['payment_method'].lower()
        payment_details = data['payment_details']
        
        # Validate payment method
        try:
            payment_method = PaymentMethod(payment_method_str)
        except ValueError:
            return jsonify({'error': 'Invalid payment method'}), 400
        
        # Get booking
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Verify booking ownership
        if booking.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized access to this booking'}), 403
        
        # Check if booking is already paid
        if booking.payment_status == BookingPaymentStatus.PAID:
            return jsonify({'error': 'Booking is already paid'}), 400
        
        # Check if booking is cancelled
        if booking.booking_status == BookingStatus.CANCELLED:
            return jsonify({'error': 'Cannot pay for a cancelled booking'}), 400
        
        # Mask sensitive payment details
        masked_details = {}
        
        if payment_method in [PaymentMethod.CREDIT_CARD, PaymentMethod.DEBIT_CARD]:
            card_number = payment_details.get('card_number', '')
            masked_details = {
                'card_number': mask_card_number(card_number),
                'card_holder': payment_details.get('card_holder', ''),
                'expiry': f"{payment_details.get('expiry_month', '**')}/{payment_details.get('expiry_year', '****')}",
                'cvv': '***'
            }
        elif payment_method == PaymentMethod.DIGITAL_WALLET:
            masked_details = {
                'wallet_id': payment_details.get('wallet_id', '')
            }
        elif payment_method == PaymentMethod.NET_BANKING:
            masked_details = {
                'bank_code': payment_details.get('bank_code', ''),
                'account_number': mask_account_number(payment_details.get('account_number', ''))
            }
        elif payment_method == PaymentMethod.UPI:
            masked_details = {
                'upi_id': payment_details.get('upi_id', '')
            }
        
        # Create payment record
        payment = Payment(
            transaction_id=Payment.generate_transaction_id(),
            booking_id=booking_id,
            user_id=current_user_id,
            amount=booking.total_amount,
            currency='USD',
            payment_method=payment_method,
            status=TransactionStatus.INITIATED,
            payment_details=json.dumps(masked_details),
            gateway_name='DEMO_PAYMENT_GATEWAY',
            is_demo=True,
            demo_note='⚠️ MOCK TRANSACTION - NO REAL MONEY PROCESSED'
        )
        
        db.session.add(payment)
        db.session.commit()
        
        return jsonify({
            'message': 'Payment initiated successfully (DEMO)',
            'demo_notice': '⚠️ THIS IS A MOCK PAYMENT - NO REAL MONEY WILL BE CHARGED',
            'payment': payment.to_dict(),
            'next_step': 'Use POST /payments/{payment_id}/process to simulate payment processing'
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to initiate payment', 'message': str(e)}), 500


@payments_bp.route('/<int:payment_id>/process', methods=['POST'])
@jwt_required()
def process_payment(payment_id):
    """
    Process/complete a payment transaction (MOCK)
    ---
    Request body (optional):
    {
        "test_scenario": "success|insufficient_funds|invalid_card|network_error|timeout|declined"
    }
    
    ⚠️ DEMO NOTICE: This simulates payment processing. No real money is charged.
    """
    try:
        current_user_id = int(get_jwt_identity())
        
        payment = Payment.query.get(payment_id)
        
        if not payment:
            return jsonify({'error': 'Payment not found'}), 404
        
        # Verify payment ownership
        if payment.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized access to this payment'}), 403
        
        # Check if payment is already processed
        if payment.status in [TransactionStatus.SUCCESS, TransactionStatus.FAILED, TransactionStatus.CANCELLED]:
            return jsonify({
                'error': f'Payment already {payment.status.value}',
                'payment': payment.to_dict()
            }), 400
        
        # Get test scenario if provided
        data = request.get_json() or {}
        test_scenario = data.get('test_scenario', 'success')
        
        # Update status to processing
        payment.status = TransactionStatus.PROCESSING
        db.session.commit()
        
        # Simulate payment processing
        success, gateway_response = simulate_payment_processing(
            payment.payment_method,
            payment.amount,
            test_scenario
        )
        
        # Update payment based on result
        payment.gateway_response = json.dumps(gateway_response)
        payment.completed_at = datetime.utcnow()
        
        if success:
            payment.status = TransactionStatus.SUCCESS
            
            # Update booking payment status
            booking = payment.booking
            booking.payment_status = BookingPaymentStatus.PAID
            
            message = '✅ Payment processed successfully (DEMO)'
            status_code = 200
        else:
            payment.status = TransactionStatus.FAILED
            payment.failure_reason = gateway_response.get('message')
            payment.failure_code = gateway_response.get('error_code')
            
            message = '❌ Payment failed (DEMO)'
            status_code = 400
        
        db.session.commit()
        
        return jsonify({
            'message': message,
            'demo_notice': '⚠️ THIS IS A MOCK TRANSACTION - NO REAL MONEY PROCESSED',
            'payment': payment.to_dict(),
            'gateway_response': gateway_response,
            'booking_payment_status': payment.booking.payment_status.value if success else 'unchanged'
        }), status_code
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to process payment', 'message': str(e)}), 500


@payments_bp.route('/<int:payment_id>', methods=['GET'])
@jwt_required()
def get_payment_status(payment_id):
    """
    Get payment transaction status
    """
    try:
        current_user_id = int(get_jwt_identity())
        
        payment = Payment.query.get(payment_id)
        
        if not payment:
            return jsonify({'error': 'Payment not found'}), 404
        
        # Verify payment ownership
        if payment.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized access to this payment'}), 403
        
        return jsonify({
            'payment': payment.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get payment status', 'message': str(e)}), 500


@payments_bp.route('/booking/<int:booking_id>', methods=['GET'])
@jwt_required()
def get_payments_for_booking(booking_id):
    """
    Get all payment attempts for a booking
    """
    try:
        current_user_id = int(get_jwt_identity())
        
        booking = Booking.query.get(booking_id)
        
        if not booking:
            return jsonify({'error': 'Booking not found'}), 404
        
        # Verify booking ownership
        if booking.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized access to this booking'}), 403
        
        payments = Payment.query.filter_by(booking_id=booking_id).order_by(
            Payment.initiated_at.desc()
        ).all()
        
        return jsonify({
            'booking_id': booking_id,
            'booking_reference': booking.booking_reference,
            'payments': [payment.to_dict() for payment in payments],
            'count': len(payments)
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get payments', 'message': str(e)}), 500


@payments_bp.route('/history', methods=['GET'])
@jwt_required()
def get_payment_history():
    """
    Get payment history for current user
    ---
    Query parameters:
    - limit: Number of results (default: 50)
    - offset: Pagination offset (default: 0)
    - status: Filter by status
    """
    try:
        current_user_id = int(get_jwt_identity())
        
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        status = request.args.get('status', '').lower()
        
        # Build query
        query = Payment.query.filter_by(user_id=current_user_id)
        
        # Filter by status if provided
        if status:
            try:
                transaction_status = TransactionStatus(status)
                query = query.filter_by(status=transaction_status)
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination and ordering
        payments = query.order_by(Payment.initiated_at.desc()).limit(limit).offset(offset).all()
        
        return jsonify({
            'payments': [payment.to_dict() for payment in payments],
            'count': len(payments),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get payment history', 'message': str(e)}), 500


@payments_bp.route('/<int:payment_id>/refund', methods=['POST'])
@jwt_required()
def request_refund(payment_id):
    """
    Request a refund for a successful payment (MOCK)
    ---
    Request body (optional):
    {
        "refund_amount": float (optional, defaults to full amount),
        "reason": "string"
    }
    
    ⚠️ DEMO NOTICE: This simulates refund processing. No real money is refunded.
    """
    try:
        current_user_id = int(get_jwt_identity())
        
        payment = Payment.query.get(payment_id)
        
        if not payment:
            return jsonify({'error': 'Payment not found'}), 404
        
        # Verify payment ownership
        if payment.user_id != current_user_id:
            return jsonify({'error': 'Unauthorized access to this payment'}), 403
        
        # Check if payment is successful
        if payment.status != TransactionStatus.SUCCESS:
            return jsonify({'error': 'Only successful payments can be refunded'}), 400
        
        # Check if already refunded
        if payment.status == TransactionStatus.REFUNDED:
            return jsonify({'error': 'Payment already refunded'}), 400
        
        data = request.get_json() or {}
        refund_amount = data.get('refund_amount', float(payment.amount))
        reason = data.get('reason', 'Customer requested refund')
        
        # Validate refund amount
        if refund_amount <= 0 or refund_amount > float(payment.amount):
            return jsonify({'error': 'Invalid refund amount'}), 400
        
        # Simulate refund processing
        time.sleep(0.5)
        
        # Update payment
        payment.status = TransactionStatus.REFUNDED
        payment.refund_amount = refund_amount
        payment.refund_date = datetime.utcnow()
        payment.refund_transaction_id = Payment.generate_refund_transaction_id()
        
        # Update booking payment status
        booking = payment.booking
        booking.payment_status = BookingPaymentStatus.REFUNDED
        
        # Update gateway response
        gateway_response = json.loads(payment.gateway_response) if payment.gateway_response else {}
        gateway_response['refund'] = {
            'status': 'success',
            'refund_transaction_id': payment.refund_transaction_id,
            'refund_amount': refund_amount,
            'reason': reason,
            'timestamp': datetime.utcnow().isoformat(),
            'demo_notice': '⚠️ MOCK REFUND - NO REAL MONEY REFUNDED'
        }
        payment.gateway_response = json.dumps(gateway_response)
        
        db.session.commit()
        
        return jsonify({
            'message': '✅ Refund processed successfully (DEMO)',
            'demo_notice': '⚠️ THIS IS A MOCK REFUND - NO REAL MONEY REFUNDED',
            'payment': payment.to_dict(),
            'refund_details': {
                'refund_transaction_id': payment.refund_transaction_id,
                'refund_amount': float(refund_amount),
                'original_amount': float(payment.amount),
                'refund_date': payment.refund_date.isoformat()
            }
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to process refund', 'message': str(e)}), 500


@payments_bp.route('/methods', methods=['GET'])
def get_payment_methods():
    """
    Get available payment methods (DEMO)
    """
    return jsonify({
        'demo_notice': '⚠️ THESE ARE MOCK PAYMENT METHODS - NO REAL PROCESSING',
        'payment_methods': [
            {
                'code': 'credit_card',
                'name': 'Credit Card',
                'description': 'Pay with Visa, MasterCard, Amex (DEMO)',
                'icon': '💳',
                'demo': True
            },
            {
                'code': 'debit_card',
                'name': 'Debit Card',
                'description': 'Pay with your debit card (DEMO)',
                'icon': '💳',
                'demo': True
            },
            {
                'code': 'digital_wallet',
                'name': 'Digital Wallet',
                'description': 'PayPal, Apple Pay, Google Pay (DEMO)',
                'icon': '👛',
                'demo': True
            },
            {
                'code': 'net_banking',
                'name': 'Net Banking',
                'description': 'Pay directly from your bank account (DEMO)',
                'icon': '🏦',
                'demo': True
            },
            {
                'code': 'upi',
                'name': 'UPI',
                'description': 'Unified Payments Interface (DEMO)',
                'icon': '📱',
                'demo': True
            }
        ]
    }), 200


@payments_bp.route('/test-scenarios', methods=['GET'])
def get_test_scenarios():
    """
    Get available test scenarios for payment simulation
    """
    return jsonify({
        'message': 'Use these test scenarios in the "test_scenario" field when processing payments',
        'demo_notice': '⚠️ FOR TESTING PURPOSES ONLY',
        'scenarios': [
            {
                'code': 'success',
                'name': 'Successful Payment',
                'description': 'Payment processes successfully'
            },
            {
                'code': 'insufficient_funds',
                'name': 'Insufficient Funds',
                'description': 'Payment fails due to insufficient funds'
            },
            {
                'code': 'invalid_card',
                'name': 'Invalid Card',
                'description': 'Payment fails due to invalid card details'
            },
            {
                'code': 'network_error',
                'name': 'Network Error',
                'description': 'Payment fails due to network issues'
            },
            {
                'code': 'timeout',
                'name': 'Transaction Timeout',
                'description': 'Payment times out'
            },
            {
                'code': 'declined',
                'name': 'Payment Declined',
                'description': 'Payment declined by bank'
            }
        ]
    }), 200

