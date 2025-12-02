# CSE327
Software Engineering 
[payment.py](https://github.com/user-attachments/files/23888235/payment.py)
from datetime import datetime
from app import db
from enum import Enum
import secrets


class PaymentMethod(Enum):
    """Payment method enumeration"""
    CREDIT_CARD = 'credit_card'
    DEBIT_CARD = 'debit_card'
    DIGITAL_WALLET = 'digital_wallet'
    NET_BANKING = 'net_banking'
    UPI = 'upi'


class TransactionStatus(Enum):
    """Transaction status enumeration"""
    INITIATED = 'initiated'
    PROCESSING = 'processing'
    SUCCESS = 'success'
    FAILED = 'failed'
    CANCELLED = 'cancelled'
    REFUNDED = 'refunded'


class Payment(db.Model):
    """
    Payment/Transaction model for booking payments
    WARNING: This is a MOCK/DEMO payment system. No real financial processing.
    """
    __tablename__ = 'payments'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_id = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Foreign keys
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Payment details
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default='USD')
    payment_method = db.Column(db.Enum(PaymentMethod), nullable=False)
    
    # Transaction status
    status = db.Column(db.Enum(TransactionStatus), nullable=False, default=TransactionStatus.INITIATED)
    
    # Mock payment details (masked for demo)
    payment_details = db.Column(db.Text)  # JSON string with masked details
    
    # Gateway simulation
    gateway_name = db.Column(db.String(50), default='DEMO_PAYMENT_GATEWAY')
    gateway_response = db.Column(db.Text)  # JSON string
    
    # Demo markers
    is_demo = db.Column(db.Boolean, nullable=False, default=True)
    demo_note = db.Column(db.String(200), default='MOCK TRANSACTION - NO REAL MONEY PROCESSED')
    
    # Failure details (if applicable)
    failure_reason = db.Column(db.String(200))
    failure_code = db.Column(db.String(20))
    
    # Refund details (if applicable)
    refund_amount = db.Column(db.Numeric(10, 2), default=0.0)
    refund_date = db.Column(db.DateTime)
    refund_transaction_id = db.Column(db.String(50))
    
    # Timestamps
    initiated_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    booking = db.relationship('Booking', backref=db.backref('payments', lazy='dynamic'))
    user = db.relationship('User', backref=db.backref('payments', lazy='dynamic'))
    
    def to_dict(self, include_sensitive=False):
        """Convert payment to dictionary"""
        data = {
            'id': self.id,
            'transaction_id': self.transaction_id,
            'booking_id': self.booking_id,
            'user_id': self.user_id,
            'amount': float(self.amount),
            'currency': self.currency,
            'payment_method': self.payment_method.value,
            'status': self.status.value,
            'gateway_name': self.gateway_name,
            'is_demo': self.is_demo,
            'demo_note': self.demo_note,
            'initiated_at': self.initiated_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }
        
        # Include failure details if failed
        if self.status == TransactionStatus.FAILED:
            data['failure_reason'] = self.failure_reason
            data['failure_code'] = self.failure_code
        
        # Include refund details if refunded
        if self.status == TransactionStatus.REFUNDED:
            data['refund_amount'] = float(self.refund_amount) if self.refund_amount else 0.0
            data['refund_date'] = self.refund_date.isoformat() if self.refund_date else None
            data['refund_transaction_id'] = self.refund_transaction_id
        
        # Include sensitive details only if requested (for admin)
        if include_sensitive:
            data['payment_details'] = self.payment_details
            data['gateway_response'] = self.gateway_response
        
        return data
    
    @staticmethod
    def generate_transaction_id():
        """Generate a unique transaction ID"""
        # Format: DEMO_TXN_<timestamp>_<random>
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_part = secrets.token_hex(4).upper()
        return f'DEMO_TXN_{timestamp}_{random_part}'
    
    @staticmethod
    def generate_refund_transaction_id():
        """Generate a unique refund transaction ID"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        random_part = secrets.token_hex(4).upper()
        return f'DEMO_REFUND_{timestamp}_{random_part}'
    
    def __repr__(self):
        return f'<Payment {self.transaction_id} - {self.status.value}>'

