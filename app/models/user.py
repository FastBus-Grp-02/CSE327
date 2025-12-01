from datetime import datetime
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from enum import Enum


class UserRole(Enum):
    """User roles enumeration"""
    CUSTOMER = 'customer'
    ADMIN = 'admin'


class User(db.Model):
    """User model"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=True)  # Nullable for OAuth users
    role = db.Column(db.Enum(UserRole), nullable=False, default=UserRole.CUSTOMER)
    first_name = db.Column(db.String(100))
    last_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    last_login_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # OAuth fields
    oauth_provider = db.Column(db.String(50), nullable=True)  # 'google', 'facebook', etc.
    oauth_id = db.Column(db.String(255), nullable=True, index=True)  # Provider's user ID
    profile_picture = db.Column(db.String(500), nullable=True)  # URL to profile picture
    
    # Relationships
    tickets = db.relationship('Ticket', back_populates='creator', lazy='dynamic', 
                             foreign_keys='Ticket.creator_id')
    assigned_tickets = db.relationship('Ticket', back_populates='assigned_to_user', 
                                      lazy='dynamic', foreign_keys='Ticket.assigned_to_id')
    
    def set_password(self, password):
        """Hash and set password"""
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        """Verify password"""
        if not self.password_hash:
            return False  # OAuth users don't have passwords
        return check_password_hash(self.password_hash, password)
    
    def is_oauth_user(self):
        """Check if user is an OAuth user"""
        return self.oauth_provider is not None
    
    def to_dict(self, include_email=True):
        """Convert user to dictionary"""
        data = {
            'id': self.id,
            'username': self.username,
            'role': self.role.value,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'oauth_provider': self.oauth_provider,
            'profile_picture': self.profile_picture
        }
        if include_email:
            data['email'] = self.email
        return data
    
    def __repr__(self):
        return f'<User {self.username}>'

