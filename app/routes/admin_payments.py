from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from app import db
from app.models.payment import Payment, TransactionStatus, PaymentMethod
from app.models.booking import Booking, BookingStatus, PaymentStatus as BookingPaymentStatus
from app.utils.decorators import admin_required
from datetime import datetime
from sqlalchemy import func

admin_payments_bp = Blueprint('admin_payments', __name__)


@admin_payments_bp.route('/', methods=['GET'])
@jwt_required()
@admin_required
def get_all_payments():
    """
    Get all payment transactions with filtering
    ---
    Query parameters:
    - status: Filter by transaction status
    - payment_method: Filter by payment method
    - user_id: Filter by user
    - booking_id: Filter by booking
    - date_from: Filter from date (YYYY-MM-DD)
    - date_to: Filter to date (YYYY-MM-DD)
    - search: Search by transaction ID
    - limit: Number of results (default: 50)
    - offset: Pagination offset (default: 0)
    - sort_by: Sort field (initiated_at, completed_at, amount)
    - sort_order: Sort order (asc, desc)
    """
    try:
        # Get query parameters
        status = request.args.get('status', '').lower()
        payment_method = request.args.get('payment_method', '').lower()
        user_id = request.args.get('user_id', type=int)
        booking_id = request.args.get('booking_id', type=int)
        date_from = request.args.get('date_from', '').strip()
        date_to = request.args.get('date_to', '').strip()
        search = request.args.get('search', '').strip()
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        sort_by = request.args.get('sort_by', 'initiated_at').lower()
        sort_order = request.args.get('sort_order', 'desc').lower()
        
        # Build query
        query = Payment.query
        
        # Apply filters
        if status:
            try:
                transaction_status = TransactionStatus(status)
                query = query.filter_by(status=transaction_status)
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        if payment_method:
            try:
                method = PaymentMethod(payment_method)
                query = query.filter_by(payment_method=method)
            except ValueError:
                return jsonify({'error': 'Invalid payment method'}), 400
        
        if user_id:
            query = query.filter_by(user_id=user_id)
        
        if booking_id:
            query = query.filter_by(booking_id=booking_id)
        
        if date_from:
            try:
                date_from_obj = datetime.strptime(date_from, '%Y-%m-%d')
                query = query.filter(Payment.initiated_at >= date_from_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_from format'}), 400
        
        if date_to:
            try:
                date_to_obj = datetime.strptime(date_to, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
                query = query.filter(Payment.initiated_at <= date_to_obj)
            except ValueError:
                return jsonify({'error': 'Invalid date_to format'}), 400
        
        if search:
            query = query.filter(Payment.transaction_id.ilike(f'%{search}%'))
        
        # Apply sorting
        if sort_by == 'completed_at':
            sort_column = Payment.completed_at
        elif sort_by == 'amount':
            sort_column = Payment.amount
        else:
            sort_column = Payment.initiated_at
        
        if sort_order == 'asc':
            query = query.order_by(sort_column.asc())
        else:
            query = query.order_by(sort_column.desc())
        
        # Get total count
        total_count = query.count()
        
        # Apply pagination
        payments = query.limit(limit).offset(offset).all()
        
        return jsonify({
            'payments': [payment.to_dict(include_sensitive=True) for payment in payments],
            'count': len(payments),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get payments', 'message': str(e)}), 500


@admin_payments_bp.route('/<int:payment_id>', methods=['GET'])
@jwt_required()
@admin_required
def get_payment(payment_id):
    """
    Get detailed payment information
    """
    try:
        payment = Payment.query.get(payment_id)
        
        if not payment:
            return jsonify({'error': 'Payment not found'}), 404
        
        # Include booking and user details
        payment_data = payment.to_dict(include_sensitive=True)
        payment_data['booking'] = payment.booking.to_dict(include_relationships=True)
        payment_data['user'] = payment.user.to_dict()
        
        return jsonify({
            'payment': payment_data
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get payment', 'message': str(e)}), 500


@admin_payments_bp.route('/statistics', methods=['GET'])
@jwt_required()
@admin_required
def get_payment_statistics():
    """
    Get payment statistics
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
            from datetime import timedelta
            date_from = date_to - timedelta(days=30)
        
        # Build base query
        query = Payment.query.filter(
            Payment.initiated_at >= date_from,
            Payment.initiated_at <= date_to
        )
        
        # Total transactions
        total_transactions = query.count()
        
        # Transactions by status
        transactions_by_status = {}
        for status in TransactionStatus:
            count = query.filter_by(status=status).count()
            transactions_by_status[status.value] = count
        
        # Transactions by payment method
        transactions_by_method = {}
        for method in PaymentMethod:
            count = query.filter_by(payment_method=method).count()
            transactions_by_method[method.value] = count
        
        # Success rate
        successful_transactions = query.filter_by(status=TransactionStatus.SUCCESS).count()
        success_rate = (successful_transactions / total_transactions * 100) if total_transactions > 0 else 0
        
        # Failed transactions breakdown
        failed_query = query.filter_by(status=TransactionStatus.FAILED)
        failed_reasons = db.session.query(
            Payment.failure_code,
            func.count(Payment.id).label('count')
        ).filter(
            Payment.id.in_([p.id for p in failed_query.all()])
        ).group_by(Payment.failure_code).all()
        
        # Total amount processed
        total_amount = db.session.query(func.sum(Payment.amount)).filter(
            Payment.id.in_([p.id for p in query.filter_by(status=TransactionStatus.SUCCESS).all()])
        ).scalar() or 0
        
        # Total refunded
        total_refunded = db.session.query(func.sum(Payment.refund_amount)).filter(
            Payment.id.in_([p.id for p in query.filter_by(status=TransactionStatus.REFUNDED).all()])
        ).scalar() or 0
        
        # Average transaction value
        avg_transaction = db.session.query(func.avg(Payment.amount)).filter(
            Payment.id.in_([p.id for p in query.all()])
        ).scalar() or 0
        
        return jsonify({
            'period': {
                'from': date_from.strftime('%Y-%m-%d'),
                'to': date_to.strftime('%Y-%m-%d')
            },
            'overview': {
                'total_transactions': total_transactions,
                'successful_transactions': successful_transactions,
                'failed_transactions': transactions_by_status.get('failed', 0),
                'success_rate': round(success_rate, 2),
                'total_amount_processed': float(total_amount),
                'total_refunded': float(total_refunded),
                'average_transaction_value': float(avg_transaction)
            },
            'transactions_by_status': transactions_by_status,
            'transactions_by_method': transactions_by_method,
            'failed_reasons': [
                {
                    'reason': reason[0],
                    'count': reason[1]
                }
                for reason in failed_reasons
            ]
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get statistics', 'message': str(e)}), 500


@admin_payments_bp.route('/failed', methods=['GET'])
@jwt_required()
@admin_required
def get_failed_payments():
    """
    Get all failed payment transactions
    ---
    Query parameters:
    - limit: Number of results (default: 50)
    - offset: Pagination offset (default: 0)
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = Payment.query.filter_by(status=TransactionStatus.FAILED)
        
        total_count = query.count()
        
        payments = query.order_by(Payment.initiated_at.desc()).limit(limit).offset(offset).all()
        
        return jsonify({
            'failed_payments': [payment.to_dict(include_sensitive=True) for payment in payments],
            'count': len(payments),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get failed payments', 'message': str(e)}), 500


@admin_payments_bp.route('/refunds', methods=['GET'])
@jwt_required()
@admin_required
def get_refunded_payments():
    """
    Get all refunded payment transactions
    ---
    Query parameters:
    - limit: Number of results (default: 50)
    - offset: Pagination offset (default: 0)
    """
    try:
        limit = request.args.get('limit', 50, type=int)
        offset = request.args.get('offset', 0, type=int)
        
        query = Payment.query.filter_by(status=TransactionStatus.REFUNDED)
        
        total_count = query.count()
        
        payments = query.order_by(Payment.refund_date.desc()).limit(limit).offset(offset).all()
        
        return jsonify({
            'refunded_payments': [payment.to_dict(include_sensitive=True) for payment in payments],
            'count': len(payments),
            'total_count': total_count,
            'limit': limit,
            'offset': offset
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get refunded payments', 'message': str(e)}), 500

