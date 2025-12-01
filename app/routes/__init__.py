from app.routes.auth import auth_bp
from app.routes.tickets import ticket_bp
from app.routes.profile import profile_bp
from app.routes.trips import trips_bp
from app.routes.bookings import bookings_bp
from app.routes.payments import payments_bp
from app.routes.admin_trips import admin_trips_bp
from app.routes.admin_bookings import admin_bookings_bp
from app.routes.admin_promos import admin_promos_bp
from app.routes.admin_analytics import admin_analytics_bp
from app.routes.admin_payments import admin_payments_bp
from app.routes.admin_users import admin_users_bp

__all__ = [
    'auth_bp', 'ticket_bp', 'profile_bp', 'trips_bp', 'bookings_bp', 'payments_bp',
    'admin_trips_bp', 'admin_bookings_bp', 'admin_promos_bp', 'admin_analytics_bp',
    'admin_payments_bp', 'admin_users_bp'
]

