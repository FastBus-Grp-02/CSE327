# TicketHub - Bus Ticket Management System

A production-ready, fully Dockerized Flask-based REST API for bus ticket management with JWT authentication, role-based access control, Google OAuth integration, and PostgreSQL database.

## 🚀 Features

### Core Functionality
- **Bus Trip Management**: Create, search, and manage bus routes and schedules
- **Ticket Booking System**: Complete booking flow with seat selection
- **Payment Processing**: Integrated payment handling with multiple methods
- **User Profiles**: Comprehensive user management with booking history
- **Promo Codes**: Dynamic discount and promotion system
- **Real-time Seat Availability**: Track available seats across trips

### Security & Authentication
- **JWT Authentication**: Secure token-based authentication with access and refresh tokens
- **Google OAuth**: Sign in with Google integration
- **Role-Based Access Control**: Customer and Admin roles with granular permissions
- **Password Security**: Bcrypt hashing with secure validation

### Admin Features
- **Analytics Dashboard**: Revenue, bookings, and user statistics
- **User Management**: View, activate/deactivate users
- **Booking Management**: Monitor and manage all bookings
- **Trip Management**: Full CRUD operations for trips
- **Payment Tracking**: Monitor all payment transactions
- **Promo Management**: Create and manage promotional codes

### Developer Experience
- **Fully Dockerized**: One-command setup and deployment
- **Database Migrations**: Alembic migrations for version control
- **Comprehensive Testing**: Pytest test suite included
- **API Documentation**: Clear endpoint documentation
- **Clean Architecture**: Modular, maintainable codebase

## 📋 Tech Stack

| Component | Technology |
|-----------|-----------|
| Framework | Flask 3.0 |
| Database | PostgreSQL 18 |
| ORM | SQLAlchemy |
| Authentication | Flask-JWT-Extended |
| OAuth | Google OAuth 2.0 |
| Password Hashing | Werkzeug Security |
| Containerization | Docker & Docker Compose |
| Web Server | Gunicorn |
| Migrations | Alembic (Flask-Migrate) |

## 🏗️ Project Structure

```
TicketHub/
├── app/
│   ├── __init__.py              # Application factory
│   ├── models/                  # Database models
│   │   ├── user.py             # User model with roles
│   │   ├── trip.py             # Trip/route model
│   │   ├── booking.py          # Booking model
│   │   ├── ticket.py           # Ticket model
│   │   └── payment.py          # Payment model
│   ├── routes/                  # API endpoints
│   │   ├── auth.py             # Authentication & OAuth
│   │   ├── trips.py            # Trip management
│   │   ├── bookings.py         # Booking operations
│   │   ├── payments.py         # Payment processing
│   │   ├── profile.py          # User profile
│   │   └── admin_*.py          # Admin endpoints
│   └── utils/                   # Helper utilities
│       ├── decorators.py       # Custom decorators
│       ├── validators.py       # Input validation
│       ├── jwt_handlers.py     # JWT utilities
│       └── error_handlers.py   # Error handling
├── frontend/                    # HTML frontend files
├── migrations/                  # Database migrations
├── tests/                       # Test suite
├── docker-compose.yml           # Docker orchestration
├── Dockerfile                   # Application container
├── Makefile                     # Useful shortcuts
├── requirements.txt             # Python dependencies
├── seed_db.py                   # Database seeding script
└── .env                         # Environment configuration
```

## 🚀 Quick Start (Docker)

### Prerequisites
- Docker (20.10+)
- Docker Compose (2.0+)

### 1. Clone Repository
```bash
git clone <repository-url>
cd TicketHub
```

### 2. Configure Environment
The `.env` file is already configured with development defaults. For production, update:

```env
# Security Keys (MUST CHANGE!)
SECRET_KEY=your-secret-key-here
JWT_SECRET_KEY=your-jwt-secret-key-here

# Database (change for production)
DB_PASSWORD=secure-password-here

# Database Seeding (optional)
SEED_DATABASE=true  # Set to false to skip seeding on startup

# Google OAuth (optional, for Sign in with Google)
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret
GOOGLE_REDIRECT_URI=http://localhost:5000/api/auth/google/callback
```

Generate secure keys:
```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Start Application
```bash
# Build and start all services
docker-compose up -d

# Or using Make
make up
```

This will:
- Build the application container
- Start PostgreSQL database
- Run database migrations automatically
- **Seed the database with sample data** (controlled by `SEED_DATABASE=true` in `.env`)
- Start the API on http://localhost:5000

> **Note:** Database seeding is **enabled by default** in development. It creates sample users, trips, bookings, and promo codes. Set `SEED_DATABASE=false` in `.env` to disable this behavior.

### 4. Verify Installation
```bash
# Check running containers
docker-compose ps

# View logs
docker-compose logs -f api

# Check API health
curl http://localhost:5000/api/auth/health
```

### 5. Access Services
- **API**: http://localhost:5000
- **pgAdmin** (optional): http://localhost:5050
  - Start with: `docker-compose --profile tools up -d`
  - Email: admin@tickethub.local
  - Password: admin

## 📚 Docker Commands

### Using Docker Compose
```bash
# Start services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f api
docker-compose logs -f db

# Restart services
docker-compose restart

# Rebuild containers
docker-compose build --no-cache

# Remove everything (including volumes)
docker-compose down -v
```

### Using Makefile
```bash
# Start services
make up

# Stop services
make down

# View logs
make logs

# Database shell
make db-shell

# Application shell
make shell

# Run migrations
make migrate

# Seed database
make seed

# Run tests
make test

# Clean everything
make clean
```

### Database Operations
```bash
# Run migrations inside container
docker-compose exec api flask db upgrade

# Create new migration
docker-compose exec api flask db migrate -m "description"

# Seed database
docker-compose exec api python seed_db.py

# Access PostgreSQL
docker-compose exec db psql -U postgres -d tickethub
```

## 🧪 Testing

### Run Tests
```bash
# Run all tests
docker-compose exec api pytest

# Run with coverage
docker-compose exec api pytest --cov=app --cov-report=html --cov-report=term

# Run specific test file
docker-compose exec api pytest tests/test_auth.py

# Run with verbose output
docker-compose exec api pytest -v
```

### Local Testing (without Docker)
```bash
# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Run tests
pytest
```

## 📖 API Documentation

### Base URL
```
http://localhost:5000/api
```

### Authentication Endpoints

#### POST /auth/signup
Register a new user account.

**Request:**
```json
{
  "email": "user@example.com",
  "username": "johndoe",
  "password": "SecurePass123",
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890"
}
```

**Response:** `201 Created`
```json
{
  "message": "User registered successfully",
  "user": { /* user object */ },
  "access_token": "eyJ0eXAiOiJKV1QiLCJhbGc...",
  "refresh_token": "eyJ0eXAiOiJKV1QiLCJhbGc..."
}
```

#### POST /auth/login
Login with email/username and password.

**Request:**
```json
{
  "email": "user@example.com",
  "password": "SecurePass123"
}
```

#### GET /auth/google/login
Initiate Google OAuth flow. Redirect to this URL in browser.

#### POST /auth/refresh
Get new access token using refresh token.

**Headers:**
```
Authorization: Bearer <refresh_token>
```

#### GET /auth/me
Get current authenticated user information.

**Headers:**
```
Authorization: Bearer <access_token>
```

### Trip Endpoints

#### GET /trips
Search for available trips.

**Query Parameters:**
- `origin`: Starting location
- `destination`: Destination location
- `date`: Departure date (YYYY-MM-DD)
- `page`: Page number (default: 1)
- `per_page`: Results per page (default: 10)

**Example:**
```bash
curl "http://localhost:5000/api/trips?origin=New York&destination=Boston&date=2024-12-10"
```

#### GET /trips/:id
Get detailed information about a specific trip.

#### POST /admin/trips (Admin Only)
Create a new trip.

**Headers:**
```
Authorization: Bearer <admin_access_token>
```

**Request:**
```json
{
  "bus_number": "BUS001",
  "origin": "New York",
  "destination": "Boston",
  "departure_time": "2024-12-10T08:00:00",
  "arrival_time": "2024-12-10T12:00:00",
  "price": 45.00,
  "available_seats": 40
}
```

### Booking Endpoints

#### POST /bookings
Create a new booking.

**Headers:**
```
Authorization: Bearer <access_token>
```

**Request:**
```json
{
  "trip_id": 1,
  "seat_numbers": [10, 11],
  "passenger_details": [
    {
      "name": "John Doe",
      "age": 30,
      "seat_number": 10
    },
    {
      "name": "Jane Doe",
      "age": 28,
      "seat_number": 11
    }
  ],
  "promo_code": "SUMMER2024"
}
```

**Response:** `201 Created`
```json
{
  "message": "Booking created successfully",
  "booking": {
    "id": 1,
    "booking_reference": "BK-ABC123",
    "trip_id": 1,
    "total_amount": 85.50,
    "status": "pending",
    "created_at": "2024-12-01T10:00:00"
  }
}
```

#### GET /bookings
Get user's booking history.

#### GET /bookings/:id
Get specific booking details.

#### DELETE /bookings/:id
Cancel a booking (before departure).

### Payment Endpoints

#### POST /payments
Process payment for a booking.

**Request:**
```json
{
  "booking_id": 1,
  "payment_method": "credit_card",
  "amount": 85.50
}
```

#### GET /payments/:id
Get payment details.

### Profile Endpoints

#### GET /profile
Get user profile with booking history.

#### PUT /profile
Update user profile.

**Request:**
```json
{
  "first_name": "John",
  "last_name": "Doe",
  "phone_number": "+1234567890"
}
```

### Admin Endpoints

All admin endpoints require admin role and access token.

#### GET /admin/analytics
Get system analytics and statistics.

#### GET /admin/users
List all users with filters.

#### PUT /admin/users/:id/activate
Activate user account.

#### PUT /admin/users/:id/deactivate
Deactivate user account.

#### GET /admin/bookings
View all bookings across system.

#### GET /admin/payments
View all payment transactions.

#### POST /admin/promos
Create promotional code.

#### GET /admin/promos
List all promo codes.

## 🔐 User Roles & Permissions

### Customer Role
- ✅ Register and login
- ✅ Search trips
- ✅ Create bookings
- ✅ Make payments
- ✅ View own bookings
- ✅ Cancel bookings
- ✅ Update profile
- ❌ Access admin features

### Admin Role
- ✅ All customer permissions
- ✅ Create/update/delete trips
- ✅ View all bookings
- ✅ Manage users
- ✅ View analytics
- ✅ Manage payments
- ✅ Create promo codes
- ✅ System configuration

## 🗄️ Database Schema

### Users
- `id`, `email`, `username`, `password_hash`, `role`, `first_name`, `last_name`, `phone_number`, `is_active`, `created_at`, `updated_at`

### Trips
- `id`, `bus_number`, `origin`, `destination`, `departure_time`, `arrival_time`, `price`, `available_seats`, `total_seats`, `status`, `created_at`, `updated_at`

### Bookings
- `id`, `booking_reference`, `user_id`, `trip_id`, `total_amount`, `status`, `promo_code_used`, `created_at`, `updated_at`

### Tickets
- `id`, `booking_id`, `passenger_name`, `passenger_age`, `seat_number`, `status`, `created_at`

### Payments
- `id`, `booking_id`, `amount`, `payment_method`, `status`, `transaction_id`, `created_at`

## 🛠️ Development

### Local Development (without Docker)
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt
pip install -r requirements-dev.txt

# Setup database
createdb tickethub
flask db upgrade

# Run application
python run.py
```

### Environment Variables
Key environment variables in `.env`:

```env
FLASK_ENV=development          # development/production
SECRET_KEY=secret-key          # Application secret key
JWT_SECRET_KEY=jwt-key         # JWT signing key
DB_HOST=db                     # Database host
DB_PORT=5432                   # Database port
DB_NAME=tickethub              # Database name
DB_USER=postgres               # Database user
DB_PASSWORD=postgres           # Database password
APP_PORT=5000                  # Application port
SEED_DATABASE=true             # Auto-seed on startup
```

### Creating Migrations
```bash
# Create new migration
docker-compose exec api flask db migrate -m "Add new field to users"

# Apply migrations
docker-compose exec api flask db upgrade

# Rollback migration
docker-compose exec api flask db downgrade
```

### Adding New Features
1. Create/modify models in `app/models/`
2. Create migration: `flask db migrate -m "description"`
3. Apply migration: `flask db upgrade`
4. Add routes in `app/routes/`
5. Add tests in `tests/`
6. Update documentation

## 📦 Production Deployment

### Docker Production Setup

1. **Update environment variables**:
```env
FLASK_ENV=production
SECRET_KEY=<strong-random-key>
JWT_SECRET_KEY=<strong-random-key>
DB_PASSWORD=<strong-password>
```

2. **Use production docker-compose**:
```yaml
# docker-compose.prod.yml
version: '3.8'
services:
  api:
    restart: always
    environment:
      FLASK_ENV: production
    # ... other production settings
```

3. **Deploy**:
```bash
docker-compose -f docker-compose.prod.yml up -d
```

### Security Checklist for Production
- [ ] Change all secret keys
- [ ] Use strong database passwords
- [ ] Enable HTTPS (add nginx reverse proxy)
- [ ] Configure CORS properly
- [ ] Set up rate limiting
- [ ] Enable logging and monitoring
- [ ] Configure backups
- [ ] Use environment-specific configs
- [ ] Disable debug mode
- [ ] Update Google OAuth redirect URIs

### Recommended Production Stack
- **Reverse Proxy**: Nginx or Traefik
- **SSL**: Let's Encrypt
- **Monitoring**: Prometheus + Grafana
- **Logging**: ELK Stack or CloudWatch
- **CI/CD**: GitHub Actions or GitLab CI

## 🐛 Troubleshooting

### Container Issues
```bash
# Check container status
docker-compose ps

# View logs
docker-compose logs -f api

# Restart services
docker-compose restart

# Rebuild from scratch
docker-compose down -v
docker-compose build --no-cache
docker-compose up -d
```

### Database Issues
```bash
# Check database connectivity
docker-compose exec api pg_isready -h db -U postgres

# Access database directly
docker-compose exec db psql -U postgres -d tickethub

# Reset database
docker-compose down -v
docker-compose up -d
```

### Migration Issues
```bash
# View migration status
docker-compose exec api flask db current

# Force upgrade
docker-compose exec api flask db upgrade

# Rollback and retry
docker-compose exec api flask db downgrade
docker-compose exec api flask db upgrade
```

### Common Errors

**Error: Port already in use**
```bash
# Change port in .env
APP_PORT=5001
```

**Error: Database connection refused**
- Check if db container is running
- Verify DB_HOST=db in .env
- Wait for database to fully start

**Error: Permission denied**
```bash
# Fix file permissions
chmod +x docker-entrypoint.sh
```

## 📊 Database Seeding

### Automatic Seeding on Startup

The application automatically seeds the database when `SEED_DATABASE=true` is set in `.env` (enabled by default for development).

**What gets seeded:**
- **2 Admin Users**
  - Email: `admin@tickethub.com` / Password: `Admin123`
  - Email: `superadmin@tickethub.com` / Password: `Super123`
- **10 Customer Users** with realistic data
- **20+ Bus Trips** across multiple routes
- **Sample Bookings** with various statuses
- **Payment Records** with different methods
- **Active Promo Codes** for testing

### Seeding Control

**Disable automatic seeding:**
```env
# In .env file
SEED_DATABASE=false
```

**Manual seeding (anytime):**
```bash
# Using Docker
docker-compose exec api python seed_db.py

# Or using Makefile
make seed
```

**Fresh database with seeding:**
```bash
# Stop services and remove volumes
docker-compose down -v

# Restart (will auto-seed if enabled)
docker-compose up -d
```

### Production Recommendation

For production environments, set `SEED_DATABASE=false` to prevent sample data from being created.

## 🔍 API Testing

### Using cURL
```bash
# Register
curl -X POST http://localhost:5000/api/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","username":"testuser","password":"Test123456","first_name":"Test","last_name":"User"}'

# Login
curl -X POST http://localhost:5000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"test@example.com","password":"Test123456"}'

# Search trips
curl "http://localhost:5000/api/trips?origin=New York&destination=Boston"
```

### Using Postman
Import the provided Postman collection: `TicketHub.postman_collection.json`

## 📝 License

This project is licensed under the MIT License.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Submit a pull request

## 📞 Support

For issues, questions, or contributions, please open an issue on the repository.

---

**Built with Flask, PostgreSQL, Docker, and industry best practices.**
