from datetime import datetime
from app import db
from enum import Enum


class TripStatus(Enum):
    """Trip status enumeration"""
    SCHEDULED = 'scheduled'
    BOARDING = 'boarding'
    IN_TRANSIT = 'in_transit'
    COMPLETED = 'completed'
    CANCELLED = 'cancelled'


class SeatClass(Enum):
    """Seat class enumeration"""
    ECONOMY = 'economy'
    BUSINESS = 'business'
    FIRST_CLASS = 'first_class'


class SeatStatus(Enum):
    """Seat status enumeration"""
    AVAILABLE = 'available'
    BOOKED = 'booked'
    BLOCKED = 'blocked'


class Trip(db.Model):
    """Trip model for bus/train trips"""
    __tablename__ = 'trips'
    
    id = db.Column(db.Integer, primary_key=True)
    trip_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    
    # Route information
    origin = db.Column(db.String(100), nullable=False, index=True)
    destination = db.Column(db.String(100), nullable=False, index=True)
    
    # Timing
    departure_time = db.Column(db.DateTime, nullable=False, index=True)
    arrival_time = db.Column(db.DateTime, nullable=False)
    duration_minutes = db.Column(db.Integer, nullable=False)
    
    # Pricing
    base_fare = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Capacity
    total_seats = db.Column(db.Integer, nullable=False)
    available_seats = db.Column(db.Integer, nullable=False)
    
    # Status
    status = db.Column(db.Enum(TripStatus), nullable=False, default=TripStatus.SCHEDULED)
    
    # Additional information
    operator_name = db.Column(db.String(100), nullable=False)
    vehicle_type = db.Column(db.String(50))  # e.g., "Bus", "Train", "Express Bus"
    amenities = db.Column(db.Text)  # JSON string of amenities
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    seats = db.relationship('Seat', back_populates='trip', lazy='dynamic', cascade='all, delete-orphan')
    bookings = db.relationship('Booking', back_populates='trip', lazy='dynamic', cascade='all, delete-orphan')
    
    def to_dict(self, include_seats=False):
        """Convert trip to dictionary"""
        # Format duration as "Xh Ym"
        hours = self.duration_minutes // 60
        minutes = self.duration_minutes % 60
        duration_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"
        
        data = {
            'id': self.id,
            'trip_number': self.trip_number,
            'origin': self.origin,
            'destination': self.destination,
            'departure_time': self.departure_time.isoformat(),
            'arrival_time': self.arrival_time.isoformat(),
            'duration_minutes': self.duration_minutes,
            'duration': duration_str,  # Formatted duration for display
            'base_fare': float(self.base_fare),
            'total_seats': self.total_seats,
            'available_seats': self.available_seats,
            'status': self.status.value,
            'operator_name': self.operator_name,
            'vehicle_type': self.vehicle_type,
            'trip_type': self.vehicle_type,  # Alias for frontend compatibility
            'amenities': self.amenities,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat()
        }
        
        if include_seats:
            data['seats'] = [seat.to_dict() for seat in self.seats.all()]
        
        return data
    
    def __repr__(self):
        return f'<Trip {self.trip_number}: {self.origin} -> {self.destination}>'


class Seat(db.Model):
    """Seat model for individual seats on trips"""
    __tablename__ = 'seats'
    
    id = db.Column(db.Integer, primary_key=True)
    seat_number = db.Column(db.String(10), nullable=False)
    seat_class = db.Column(db.Enum(SeatClass), nullable=False, default=SeatClass.ECONOMY)
    status = db.Column(db.Enum(SeatStatus), nullable=False, default=SeatStatus.AVAILABLE)
    
    # Pricing multiplier
    price_multiplier = db.Column(db.Numeric(3, 2), nullable=False, default=1.0)
    
    # Foreign keys
    trip_id = db.Column(db.Integer, db.ForeignKey('trips.id'), nullable=False)
    booking_id = db.Column(db.Integer, db.ForeignKey('bookings.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    trip = db.relationship('Trip', back_populates='seats')
    booking = db.relationship('Booking', back_populates='seats', foreign_keys=[booking_id])
    
    # Unique constraint
    __table_args__ = (
        db.UniqueConstraint('trip_id', 'seat_number', name='unique_seat_per_trip'),
    )
    
    def to_dict(self):
        """Convert seat to dictionary"""
        return {
            'id': self.id,
            'seat_number': self.seat_number,
            'seat_class': self.seat_class.value,
            'status': self.status.value,
            'price_multiplier': float(self.price_multiplier),
            'trip_id': self.trip_id,
            'booking_id': self.booking_id
        }
    
    def calculate_price(self):
        """Calculate seat price based on trip base fare and multiplier"""
        return float(self.trip.base_fare * self.price_multiplier)
    
    def __repr__(self):
        return f'<Seat {self.seat_number} on Trip {self.trip_id}>'

