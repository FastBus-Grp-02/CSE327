import pytest
from app.models.user import User


class TestSignup:
    def test_successful_signup(self, client):
        response = client.post('/api/auth/signup', json={
            'email': 'newuser@test.com',
            'username': 'newuser',
            'password': 'TestPass123',
            'first_name': 'New',
            'last_name': 'User'
        })
        
        assert response.status_code == 201
        data = response.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['user']['email'] == 'newuser@test.com'
        assert data['user']['username'] == 'newuser'
    
    def test_signup_missing_fields(self, client):
        response = client.post('/api/auth/signup', json={
            'email': 'test@test.com',
            'username': 'testuser'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'error' in data
    
    def test_signup_invalid_email(self, client):
        response = client.post('/api/auth/signup', json={
            'email': 'invalid-email',
            'username': 'testuser',
            'password': 'TestPass123',
            'first_name': 'Test',
            'last_name': 'User'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'email' in data['error'].lower()
    
    def test_signup_weak_password(self, client):
        response = client.post('/api/auth/signup', json={
            'email': 'test@test.com',
            'username': 'testuser',
            'password': 'weak',
            'first_name': 'Test',
            'last_name': 'User'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'password' in data['error'].lower()
    
    def test_signup_duplicate_email(self, client, sample_customer):
        response = client.post('/api/auth/signup', json={
            'email': 'customer@test.com',
            'username': 'uniqueuser',
            'password': 'TestPass123',
            'first_name': 'Test',
            'last_name': 'User'
        })
        
        assert response.status_code == 409
        data = response.get_json()
        assert 'email' in data['error'].lower()
    
    def test_signup_duplicate_username(self, client, sample_customer):
        response = client.post('/api/auth/signup', json={
            'email': 'unique@test.com',
            'username': 'testcustomer',
            'password': 'TestPass123',
            'first_name': 'Test',
            'last_name': 'User'
        })
        
        assert response.status_code == 409
        data = response.get_json()
        assert 'username' in data['error'].lower()
    
    def test_signup_invalid_username(self, client):
        response = client.post('/api/auth/signup', json={
            'email': 'test@test.com',
            'username': 'ab',
            'password': 'TestPass123',
            'first_name': 'Test',
            'last_name': 'User'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'username' in data['error'].lower()


class TestLogin:
    def test_successful_login_with_email(self, client, sample_customer):
        response = client.post('/api/auth/login', json={
            'email': 'customer@test.com',
            'password': 'TestPass123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
        assert data['user']['email'] == 'customer@test.com'
    
    def test_successful_login_with_username(self, client, sample_customer):
        response = client.post('/api/auth/login', json={
            'username': 'testcustomer',
            'password': 'TestPass123'
        })
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
        assert 'refresh_token' in data
    
    def test_login_invalid_credentials(self, client, sample_customer):
        response = client.post('/api/auth/login', json={
            'email': 'customer@test.com',
            'password': 'WrongPassword123'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'credentials' in data['error'].lower()
    
    def test_login_nonexistent_user(self, client):
        response = client.post('/api/auth/login', json={
            'email': 'nonexistent@test.com',
            'password': 'TestPass123'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'credentials' in data['error'].lower()
    
    def test_login_missing_credentials(self, client):
        response = client.post('/api/auth/login', json={
            'email': 'test@test.com'
        })
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'password' in data['error'].lower()
    
    def test_login_inactive_user(self, client, app, sample_customer):
        with app.app_context():
            user = User.query.filter_by(email='customer@test.com').first()
            user.is_active = False
            from app import db
            db.session.commit()
        
        response = client.post('/api/auth/login', json={
            'email': 'customer@test.com',
            'password': 'TestPass123'
        })
        
        assert response.status_code == 403
        data = response.get_json()
        assert 'inactive' in data['error'].lower()


class TestRefreshToken:
    def test_successful_refresh(self, client, customer_refresh_token):
        response = client.post('/api/auth/refresh',
                             headers={'Authorization': f'Bearer {customer_refresh_token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'access_token' in data
    
    def test_refresh_without_token(self, client):
        response = client.post('/api/auth/refresh')
        
        assert response.status_code == 401
    
    def test_refresh_with_access_token(self, client, customer_token):
        response = client.post('/api/auth/refresh',
                             headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code in [401, 422]


class TestGetCurrentUser:
    def test_get_current_user_success(self, client, customer_token):
        response = client.get('/api/auth/me',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert 'user' in data
        assert data['user']['email'] == 'customer@test.com'
    
    def test_get_current_user_without_token(self, client):
        response = client.get('/api/auth/me')
        
        assert response.status_code == 401


class TestVerifyToken:
    def test_verify_token_success(self, client, customer_token):
        response = client.get('/api/auth/verify-token',
                            headers={'Authorization': f'Bearer {customer_token}'})
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['valid'] is True
        assert 'user_id' in data
    
    def test_verify_token_without_token(self, client):
        response = client.get('/api/auth/verify-token')
        
        assert response.status_code == 401


class TestHealthCheck:
    def test_health_check(self, client):
        response = client.get('/api/auth/health')
        
        assert response.status_code == 200
        data = response.get_json()
        assert data['status'] == 'healthy'
        assert 'database' in data


class TestGoogleOAuth:
    def test_google_login_missing_credential(self, client):
        response = client.post('/api/auth/google/login', json={})
        
        assert response.status_code == 400
        data = response.get_json()
        assert 'credential' in data['error'].lower()
    
    def test_google_login_invalid_token(self, client):
        response = client.post('/api/auth/google/login', json={
            'credential': 'invalid_token_here'
        })
        
        assert response.status_code == 401
        data = response.get_json()
        assert 'error' in data
    
    def test_oauth_user_has_no_password(self, client, app):
        """Test that OAuth users are created without passwords"""
        from app import db
        from app.models.user import User, UserRole
        
        # Create an OAuth user
        with app.app_context():
            oauth_user = User(
                email='oauth@test.com',
                username='oauthuser',
                first_name='OAuth',
                last_name='User',
                role=UserRole.CUSTOMER,
                oauth_provider='google',
                oauth_id='google_123456',
                password_hash=None
            )
            db.session.add(oauth_user)
            db.session.commit()
            
            # Verify user has no password
            user = User.query.filter_by(email='oauth@test.com').first()
            assert user.is_oauth_user() is True
            assert user.password_hash is None
            assert user.check_password('any_password') is False
