"""
Database seeding script for FastBus with Bangladesh-specific sample data
"""
import os
import sys
from datetime import datetime, timedelta
from decimal import Decimal
import random
import json

# Add the project directory to the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.user import User, UserRole
from app.models.trip import Trip, Seat, TripStatus, SeatClass, SeatStatus
from app.models.booking import Booking, PromoCode, BookingStatus, PaymentStatus
from app.models.payment import Payment, PaymentMethod, TransactionStatus
from app.models.ticket import Ticket, TicketStatus, TicketPriority


# Bangladesh cities for routes
BD_CITIES = [
    'Dhaka', 'Chittagong', 'Sylhet', 'Rajshahi', 'Khulna', 
    'Barisal', 'Rangpur', 'Mymensingh', 'Cox\'s Bazar', 
    'Comilla', 'Narayanganj', 'Jessore', 'Bogra', 'Dinajpur'
]

# Popular bus operators in Bangladesh
BD_OPERATORS = [
    'Green Line Paribahan',
    'Shyamoli Paribahan', 
    'Ena Transport',
    'Hanif Enterprise',
    'Shohagh Paribahan',
    'Nabil Paribahan',
    'Royal Coach',
    'TR Travels',
    'Desh Travels',
    'Sakura Paribahan'
]

# Popular routes in Bangladesh with approximate distances and durations
BD_POPULAR_ROUTES = [
    {'origin': 'Dhaka', 'destination': 'Chittagong', 'distance_km': 264, 'duration_min': 360},
    {'origin': 'Dhaka', 'destination': 'Sylhet', 'distance_km': 244, 'duration_min': 330},
    {'origin': 'Dhaka', 'destination': 'Cox\'s Bazar', 'distance_km': 403, 'duration_min': 600},
    {'origin': 'Dhaka', 'destination': 'Rajshahi', 'distance_km': 256, 'duration_min': 360},
    {'origin': 'Dhaka', 'destination': 'Khulna', 'distance_km': 334, 'duration_min': 420},
    {'origin': 'Dhaka', 'destination': 'Rangpur', 'distance_km': 317, 'duration_min': 390},
    {'origin': 'Dhaka', 'destination': 'Barisal', 'distance_km': 210, 'duration_min': 300},
    {'origin': 'Chittagong', 'destination': 'Cox\'s Bazar', 'distance_km': 152, 'duration_min': 210},
    {'origin': 'Chittagong', 'destination': 'Sylhet', 'distance_km': 338, 'duration_min': 450},
    {'origin': 'Dhaka', 'destination': 'Comilla', 'distance_km': 97, 'duration_min': 120},
]

# Bangladesh names for sample users
BD_FIRST_NAMES = [
    'Rafiq', 'Kamal', 'Farhan', 'Tahmid', 'Shakib', 'Mushfiq', 'Nazmul',
    'Ayesha', 'Fariha', 'Nusrat', 'Sultana', 'Rupa', 'Shirin', 'Nasrin',
    'Rahman', 'Hasan', 'Ahmed', 'Ali', 'Mahmud', 'Akter'
]

BD_LAST_NAMES = [
    'Rahman', 'Hossain', 'Ahmed', 'Khan', 'Ali', 'Mahmud', 'Islam', 
    'Chowdhury', 'Akter', 'Begum', 'Khatun', 'Mia', 'Sheikh', 'Uddin'
]


def clear_database():
    """Clear all existing data from database"""
    print("Clearing existing data...")
    
    # Drop all tables and recreate them
    db.drop_all()
    db.create_all()
    
    print("[OK] Database cleared and recreated")


def seed_users():
    """Seed users (both customers and admins)"""
    print("\nSeeding users...")
    users = []
    
    # Create admin users
    admin1 = User(
        email='admin@tickethub.bd',
        username='admin',
        first_name='System',
        last_name='Administrator',
        role=UserRole.ADMIN,
        is_active=True
    )
    admin1.set_password('admin123')
    users.append(admin1)
    
    admin2 = User(
        email='support@tickethub.bd',
        username='support_admin',
        first_name='Support',
        last_name='Team',
        role=UserRole.ADMIN,
        is_active=True
    )
    admin2.set_password('support123')
    users.append(admin2)
    
    # Create customer users
    customer_data = [
        ('rafiq.rahman@gmail.com', 'rafiq_rahman', 'Rafiq', 'Rahman', '+8801711234567'),
        ('kamal.hossain@yahoo.com', 'kamal_h', 'Kamal', 'Hossain', '+8801812345678'),
        ('ayesha.begum@outlook.com', 'ayesha_b', 'Ayesha', 'Begum', '+8801912345679'),
        ('farhan.ahmed@gmail.com', 'farhan_a', 'Farhan', 'Ahmed', '+8801611234560'),
        ('nusrat.khan@gmail.com', 'nusrat_k', 'Nusrat', 'Khan', '+8801712345681'),
        ('tahmid.islam@yahoo.com', 'tahmid_i', 'Tahmid', 'Islam', '+8801812345682'),
        ('fariha.akter@gmail.com', 'fariha_a', 'Fariha', 'Akter', '+8801912345683'),
        ('shakib.chowdhury@outlook.com', 'shakib_c', 'Shakib', 'Chowdhury', '+8801611234584'),
        ('sultana.mia@gmail.com', 'sultana_m', 'Sultana', 'Mia', '+8801712345685'),
        ('nazmul.uddin@gmail.com', 'nazmul_u', 'Nazmul', 'Uddin', '+8801812345686'),
    ]
    
    for email, username, fname, lname, phone in customer_data:
        customer = User(
            email=email,
            username=username,
            first_name=fname,
            last_name=lname,
            role=UserRole.CUSTOMER,
            is_active=True
        )
        customer.set_password('customer123')
        users.append(customer)
    
    db.session.add_all(users)
    db.session.commit()
    
    print(f"[OK] Created {len(users)} users ({len([u for u in users if u.role == UserRole.ADMIN])} admins, {len([u for u in users if u.role == UserRole.CUSTOMER])} customers)")
    return users


def seed_promo_codes():
    """Seed promotional codes"""
    print("\nSeeding promo codes...")
    promo_codes = []
    
    now = datetime.utcnow()
    
    # Welcome offer
    promo1 = PromoCode(
        code='WELCOME10',
        description='Welcome offer - 10% off for new users',
        discount_percentage=10.0,
        max_discount_amount=500.0,
        min_purchase_amount=1000.0,
        usage_limit=100,
        used_count=15,
        usage_per_user=1,
        valid_from=now - timedelta(days=30),
        valid_until=now + timedelta(days=60),
        is_active=True
    )
    promo_codes.append(promo1)
    
    # Eid special
    promo2 = PromoCode(
        code='EID2024',
        description='Eid Mubarak! 15% off on all trips',
        discount_percentage=15.0,
        max_discount_amount=1000.0,
        min_purchase_amount=1500.0,
        usage_limit=500,
        used_count=234,
        usage_per_user=2,
        valid_from=now - timedelta(days=10),
        valid_until=now + timedelta(days=20),
        is_active=True
    )
    promo_codes.append(promo2)
    
    # Weekend special
    promo3 = PromoCode(
        code='WEEKEND20',
        description='Weekend special - 20% off',
        discount_percentage=20.0,
        max_discount_amount=800.0,
        min_purchase_amount=2000.0,
        usage_limit=None,  # Unlimited
        used_count=87,
        usage_per_user=None,  # Unlimited per user
        valid_from=now - timedelta(days=5),
        valid_until=now + timedelta(days=25),
        is_active=True
    )
    promo_codes.append(promo3)
    
    # Early bird
    promo4 = PromoCode(
        code='EARLYBIRD',
        description='Book early and save 12%',
        discount_percentage=12.0,
        max_discount_amount=600.0,
        min_purchase_amount=800.0,
        usage_limit=200,
        used_count=156,
        usage_per_user=3,
        valid_from=now - timedelta(days=15),
        valid_until=now + timedelta(days=45),
        is_active=True
    )
    promo_codes.append(promo4)
    
    # Student discount
    promo5 = PromoCode(
        code='STUDENT25',
        description='Student discount - 25% off',
        discount_percentage=25.0,
        max_discount_amount=1200.0,
        min_purchase_amount=1000.0,
        usage_limit=300,
        used_count=198,
        usage_per_user=5,
        valid_from=now - timedelta(days=60),
        valid_until=now + timedelta(days=120),
        is_active=True
    )
    promo_codes.append(promo5)
    
    # Expired promo (for testing)
    promo6 = PromoCode(
        code='EXPIRED50',
        description='Expired promo code',
        discount_percentage=50.0,
        max_discount_amount=2000.0,
        min_purchase_amount=500.0,
        usage_limit=50,
        used_count=45,
        usage_per_user=1,
        valid_from=now - timedelta(days=90),
        valid_until=now - timedelta(days=1),
        is_active=False
    )
    promo_codes.append(promo6)
    
    db.session.add_all(promo_codes)
    db.session.commit()
    
    print(f"[OK] Created {len(promo_codes)} promo codes")
    return promo_codes


def seed_trips():
    """Seed trips with Bangladesh routes"""
    print("\nSeeding trips...")
    trips = []
    
    now = datetime.utcnow()
    
    # Vehicle types
    vehicle_types = ['AC Bus', 'Non-AC Bus', 'Express Bus', 'Sleeper Coach', 'Deluxe AC']
    
    # Amenities
    amenities_options = [
        json.dumps(['WiFi', 'AC', 'USB Charging', 'Reclining Seats']),
        json.dumps(['AC', 'TV', 'Water Bottle', 'Blanket']),
        json.dumps(['WiFi', 'AC', 'Snacks', 'Entertainment']),
        json.dumps(['AC', 'Reclining Seats', 'Reading Light']),
        json.dumps(['WiFi', 'AC', 'USB Charging', 'Refreshments', 'Restroom'])
    ]
    
    trip_counter = 1000
    
    # Generate trips for the next 7 days
    for day_offset in range(7):
        # Create multiple trips per day for popular routes
        for route in BD_POPULAR_ROUTES:
            # Morning trips (2-3 per route)
            num_morning_trips = random.randint(2, 3)
            for i in range(num_morning_trips):
                hour = random.randint(6, 11)
                minute = random.choice([0, 15, 30, 45])
                
                departure = now + timedelta(days=day_offset, hours=hour, minutes=minute)
                arrival = departure + timedelta(minutes=route['duration_min'])
                
                operator = random.choice(BD_OPERATORS)
                vehicle = random.choice(vehicle_types)
                
                # Calculate base fare (approximately 1.5-2.5 BDT per km)
                base_fare = round(route['distance_km'] * random.uniform(1.5, 2.5), 2)
                
                # Premium vehicles cost more
                if vehicle in ['Deluxe AC', 'Sleeper Coach']:
                    base_fare *= 1.5
                elif vehicle == 'Express Bus':
                    base_fare *= 1.3
                
                total_seats = random.choice([40, 45, 48, 52])
                
                trip = Trip(
                    trip_number=f'TH{trip_counter}',
                    origin=route['origin'],
                    destination=route['destination'],
                    departure_time=departure,
                    arrival_time=arrival,
                    duration_minutes=route['duration_min'],
                    base_fare=base_fare,
                    total_seats=total_seats,
                    available_seats=total_seats,
                    status=TripStatus.SCHEDULED,
                    operator_name=operator,
                    vehicle_type=vehicle,
                    amenities=random.choice(amenities_options)
                )
                trips.append(trip)
                trip_counter += 1
            
            # Evening trips (1-2 per route)
            num_evening_trips = random.randint(1, 2)
            for i in range(num_evening_trips):
                hour = random.randint(18, 23)
                minute = random.choice([0, 15, 30, 45])
                
                departure = now + timedelta(days=day_offset, hours=hour, minutes=minute)
                arrival = departure + timedelta(minutes=route['duration_min'])
                
                operator = random.choice(BD_OPERATORS)
                vehicle = random.choice(vehicle_types)
                
                base_fare = round(route['distance_km'] * random.uniform(1.5, 2.5), 2)
                
                if vehicle in ['Deluxe AC', 'Sleeper Coach']:
                    base_fare *= 1.5
                elif vehicle == 'Express Bus':
                    base_fare *= 1.3
                
                total_seats = random.choice([40, 45, 48, 52])
                
                trip = Trip(
                    trip_number=f'TH{trip_counter}',
                    origin=route['origin'],
                    destination=route['destination'],
                    departure_time=departure,
                    arrival_time=arrival,
                    duration_minutes=route['duration_min'],
                    base_fare=base_fare,
                    total_seats=total_seats,
                    available_seats=total_seats,
                    status=TripStatus.SCHEDULED,
                    operator_name=operator,
                    vehicle_type=vehicle,
                    amenities=random.choice(amenities_options)
                )
                trips.append(trip)
                trip_counter += 1
    
    # Add some trips with different statuses for variety
    # Boarding trip (happening soon)
    departure_boarding = now + timedelta(minutes=30)
    trip_boarding = Trip(
        trip_number=f'TH{trip_counter}',
        origin='Dhaka',
        destination='Chittagong',
        departure_time=departure_boarding,
        arrival_time=departure_boarding + timedelta(hours=6),
        duration_minutes=360,
        base_fare=800.0,
        total_seats=48,
        available_seats=5,
        status=TripStatus.BOARDING,
        operator_name='Green Line Paribahan',
        vehicle_type='Deluxe AC',
        amenities=json.dumps(['WiFi', 'AC', 'USB Charging', 'Refreshments', 'Restroom'])
    )
    trips.append(trip_boarding)
    trip_counter += 1
    
    # In-transit trip
    departure_transit = now - timedelta(hours=2)
    trip_transit = Trip(
        trip_number=f'TH{trip_counter}',
        origin='Dhaka',
        destination='Sylhet',
        departure_time=departure_transit,
        arrival_time=departure_transit + timedelta(hours=5, minutes=30),
        duration_minutes=330,
        base_fare=650.0,
        total_seats=45,
        available_seats=0,
        status=TripStatus.IN_TRANSIT,
        operator_name='Shyamoli Paribahan',
        vehicle_type='AC Bus',
        amenities=json.dumps(['AC', 'TV', 'Water Bottle'])
    )
    trips.append(trip_transit)
    trip_counter += 1
    
    # Completed trip
    departure_completed = now - timedelta(days=1)
    trip_completed = Trip(
        trip_number=f'TH{trip_counter}',
        origin='Chittagong',
        destination='Cox\'s Bazar',
        departure_time=departure_completed,
        arrival_time=departure_completed + timedelta(hours=3, minutes=30),
        duration_minutes=210,
        base_fare=400.0,
        total_seats=40,
        available_seats=0,
        status=TripStatus.COMPLETED,
        operator_name='Hanif Enterprise',
        vehicle_type='Express Bus',
        amenities=json.dumps(['AC', 'Reclining Seats', 'Reading Light'])
    )
    trips.append(trip_completed)
    
    db.session.add_all(trips)
    db.session.commit()
    
    print(f"[OK] Created {len(trips)} trips")
    return trips


def seed_seats(trips):
    """Seed seats for all trips"""
    print("\nSeeding seats...")
    seats = []
    
    for trip in trips:
        # Determine seat layout based on vehicle type
        if trip.vehicle_type == 'Sleeper Coach':
            # Sleeper coaches have different layout (bunks)
            seat_numbers = [f'L{i}' for i in range(1, trip.total_seats // 2 + 1)] + \
                          [f'U{i}' for i in range(1, trip.total_seats // 2 + 1)]
        else:
            # Regular buses have standard seat numbers
            seat_numbers = [f'{chr(65 + (i // 4))}{(i % 4) + 1}' for i in range(trip.total_seats)]
        
        # Assign seat classes
        for i, seat_number in enumerate(seat_numbers):
            # First 8 seats are business class, rest are economy
            if i < 8:
                seat_class = SeatClass.BUSINESS
                price_multiplier = 1.5
            else:
                seat_class = SeatClass.ECONOMY
                price_multiplier = 1.0
            
            # Some seats are already booked for trips with reduced availability
            if trip.available_seats < trip.total_seats:
                booked_seats = trip.total_seats - trip.available_seats
                if i < booked_seats:
                    status = SeatStatus.BOOKED
                else:
                    status = SeatStatus.AVAILABLE
            else:
                status = SeatStatus.AVAILABLE
            
            seat = Seat(
                seat_number=seat_number,
                seat_class=seat_class,
                status=status,
                price_multiplier=price_multiplier,
                trip_id=trip.id
            )
            seats.append(seat)
    
    db.session.add_all(seats)
    db.session.commit()
    
    print(f"[OK] Created {len(seats)} seats across all trips")
    return seats


def seed_bookings(users, trips, promo_codes):
    """Seed sample bookings"""
    print("\nSeeding bookings...")
    bookings = []
    
    # Get customer users only
    customers = [u for u in users if u.role == UserRole.CUSTOMER]
    
    # Get trips that are completed or in transit to create bookings for
    past_trips = [t for t in trips if t.status in [TripStatus.COMPLETED, TripStatus.IN_TRANSIT, TripStatus.BOARDING]]
    
    # Create bookings for past/current trips
    for trip in past_trips[:20]:  # Limit to first 20 past trips
        num_bookings = random.randint(5, 15)
        trip_seats = Seat.query.filter_by(trip_id=trip.id, status=SeatStatus.AVAILABLE).limit(num_bookings).all()
        
        for i in range(min(num_bookings, len(trip_seats))):
            customer = random.choice(customers)
            
            # Randomly assign 1-3 seats per booking
            num_seats = random.randint(1, min(3, len(trip_seats) - i))
            booking_seats = trip_seats[i:i+num_seats]
            
            # Calculate costs
            subtotal_float = sum([seat.calculate_price() for seat in booking_seats])
            subtotal = Decimal(str(round(subtotal_float, 2)))
            
            # Apply promo code randomly (30% chance)
            promo = None
            discount = Decimal('0.0')
            if random.random() < 0.3:
                active_promos = [p for p in promo_codes if p.is_active and p.valid_until > datetime.utcnow()]
                if active_promos:
                    promo = random.choice(active_promos)
                    # Calculate discount manually to avoid type issues
                    if not promo.min_purchase_amount or subtotal >= promo.min_purchase_amount:
                        discount_pct = float(promo.discount_percentage)
                        discount_value = subtotal_float * (discount_pct / 100)
                        if promo.max_discount_amount:
                            discount_value = min(discount_value, float(promo.max_discount_amount))
                        discount = Decimal(str(round(discount_value, 2)))
            
            total = subtotal - discount
            
            # Determine status based on trip status
            if trip.status == TripStatus.COMPLETED:
                booking_status = BookingStatus.COMPLETED
                payment_status = PaymentStatus.PAID
            elif trip.status == TripStatus.IN_TRANSIT:
                booking_status = BookingStatus.CONFIRMED
                payment_status = PaymentStatus.PAID
            else:  # BOARDING
                booking_status = BookingStatus.CONFIRMED
                payment_status = PaymentStatus.PAID
            
            booking = Booking(
                booking_reference=Booking.generate_booking_reference(),
                user_id=customer.id,
                trip_id=trip.id,
                promo_code_id=promo.id if promo else None,
                passenger_name=f"{customer.first_name} {customer.last_name}",
                passenger_email=customer.email,
                passenger_phone=f"+880{random.randint(1600000000, 1999999999)}",
                subtotal=subtotal,
                discount_amount=discount,
                total_amount=total,
                booking_status=booking_status,
                payment_status=payment_status,
                num_seats=num_seats,
                special_requests=random.choice([None, 'Window seat preferred', 'Need extra legroom', 'Traveling with child'])
            )
            bookings.append(booking)
            
            # Update seats
            for seat in booking_seats:
                seat.status = SeatStatus.BOOKED
                seat.booking_id = None  # Will be set after booking is committed
            
            # Update trip available seats
            trip.available_seats -= num_seats
    
    # Also create some future bookings
    future_trips = [t for t in trips if t.status == TripStatus.SCHEDULED][:30]
    
    for trip in future_trips:
        num_bookings = random.randint(2, 8)
        trip_seats = Seat.query.filter_by(trip_id=trip.id, status=SeatStatus.AVAILABLE).limit(num_bookings * 2).all()
        
        for i in range(min(num_bookings, len(trip_seats) // 2)):
            customer = random.choice(customers)
            
            num_seats = random.randint(1, min(2, len(trip_seats) // 2 - i))
            booking_seats = trip_seats[i*2:i*2+num_seats]
            
            subtotal_float = sum([seat.calculate_price() for seat in booking_seats])
            subtotal = Decimal(str(round(subtotal_float, 2)))
            
            # Higher chance of promo for future bookings (50%)
            promo = None
            discount = Decimal('0.0')
            if random.random() < 0.5:
                active_promos = [p for p in promo_codes if p.is_active and p.valid_until > datetime.utcnow()]
                if active_promos:
                    promo = random.choice(active_promos)
                    # Calculate discount manually to avoid type issues
                    if not promo.min_purchase_amount or subtotal >= promo.min_purchase_amount:
                        discount_pct = float(promo.discount_percentage)
                        discount_value = subtotal_float * (discount_pct / 100)
                        if promo.max_discount_amount:
                            discount_value = min(discount_value, float(promo.max_discount_amount))
                        discount = Decimal(str(round(discount_value, 2)))
            
            total = subtotal - discount
            
            # Mix of confirmed and pending bookings
            if random.random() < 0.8:
                booking_status = BookingStatus.CONFIRMED
                payment_status = PaymentStatus.PAID
            else:
                booking_status = BookingStatus.PENDING
                payment_status = PaymentStatus.UNPAID
            
            booking = Booking(
                booking_reference=Booking.generate_booking_reference(),
                user_id=customer.id,
                trip_id=trip.id,
                promo_code_id=promo.id if promo else None,
                passenger_name=f"{customer.first_name} {customer.last_name}",
                passenger_email=customer.email,
                passenger_phone=f"+880{random.randint(1600000000, 1999999999)}",
                subtotal=subtotal,
                discount_amount=discount,
                total_amount=total,
                booking_status=booking_status,
                payment_status=payment_status,
                num_seats=num_seats,
                special_requests=random.choice([None, 'Window seat preferred', 'Need extra legroom', 'Traveling with elderly'])
            )
            bookings.append(booking)
            
            # Update seats if confirmed
            if booking_status == BookingStatus.CONFIRMED:
                for seat in booking_seats:
                    seat.status = SeatStatus.BOOKED
                
                trip.available_seats -= num_seats
    
    db.session.add_all(bookings)
    db.session.commit()
    
    # Update seat booking_ids
    for booking in bookings:
        booking_seats = Seat.query.filter_by(trip_id=booking.trip_id, status=SeatStatus.BOOKED).limit(booking.num_seats).all()
        for seat in booking_seats:
            if seat.booking_id is None:
                seat.booking_id = booking.id
    
    db.session.commit()
    
    print(f"[OK] Created {len(bookings)} bookings")
    return bookings


def seed_payments(bookings):
    """Seed payments for bookings"""
    print("\nSeeding payments...")
    payments = []
    
    # Payment methods common in Bangladesh
    payment_methods = [
        PaymentMethod.DIGITAL_WALLET,  # bKash, Nagad, Rocket
        PaymentMethod.CREDIT_CARD,
        PaymentMethod.DEBIT_CARD,
        PaymentMethod.NET_BANKING,
    ]
    
    # Create payments for paid bookings
    paid_bookings = [b for b in bookings if b.payment_status == PaymentStatus.PAID]
    
    for booking in paid_bookings:
        payment_method = random.choice(payment_methods)
        
        # Most payments are successful
        if random.random() < 0.95:
            status = TransactionStatus.SUCCESS
            completed_at = booking.created_at + timedelta(minutes=random.randint(1, 5))
        else:
            status = TransactionStatus.FAILED
            completed_at = booking.created_at + timedelta(minutes=random.randint(1, 3))
        
        payment_details = json.dumps({
            'method': payment_method.value,
            'masked_number': f"****{random.randint(1000, 9999)}",
            'provider': random.choice(['bKash', 'Nagad', 'Rocket', 'DBBL', 'City Bank', 'Dutch-Bangla Bank'])
        })
        
        gateway_response = json.dumps({
            'status': status.value,
            'timestamp': completed_at.isoformat(),
            'gateway_transaction_id': f'GW_{Payment.generate_transaction_id()}'
        })
        
        payment = Payment(
            transaction_id=Payment.generate_transaction_id(),
            booking_id=booking.id,
            user_id=booking.user_id,
            amount=booking.total_amount,
            currency='BDT',
            payment_method=payment_method,
            status=status,
            payment_details=payment_details,
            gateway_name='DEMO_BD_PAYMENT_GATEWAY',
            gateway_response=gateway_response,
            is_demo=True,
            demo_note='MOCK TRANSACTION - NO REAL MONEY PROCESSED',
            completed_at=completed_at if status == TransactionStatus.SUCCESS else None,
            failure_reason='Insufficient funds' if status == TransactionStatus.FAILED else None,
            failure_code='INSUF_FUNDS' if status == TransactionStatus.FAILED else None
        )
        payments.append(payment)
    
    # Create pending payments for unpaid bookings
    pending_bookings = [b for b in bookings if b.payment_status == PaymentStatus.UNPAID]
    
    for booking in pending_bookings:
        payment_method = random.choice(payment_methods)
        
        payment_details = json.dumps({
            'method': payment_method.value,
            'status': 'awaiting_completion'
        })
        
        payment = Payment(
            transaction_id=Payment.generate_transaction_id(),
            booking_id=booking.id,
            user_id=booking.user_id,
            amount=booking.total_amount,
            currency='BDT',
            payment_method=payment_method,
            status=TransactionStatus.INITIATED,
            payment_details=payment_details,
            gateway_name='DEMO_BD_PAYMENT_GATEWAY',
            is_demo=True,
            demo_note='MOCK TRANSACTION - NO REAL MONEY PROCESSED'
        )
        payments.append(payment)
    
    db.session.add_all(payments)
    db.session.commit()
    
    print(f"[OK] Created {len(payments)} payments")
    return payments


def seed_support_tickets(users):
    """Seed customer support tickets"""
    print("\nSeeding support tickets...")
    tickets = []
    
    customers = [u for u in users if u.role == UserRole.CUSTOMER]
    admins = [u for u in users if u.role == UserRole.ADMIN]
    
    ticket_templates = [
        {
            'title': 'Unable to complete booking',
            'description': 'I am trying to book a seat from Dhaka to Chittagong but payment is failing. Please help.',
            'priority': TicketPriority.HIGH
        },
        {
            'title': 'Refund request for cancelled trip',
            'description': 'My trip was cancelled and I need a refund. Booking reference: {ref}',
            'priority': TicketPriority.URGENT
        },
        {
            'title': 'Change seat selection',
            'description': 'I want to change my seat from {old} to {new}. Is this possible?',
            'priority': TicketPriority.MEDIUM
        },
        {
            'title': 'Question about amenities',
            'description': 'Does the bus from Dhaka to Cox\'s Bazar have WiFi and charging points?',
            'priority': TicketPriority.LOW
        },
        {
            'title': 'Promo code not working',
            'description': 'I tried using promo code WELCOME10 but it shows as invalid. Can you check?',
            'priority': TicketPriority.MEDIUM
        },
        {
            'title': 'Update passenger details',
            'description': 'I need to update the passenger name on my booking. How can I do this?',
            'priority': TicketPriority.MEDIUM
        },
        {
            'title': 'Bus departure time inquiry',
            'description': 'What is the exact departure time for trip TH1045? The website shows conflicting times.',
            'priority': TicketPriority.HIGH
        },
        {
            'title': 'Feedback on service',
            'description': 'I had a great experience with Green Line Paribahan. The service was excellent!',
            'priority': TicketPriority.LOW
        },
        {
            'title': 'Lost item on bus',
            'description': 'I left my bag on the bus from Dhaka to Sylhet yesterday. How can I recover it?',
            'priority': TicketPriority.URGENT
        },
        {
            'title': 'Group booking discount',
            'description': 'Do you offer discounts for group bookings? I need to book 15 seats.',
            'priority': TicketPriority.MEDIUM
        },
    ]
    
    for i, template in enumerate(ticket_templates):
        customer = random.choice(customers)
        
        # Some tickets are resolved, some are in progress, some are open
        status_choices = [
            (TicketStatus.OPEN, None),
            (TicketStatus.IN_PROGRESS, random.choice(admins).id),
            (TicketStatus.RESOLVED, random.choice(admins).id),
            (TicketStatus.CLOSED, random.choice(admins).id),
        ]
        
        status, assigned_to = random.choice(status_choices)
        
        description = template['description']
        if '{ref}' in description:
            description = description.replace('{ref}', Booking.generate_booking_reference())
        if '{old}' in description:
            description = description.replace('{old}', f'A{random.randint(1, 4)}')
        if '{new}' in description:
            description = description.replace('{new}', f'B{random.randint(1, 4)}')
        
        created_at = datetime.utcnow() - timedelta(days=random.randint(0, 30))
        
        ticket = Ticket(
            title=template['title'],
            description=description,
            status=status,
            priority=template['priority'],
            creator_id=customer.id,
            assigned_to_id=assigned_to,
            created_at=created_at,
            resolved_at=created_at + timedelta(days=random.randint(1, 5)) if status in [TicketStatus.RESOLVED, TicketStatus.CLOSED] else None
        )
        tickets.append(ticket)
    
    # Add a few more random tickets
    for i in range(15):
        customer = random.choice(customers)
        template = random.choice(ticket_templates)
        
        status_choices = [
            (TicketStatus.OPEN, None),
            (TicketStatus.IN_PROGRESS, random.choice(admins).id),
            (TicketStatus.RESOLVED, random.choice(admins).id),
        ]
        
        status, assigned_to = random.choice(status_choices)
        
        created_at = datetime.utcnow() - timedelta(days=random.randint(0, 15))
        
        ticket = Ticket(
            title=template['title'],
            description=template['description'],
            status=status,
            priority=template['priority'],
            creator_id=customer.id,
            assigned_to_id=assigned_to,
            created_at=created_at,
            resolved_at=created_at + timedelta(days=random.randint(1, 3)) if status == TicketStatus.RESOLVED else None
        )
        tickets.append(ticket)
    
    db.session.add_all(tickets)
    db.session.commit()
    
    print(f"[OK] Created {len(tickets)} support tickets")
    return tickets


def print_summary(users, promo_codes, trips, seats, bookings, payments, tickets):
    """Print summary of seeded data"""
    print("\n" + "="*60)
    print("DATABASE SEEDING COMPLETED SUCCESSFULLY!")
    print("="*60)
    
    print("\n[DATA SUMMARY]")
    print(f"   Users: {len(users)}")
    print(f"     - Admins: {len([u for u in users if u.role == UserRole.ADMIN])}")
    print(f"     - Customers: {len([u for u in users if u.role == UserRole.CUSTOMER])}")
    print(f"   Promo Codes: {len(promo_codes)}")
    print(f"   Trips: {len(trips)}")
    print(f"   Seats: {len(seats)}")
    print(f"   Bookings: {len(bookings)}")
    print(f"   Payments: {len(payments)}")
    print(f"   Support Tickets: {len(tickets)}")
    
    print("\n[TEST ACCOUNTS]")
    print("   Admin:")
    print("     Email: admin@tickethub.bd")
    print("     Username: admin")
    print("     Password: admin123")
    print("\n   Customer:")
    print("     Email: rafiq.rahman@gmail.com")
    print("     Username: rafiq_rahman")
    print("     Password: customer123")
    
    print("\n[SAMPLE PROMO CODES]")
    active_promos = [p for p in promo_codes if p.is_active and p.valid_until > datetime.utcnow()]
    for promo in active_promos[:3]:
        print(f"     {promo.code}: {promo.discount_percentage}% off - {promo.description}")
    
    print("\n[TRIP STATISTICS]")
    print(f"     Scheduled: {len([t for t in trips if t.status == TripStatus.SCHEDULED])}")
    print(f"     Boarding: {len([t for t in trips if t.status == TripStatus.BOARDING])}")
    print(f"     In Transit: {len([t for t in trips if t.status == TripStatus.IN_TRANSIT])}")
    print(f"     Completed: {len([t for t in trips if t.status == TripStatus.COMPLETED])}")
    
    print("\n[PAYMENT STATISTICS]")
    print(f"     Successful: {len([p for p in payments if p.status == TransactionStatus.SUCCESS])}")
    print(f"     Failed: {len([p for p in payments if p.status == TransactionStatus.FAILED])}")
    print(f"     Pending: {len([p for p in payments if p.status == TransactionStatus.INITIATED])}")
    
    print("\n" + "="*60)


def main():
    """Main function to seed the database"""
    print("="*60)
    print("FastBus Database Seeding Script")
    print("Bangladesh-Specific Sample Data")
    print("="*60)
    
    # Create Flask app context
    app = create_app(os.getenv('FLASK_ENV', 'development'))
    
    with app.app_context():
        # Check if running in non-interactive mode (Docker/CI)
        is_non_interactive = not os.isatty(0) or os.getenv('SEED_DATABASE') == 'true'
        
        if not is_non_interactive:
            # Confirm before clearing database
            print("\n[WARNING] This will clear all existing data in the database!")
            response = input("Do you want to continue? (yes/no): ")
            
            if response.lower() not in ['yes', 'y']:
                print("Seeding cancelled.")
                return
        else:
            print("\n[INFO] Running in non-interactive mode - proceeding with seeding automatically...")
        
        # Clear existing data
        clear_database()
        
        # Seed data in order (respecting foreign key constraints)
        users = seed_users()
        promo_codes = seed_promo_codes()
        trips = seed_trips()
        seats = seed_seats(trips)
        bookings = seed_bookings(users, trips, promo_codes)
        payments = seed_payments(bookings)
        tickets = seed_support_tickets(users)
        
        # Print summary
        print_summary(users, promo_codes, trips, seats, bookings, payments, tickets)
        
        print("\n[SUCCESS] Database seeding completed successfully!")
        print("   You can now start using the application with sample data.\n")


if __name__ == '__main__':
    main()

