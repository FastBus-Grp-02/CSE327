import re
from flask import jsonify


def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None


def validate_password(password):
    """
    Validate password strength:
    - At least 8 characters
    - Contains at least one uppercase letter
    - Contains at least one lowercase letter
    - Contains at least one digit
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one digit"
    
    return True, "Password is valid"


def validate_username(username):
    """
    Validate username:
    - 3-80 characters
    - Alphanumeric and underscores only
    """
    if len(username) < 3 or len(username) > 80:
        return False, "Username must be between 3 and 80 characters"
    
    if not re.match(r'^[a-zA-Z0-9_]+$', username):
        return False, "Username can only contain letters, numbers, and underscores"
    
    return True, "Username is valid"


def validate_required_fields(data, required_fields):
    """Validate that all required fields are present"""
    missing_fields = [field for field in required_fields if field not in data or not data[field]]
    
    if missing_fields:
        return False, f"Missing required fields: {', '.join(missing_fields)}"
    
    return True, "All required fields present"


def validate_phone_number(phone):
    """
    Validate phone number format
    - 10-15 digits
    - May contain +, -, spaces, and parentheses
    """
    # Remove formatting characters
    digits_only = re.sub(r'[\s\-\(\)\+]', '', phone)
    
    if len(digits_only) < 10 or len(digits_only) > 15:
        return False, "Phone number must be between 10 and 15 digits"
    
    if not digits_only.isdigit():
        return False, "Phone number can only contain digits and formatting characters (+, -, spaces, parentheses)"
    
    return True, "Phone number is valid"


def validate_seat_selection(seat_ids):
    """
    Validate seat selection
    - Must be a list
    - Must contain at least one seat
    - No duplicate seats
    """
    if not isinstance(seat_ids, list):
        return False, "Seat IDs must be provided as a list"
    
    if len(seat_ids) == 0:
        return False, "At least one seat must be selected"
    
    if len(seat_ids) != len(set(seat_ids)):
        return False, "Duplicate seat IDs are not allowed"
    
    return True, "Seat selection is valid"
