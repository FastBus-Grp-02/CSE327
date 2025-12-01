import os
from app import create_app, db

# Create application instance
app = create_app(os.getenv('FLASK_ENV', 'development'))


@app.shell_context_processor
def make_shell_context():
    """Add database instance and models to shell context"""
    from app.models import User, Ticket
    return {'db': db, 'User': User, 'Ticket': Ticket}


@app.cli.command()
def init_db():
    """Initialize the database"""
    db.create_all()
    print("Database initialized successfully!")


@app.cli.command()
def create_admin():
    """Create an admin user"""
    from app.models.user import User, UserRole
    
    email = input("Enter admin email: ")
    username = input("Enter admin username: ")
    password = input("Enter admin password: ")
    first_name = input("Enter first name: ")
    last_name = input("Enter last name: ")
    
    # Check if user exists
    if User.query.filter_by(email=email).first():
        print("Error: Email already exists!")
        return
    
    if User.query.filter_by(username=username).first():
        print("Error: Username already exists!")
        return
    
    # Create admin user
    admin = User(
        email=email,
        username=username,
        first_name=first_name,
        last_name=last_name,
        role=UserRole.ADMIN
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    
    print(f"Admin user '{username}' created successfully!")


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)

