from datetime import datetime
from app import db
from enum import Enum


class TicketStatus(Enum):
    """Ticket status enumeration"""
    OPEN = 'open'
    IN_PROGRESS = 'in_progress'
    RESOLVED = 'resolved'
    CLOSED = 'closed'


class TicketPriority(Enum):
    """Ticket priority enumeration"""
    LOW = 'low'
    MEDIUM = 'medium'
    HIGH = 'high'
    URGENT = 'urgent'


class Ticket(db.Model):
    """Ticket model"""
    __tablename__ = 'tickets'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=False)
    status = db.Column(db.Enum(TicketStatus), nullable=False, default=TicketStatus.OPEN)
    priority = db.Column(db.Enum(TicketPriority), nullable=False, default=TicketPriority.MEDIUM)
    
    # Foreign keys
    creator_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    creator = db.relationship('User', back_populates='tickets', foreign_keys=[creator_id])
    assigned_to_user = db.relationship('User', back_populates='assigned_tickets', 
                                       foreign_keys=[assigned_to_id])
    
    def to_dict(self, include_relationships=True):
        """Convert ticket to dictionary"""
        data = {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'status': self.status.value,
            'priority': self.priority.value,
            'creator_id': self.creator_id,
            'assigned_to_id': self.assigned_to_id,
            'created_at': self.created_at.isoformat(),
            'updated_at': self.updated_at.isoformat(),
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None
        }
        
        if include_relationships:
            data['creator'] = {
                'id': self.creator.id,
                'username': self.creator.username,
                'email': self.creator.email
            }
            if self.assigned_to_user:
                data['assigned_to'] = {
                    'id': self.assigned_to_user.id,
                    'username': self.assigned_to_user.username,
                    'email': self.assigned_to_user.email
                }
            else:
                data['assigned_to'] = None
        
        return data
    
    def __repr__(self):
        return f'<Ticket {self.id}: {self.title}>'

