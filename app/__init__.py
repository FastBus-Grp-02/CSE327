from flask import Flask, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_migrate import Migrate
from flask_cors import CORS
from config import config
import os

db = SQLAlchemy()
jwt = JWTManager()
migrate = Migrate()


def create_app(config_name='default'):
    """Application factory pattern"""
    # Configure Flask to serve static files from frontend directory
    app = Flask(__name__,
                static_folder='../frontend',
                static_url_path='')
    app.config.from_object(config[config_name])
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)
    
    # Configure CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": [
                "http://127.0.0.1:5000",
                "http://localhost:5000",
                "http://127.0.0.1:5500",
                "http://localhost:5500"
            ],
            "methods": ["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
            "expose_headers": ["Content-Type", "Authorization"],
            "supports_credentials": True,
            "max_age": 3600
        }
    })
    
    # JWT error handlers
    from app.utils.jwt_handlers import register_jwt_handlers
    register_jwt_handlers(jwt)
    
    # Register blueprints
    from app.routes import (auth_bp, ticket_bp, profile_bp, trips_bp, bookings_bp, payments_bp,
                           admin_trips_bp, admin_bookings_bp, admin_promos_bp, admin_analytics_bp,
                           admin_payments_bp, admin_users_bp)
    
    # Disable strict slashes globally for all blueprints to avoid 308 redirects on OPTIONS
    app.url_map.strict_slashes = False
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(ticket_bp, url_prefix='/api/tickets')
    app.register_blueprint(profile_bp, url_prefix='/api/profile')
    app.register_blueprint(trips_bp, url_prefix='/api/trips')
    app.register_blueprint(bookings_bp, url_prefix='/api/bookings')
    app.register_blueprint(payments_bp, url_prefix='/api/payments')
    
    # Admin blueprints
    app.register_blueprint(admin_trips_bp, url_prefix='/api/admin/trips')
    app.register_blueprint(admin_bookings_bp, url_prefix='/api/admin/bookings')
    app.register_blueprint(admin_promos_bp, url_prefix='/api/admin/promo-codes')
    app.register_blueprint(admin_analytics_bp, url_prefix='/api/admin/analytics')
    app.register_blueprint(admin_payments_bp, url_prefix='/api/admin/payments')
    app.register_blueprint(admin_users_bp, url_prefix='/api/admin/users')
    
    # Error handlers
    from app.utils.error_handlers import register_error_handlers
    register_error_handlers(app)
    
    # Serve frontend
    @app.route('/')
    def index():
        """Serve the main index page"""
        return send_from_directory(app.static_folder, 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        """Serve static files from frontend directory"""
        # Check if the file exists in the frontend folder
        if path and os.path.exists(os.path.join(app.static_folder, path)):
            return send_from_directory(app.static_folder, path)
        # If file doesn't exist, serve index.html (for client-side routing)
        return send_from_directory(app.static_folder, 'index.html')
    
    return app

