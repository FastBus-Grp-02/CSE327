from datetime import datetime
from app import db
from enum import Enum
import secrets


class BookingStatus(Enum):
    """Booking status enumeration"""
    PENDING = 'pending'
    CONFIRMED = 'confirmed'
    CANCELLED = 'cancelled'
    COMPLETED = 'completed'


class PaymentStatus(Enum):
    """Payment status enumeration"""
    UNPAID = 'unpaid'
    PAID = 'paid'
    REFUNDED = 'refunded'
    FAILED = 'failed'


class Booking(db.Model):
    """Booking model for trip reservations"""
    __tablename__ = 'bookings'
    
    id = db.Column(db.Integer, primary_key=True)
    booking_reference = db.Column(db.String(20), unique=True, nullable=False, index=True)
    
    # Foreign keys
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id'), nullable=False)
    promo_code_id = db.Column(db.Integer, db.ForeignKey('promo_codes.id'), nullable=True)
    
    # Passenger information
    passenger_name = db.Column(db.String(200), nullable=False)
    passenger_email = db.Column(db.String(120), nullable=False)
    passenger_phone = db.Column(db.String(20), nullable=False)
    
    # Pricing
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0.0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Status
    booking_status = db.Column(db.Enum(BookingStatus), nullable=False, default=BookingStatus.PENDING)
    payment_status = db.Column(db.Enum(PaymentStatus), nullable=False, default=PaymentStatus.UNPAID)
    
    # Additional information
    num_seats = db.Column(db.Integer, nullable=False)
    special_requests = db.Column(db.Text)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = db.relationship('User', backref=db.backref('bookings', lazy='dynamic'))
    trip = db.relationship('Trip', back_populates='bookings')
    seats = db.relationship('Seat', back_populates='booking', foreign_keys='Seat.booking_id')
    promo_code = db.relationship('PromoCode', backref=db.backref('bookings', lazy='dynamic'))
    
    def to_dict(self, include_relationships=True):
        """Convert booking to dictionary"""
        data = {
            'id': self.id,
            'booking_reference': self.booking_reference,
            'user_id': self.user_id,
            'trip_id': self.trip_id,
            'passenger_name': self.passenger_name,
            'passenger_email': self.passenger_email,
            'passenger_phone': self.passenger_phone,
            'subtotal': float(self.subtotal),
            'discount_amount': float(self.discount_amount),
            'total_amount': float(self.total_amount),
            'booking_status': self.booking_status.value,
            'payment_status': self.payment_status.value,
            'num_seats': self.num_seats,
            'special_requests': self.special_requests,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_relationships:
            data['trip'] = self.trip.to_dict(include_seats=False)
            data['seats'] = [seat.to_dict() for seat in self.seats]
            if self.promo_code:
                data['promo_code'] = {
                    'code': self.promo_code.code,
                    'discount_percentage': float(self.promo_code.discount_percentage)
                }
            else:
                data['promo_code'] = None
        
        return data
    
    @staticmethod
    def generate_booking_reference():
        """Generate a unique booking reference"""
        return secrets.token_urlsafe(12).upper()[:12]
    
    def __repr__(self):
        return f'<Booking {self.booking_reference}>'


class PromoCode(db.Model):
    """Promo code model for discounts"""
    __tablename__ = 'promo_codes'
    
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(50), unique=True, nullable=False, index=True)
    description = db.Column(db.String(200))
    
    # Discount details
    discount_percentage = db.Column(db.Numeric(5, 2), nullable=False)
    max_discount_amount = db.Column(db.Numeric(10, 2), nullable=True)
    min_purchase_amount = db.Column(db.Numeric(10, 2), nullable=True, default=0.0)
    
    # Usage limits
    usage_limit = db.Column(db.Integer, nullable=True)  # None means unlimited
    used_count = db.Column(db.Integer, nullable=False, default=0)
    usage_per_user = db.Column(db.Integer, nullable=True, default=1)
    
    # Validity
    valid_from = db.Column(db.DateTime, nullable=False)
    valid_until = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, nullable=False, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    def is_valid(self):
        """Check if promo code is currently valid"""
        now = datetime.utcnow()
        
        # Check if active
        if not self.is_active:
            return False, "Promo code is inactive"
        
        # Check date validity
        if now < self.valid_from:
            return False, "Promo code is not yet valid"
        
        if now > self.valid_until:
            return False, "Promo code has expired"
        
        # Check usage limit
        if self.usage_limit is not None and self.used_count >= self.usage_limit:
            return False, "Promo code usage limit reached"
        
        return True, "Promo code is valid"
    
    def check_user_eligibility(self, user_id):
        """Check if user is eligible to use this promo code"""
        if self.usage_per_user is None:
            return True, "User is eligible"
        
        # Count how many times user has used this promo code
        user_usage = Booking.query.filter_by(
            user_id=user_id,
            promo_code_id=self.id
        ).count()
        
        if user_usage >= self.usage_per_user:
            return False, f"You have already used this promo code {user_usage} time(s)"
        
        return True, "User is eligible"
    
    def calculate_discount(self, amount):
        """Calculate discount amount for given purchase amount"""
        # Check minimum purchase amount
        if self.min_purchase_amount and amount < float(self.min_purchase_amount):
            return 0.0
        
        # Calculate percentage discount
        discount = float(amount) * (float(self.discount_percentage) / 100)
        
        # Apply max discount limit if set
        if self.max_discount_amount:
            discount = min(discount, float(self.max_discount_amount))
        
        return round(discount, 2)
    
    def to_dict(self):
        """Convert promo code to dictionary"""
        return {
            'id': self.id,
            'code': self.code,
            'description': self.description,
            'discount_percentage': float(self.discount_percentage),
            'max_discount_amount': float(self.max_discount_amount) if self.max_discount_amount else None,
            'min_purchase_amount': float(self.min_purchase_amount) if self.min_purchase_amount else None,
            'usage_limit': self.usage_limit,
            'used_count': self.used_count,
            'usage_per_user': self.usage_per_user,
            'valid_from': self.valid_from.isoformat(),
            'valid_until': self.valid_until.isoformat(),
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
    
    def __repr__(self):
        return f'<PromoCode {self.code}>'

