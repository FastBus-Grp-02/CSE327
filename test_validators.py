import pytest
from app.utils.validators import (
    validate_email,
    validate_password,
    validate_username,
    validate_required_fields,
    validate_phone_number,
    validate_seat_selection
)


class TestValidateEmail:
    def test_valid_email(self):
        assert validate_email('test@example.com') is True
        assert validate_email('user.name@domain.co.uk') is True
        assert validate_email('user+tag@example.com') is True
    
    def test_invalid_email(self):
        assert validate_email('invalid-email') is False
        assert validate_email('@example.com') is False
        assert validate_email('user@') is False
        assert validate_email('user@domain') is False
        assert validate_email('') is False
        assert validate_email('user name@example.com') is False


class TestValidatePassword:
    def test_valid_password(self):
        is_valid, message = validate_password('TestPass123')
        assert is_valid is True
        
        is_valid, message = validate_password('SecureP@ss1')
        assert is_valid is True
    
    def test_password_too_short(self):
        is_valid, message = validate_password('Short1A')
        assert is_valid is False
        assert 'at least 8 characters' in message.lower()
    
    def test_password_no_uppercase(self):
        is_valid, message = validate_password('testpass123')
        assert is_valid is False
        assert 'uppercase' in message.lower()
    
    def test_password_no_lowercase(self):
        is_valid, message = validate_password('TESTPASS123')
        assert is_valid is False
        assert 'lowercase' in message.lower()
    
    def test_password_no_digit(self):
        is_valid, message = validate_password('TestPassword')
        assert is_valid is False
        assert 'digit' in message.lower()


class TestValidateUsername:
    def test_valid_username(self):
        is_valid, message = validate_username('validuser')
        assert is_valid is True
        
        is_valid, message = validate_username('user_123')
        assert is_valid is True
        
        is_valid, message = validate_username('ABC')
        assert is_valid is True
    
    def test_username_too_short(self):
        is_valid, message = validate_username('ab')
        assert is_valid is False
        assert 'between 3 and 80' in message.lower()
    
    def test_username_too_long(self):
        is_valid, message = validate_username('a' * 81)
        assert is_valid is False
        assert 'between 3 and 80' in message.lower()
    
    def test_username_invalid_characters(self):
        is_valid, message = validate_username('user-name')
        assert is_valid is False
        assert 'letters, numbers, and underscores' in message.lower()
        
        is_valid, message = validate_username('user@name')
        assert is_valid is False
        
        is_valid, message = validate_username('user name')
        assert is_valid is False


class TestValidateRequiredFields:
    def test_all_fields_present(self):
        data = {
            'field1': 'value1',
            'field2': 'value2',
            'field3': 'value3'
        }
        required = ['field1', 'field2', 'field3']
        
        is_valid, message = validate_required_fields(data, required)
        assert is_valid is True
    
    def test_missing_fields(self):
        data = {
            'field1': 'value1',
            'field3': 'value3'
        }
        required = ['field1', 'field2', 'field3']
        
        is_valid, message = validate_required_fields(data, required)
        assert is_valid is False
        assert 'field2' in message
    
    def test_empty_field_value(self):
        data = {
            'field1': 'value1',
            'field2': '',
            'field3': 'value3'
        }
        required = ['field1', 'field2', 'field3']
        
        is_valid, message = validate_required_fields(data, required)
        assert is_valid is False
        assert 'field2' in message
    
    def test_none_field_value(self):
        data = {
            'field1': 'value1',
            'field2': None,
            'field3': 'value3'
        }
        required = ['field1', 'field2', 'field3']
        
        is_valid, message = validate_required_fields(data, required)
        assert is_valid is False


class TestValidatePhoneNumber:
    def test_valid_phone_number(self):
        is_valid, message = validate_phone_number('+1234567890')
        assert is_valid is True
        
        is_valid, message = validate_phone_number('1234567890')
        assert is_valid is True
        
        is_valid, message = validate_phone_number('(123) 456-7890')
        assert is_valid is True
        
        is_valid, message = validate_phone_number('+1 (123) 456-7890')
        assert is_valid is True
    
    def test_phone_number_too_short(self):
        is_valid, message = validate_phone_number('123456789')
        assert is_valid is False
        assert 'between 10 and 15' in message.lower()
    
    def test_phone_number_too_long(self):
        is_valid, message = validate_phone_number('1234567890123456')
        assert is_valid is False
        assert 'between 10 and 15' in message.lower()
    
    def test_phone_number_invalid_characters(self):
        is_valid, message = validate_phone_number('123-456-ABCD')
        assert is_valid is False
        assert 'digits' in message.lower()


class TestValidateSeatSelection:
    def test_valid_seat_selection(self):
        is_valid, message = validate_seat_selection([1, 2, 3])
        assert is_valid is True
        
        is_valid, message = validate_seat_selection([5])
        assert is_valid is True
    
    def test_seat_selection_not_list(self):
        is_valid, message = validate_seat_selection('not a list')
        assert is_valid is False
        assert 'must be provided as a list' in message.lower()
    
    def test_seat_selection_empty(self):
        is_valid, message = validate_seat_selection([])
        assert is_valid is False
        assert 'at least one seat' in message.lower()
    
    def test_seat_selection_duplicates(self):
        is_valid, message = validate_seat_selection([1, 2, 2, 3])
        assert is_valid is False
        assert 'duplicate' in message.lower()

