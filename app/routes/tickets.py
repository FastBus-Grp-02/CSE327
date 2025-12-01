from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required
from datetime import datetime
from app import db
from app.models.user import UserRole
from app.models.ticket import Ticket, TicketStatus, TicketPriority
from app.utils.decorators import role_required, admin_required, get_current_user
from app.utils.validators import validate_required_fields

ticket_bp = Blueprint('tickets', __name__)


@ticket_bp.route('', methods=['POST'])
@jwt_required()
def create_ticket():
    """
    Create a new ticket
    ---
    Required fields: title, description
    Optional fields: priority (defaults to 'medium')
    """
    try:
        current_user = get_current_user()
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['title', 'description']
        is_valid, message = validate_required_fields(data, required_fields)
        if not is_valid:
            return jsonify({'error': message}), 400
        
        title = data['title'].strip()
        description = data['description'].strip()
        priority = data.get('priority', 'medium').lower()
        
        # Validate priority
        try:
            ticket_priority = TicketPriority(priority)
        except ValueError:
            return jsonify({'error': 'Invalid priority. Must be: low, medium, high, or urgent'}), 400
        
        # Validate title length
        if len(title) < 5 or len(title) > 200:
            return jsonify({'error': 'Title must be between 5 and 200 characters'}), 400
        
        if len(description) < 10:
            return jsonify({'error': 'Description must be at least 10 characters'}), 400
        
        # Create ticket
        ticket = Ticket(
            title=title,
            description=description,
            priority=ticket_priority,
            creator_id=current_user.id
        )
        
        db.session.add(ticket)
        db.session.commit()
        
        return jsonify({
            'message': 'Ticket created successfully',
            'ticket': ticket.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to create ticket', 'message': str(e)}), 500


@ticket_bp.route('', methods=['GET'])
@jwt_required()
def get_tickets():
    """
    Get all tickets (with filtering)
    ---
    Query parameters:
    - status: Filter by status (open, in_progress, resolved, closed)
    - priority: Filter by priority (low, medium, high, urgent)
    - assigned_to_me: If 'true', show only tickets assigned to current user
    - created_by_me: If 'true', show only tickets created by current user
    - page: Page number (default: 1)
    - per_page: Items per page (default: 10, max: 100)
    """
    try:
        current_user = get_current_user()
        
        # Pagination
        page = request.args.get('page', 1, type=int)
        per_page = min(request.args.get('per_page', 10, type=int), 100)
        
        # Build query
        query = Ticket.query
        
        # Filter by status
        status = request.args.get('status')
        if status:
            try:
                ticket_status = TicketStatus(status.lower())
                query = query.filter_by(status=ticket_status)
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        # Filter by priority
        priority = request.args.get('priority')
        if priority:
            try:
                ticket_priority = TicketPriority(priority.lower())
                query = query.filter_by(priority=ticket_priority)
            except ValueError:
                return jsonify({'error': 'Invalid priority'}), 400
        
        # Filter by assigned to current user
        if request.args.get('assigned_to_me', '').lower() == 'true':
            query = query.filter_by(assigned_to_id=current_user.id)
        
        # Filter by created by current user
        if request.args.get('created_by_me', '').lower() == 'true':
            query = query.filter_by(creator_id=current_user.id)
        
        # If customer, only show their own tickets
        if current_user.role == UserRole.CUSTOMER:
            query = query.filter(
                (Ticket.creator_id == current_user.id) | 
                (Ticket.assigned_to_id == current_user.id)
            )
        
        # Order by created_at descending
        query = query.order_by(Ticket.created_at.desc())
        
        # Paginate
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        tickets = pagination.items
        
        return jsonify({
            'tickets': [ticket.to_dict() for ticket in tickets],
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': pagination.total,
                'pages': pagination.pages,
                'has_next': pagination.has_next,
                'has_prev': pagination.has_prev
            }
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get tickets', 'message': str(e)}), 500


@ticket_bp.route('/<int:ticket_id>', methods=['GET'])
@jwt_required()
def get_ticket(ticket_id):
    """Get a single ticket by ID"""
    try:
        current_user = get_current_user()
        ticket = Ticket.query.get(ticket_id)
        
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Check permissions (customers can only view their own tickets)
        if current_user.role == UserRole.CUSTOMER:
            if ticket.creator_id != current_user.id and ticket.assigned_to_id != current_user.id:
                return jsonify({'error': 'Access denied'}), 403
        
        return jsonify({
            'ticket': ticket.to_dict()
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get ticket', 'message': str(e)}), 500


@ticket_bp.route('/<int:ticket_id>', methods=['PUT'])
@jwt_required()
def update_ticket(ticket_id):
    """
    Update a ticket
    ---
    Customers can only update their own tickets and limited fields
    Admins can update any ticket
    Updateable fields: title, description, priority, status, assigned_to_id
    """
    try:
        current_user = get_current_user()
        ticket = Ticket.query.get(ticket_id)
        
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        # Check permissions
        if current_user.role == UserRole.CUSTOMER:
            if ticket.creator_id != current_user.id:
                return jsonify({'error': 'You can only update your own tickets'}), 403
        
        data = request.get_json()
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Update title
        if 'title' in data:
            title = data['title'].strip()
            if len(title) < 5 or len(title) > 200:
                return jsonify({'error': 'Title must be between 5 and 200 characters'}), 400
            ticket.title = title
        
        # Update description
        if 'description' in data:
            description = data['description'].strip()
            if len(description) < 10:
                return jsonify({'error': 'Description must be at least 10 characters'}), 400
            ticket.description = description
        
        # Update priority
        if 'priority' in data:
            try:
                ticket.priority = TicketPriority(data['priority'].lower())
            except ValueError:
                return jsonify({'error': 'Invalid priority'}), 400
        
        # Update status (admin only)
        if 'status' in data:
            if current_user.role != UserRole.ADMIN:
                return jsonify({'error': 'Only admins can update ticket status'}), 403
            
            try:
                new_status = TicketStatus(data['status'].lower())
                ticket.status = new_status
                
                # Set resolved_at timestamp
                if new_status == TicketStatus.RESOLVED and not ticket.resolved_at:
                    ticket.resolved_at = datetime.utcnow()
            except ValueError:
                return jsonify({'error': 'Invalid status'}), 400
        
        # Assign ticket (admin only)
        if 'assigned_to_id' in data:
            if current_user.role != UserRole.ADMIN:
                return jsonify({'error': 'Only admins can assign tickets'}), 403
            
            if data['assigned_to_id'] is not None:
                from app.models.user import User
                assigned_user = User.query.get(data['assigned_to_id'])
                if not assigned_user:
                    return jsonify({'error': 'Assigned user not found'}), 404
                ticket.assigned_to_id = data['assigned_to_id']
            else:
                ticket.assigned_to_id = None
        
        db.session.commit()
        
        return jsonify({
            'message': 'Ticket updated successfully',
            'ticket': ticket.to_dict()
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to update ticket', 'message': str(e)}), 500


@ticket_bp.route('/<int:ticket_id>', methods=['DELETE'])
@admin_required
def delete_ticket(ticket_id):
    """Delete a ticket (admin only)"""
    try:
        ticket = Ticket.query.get(ticket_id)
        
        if not ticket:
            return jsonify({'error': 'Ticket not found'}), 404
        
        db.session.delete(ticket)
        db.session.commit()
        
        return jsonify({
            'message': 'Ticket deleted successfully'
        }), 200
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Failed to delete ticket', 'message': str(e)}), 500


@ticket_bp.route('/stats', methods=['GET'])
@admin_required
def get_ticket_stats():
    """Get ticket statistics (admin only)"""
    try:
        total_tickets = Ticket.query.count()
        
        stats = {
            'total': total_tickets,
            'by_status': {},
            'by_priority': {}
        }
        
        # Count by status
        for status in TicketStatus:
            count = Ticket.query.filter_by(status=status).count()
            stats['by_status'][status.value] = count
        
        # Count by priority
        for priority in TicketPriority:
            count = Ticket.query.filter_by(priority=priority).count()
            stats['by_priority'][priority.value] = count
        
        return jsonify({
            'stats': stats
        }), 200
        
    except Exception as e:
        return jsonify({'error': 'Failed to get stats', 'message': str(e)}), 500

