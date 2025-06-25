import pytest
from fastapi import status
from app.models.user import User
from app.api.auth import get_password_hash

class TestAuthEndpoints:
    """Test authentication API endpoints"""
    
    def test_login_success(self, client, admin_user):
        """Test successful login"""
        response = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin123"}
        )
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "access_token" in data
        assert "token_type" in data
        assert data["token_type"] == "bearer"
        assert len(data["access_token"]) > 50  # JWT tokens are long
    
    def test_login_invalid_username(self, client):
        """Test login with invalid username"""
        response = client.post(
            "/api/auth/login",
            data={"username": "nonexistent", "password": "password123"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
    
    def test_login_invalid_password(self, client, admin_user):
        """Test login with invalid password"""
        response = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "wrongpassword"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
        data = response.json()
        assert "detail" in data
    
    def test_login_missing_credentials(self, client):
        """Test login with missing credentials"""
        # Missing password
        response = client.post(
            "/api/auth/login",
            data={"username": "admin"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing username
        response = client.post(
            "/api/auth/login",
            data={"password": "password123"}
        )
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        
        # Missing both
        response = client.post("/api/auth/login", data={})
        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_login_inactive_user(self, client, test_db, test_user_data):
        """Test login with inactive user"""
        # Create inactive user
        inactive_user = User(
            username="inactive_user",
            email="inactive@test.com",
            hashed_password=get_password_hash("password123"),
            is_active=False
        )
        test_db.add(inactive_user)
        test_db.commit()
        
        response = client.post(
            "/api/auth/login",
            data={"username": "inactive_user", "password": "password123"}
        )
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_success(self, client, auth_headers):
        """Test getting current user info with valid token"""
        response = client.get("/api/auth/me", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert "id" in data
        assert "username" in data
        assert "email" in data
        assert "is_active" in data
        assert data["username"] == "admin"
        assert data["is_active"] is True
    
    def test_get_current_user_no_token(self, client):
        """Test getting current user without token"""
        response = client.get("/api/auth/me")
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_invalid_token(self, client):
        """Test getting current user with invalid token"""
        headers = {"Authorization": "Bearer invalid_token"}
        response = client.get("/api/auth/me", headers=headers)
        
        assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_malformed_auth_header(self, client):
        """Test getting current user with malformed authorization header"""
        malformed_headers = [
            {"Authorization": "invalid_format"},
            {"Authorization": "Bearer"},  # Missing token
            {"Authorization": "NotBearer token123"},
            {"Authorization": ""}
        ]
        
        for headers in malformed_headers:
            response = client.get("/api/auth/me", headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_register_user_success(self, client, test_db):
        """Test successful user registration"""
        user_data = {
            "username": "newuser",
            "email": "newuser@test.com",
            "password": "newpassword123",
            "full_name": "New User"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        # Check if registration endpoint exists, otherwise skip
        if response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Registration endpoint not implemented")
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert "id" in data
        assert data["username"] == user_data["username"]
        assert data["email"] == user_data["email"]
        assert data["full_name"] == user_data["full_name"]
        assert data["is_active"] is True
        
        # Verify user was created in database
        user = test_db.query(User).filter(User.username == user_data["username"]).first()
        assert user is not None
        assert user.email == user_data["email"]
    
    def test_register_duplicate_username(self, client, admin_user):
        """Test registration with duplicate username"""
        user_data = {
            "username": "admin",  # Already exists
            "email": "newemail@test.com",
            "password": "newpassword123"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        # Skip if registration endpoint doesn't exist
        if response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Registration endpoint not implemented")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_duplicate_email(self, client, admin_user):
        """Test registration with duplicate email"""
        user_data = {
            "username": "newuser",
            "email": "admin@gitanalytics.local",  # Already exists
            "password": "newpassword123"
        }
        
        response = client.post("/api/auth/register", json=user_data)
        
        # Skip if registration endpoint doesn't exist
        if response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Registration endpoint not implemented")
        
        assert response.status_code == status.HTTP_400_BAD_REQUEST
    
    def test_register_invalid_data(self, client):
        """Test registration with invalid data"""
        invalid_data_sets = [
            {"username": "", "email": "test@test.com", "password": "password"},  # Empty username
            {"username": "test", "email": "invalid-email", "password": "password"},  # Invalid email
            {"username": "test", "email": "test@test.com", "password": ""},  # Empty password
            {"username": "test", "email": "test@test.com"},  # Missing password
            {"email": "test@test.com", "password": "password"},  # Missing username
            {"username": "test", "password": "password"},  # Missing email
        ]
        
        for user_data in invalid_data_sets:
            response = client.post("/api/auth/register", json=user_data)
            
            # Skip if registration endpoint doesn't exist
            if response.status_code == status.HTTP_404_NOT_FOUND:
                pytest.skip("Registration endpoint not implemented")
            
            assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

class TestProtectedEndpoints:
    """Test that endpoints requiring authentication are properly protected"""
    
    def test_protected_endpoint_without_auth(self, client):
        """Test accessing protected endpoints without authentication"""
        # These are examples of endpoints that should require authentication
        protected_endpoints = [
            "/api/repositories",
            "/api/github/users",
            "/api/analytics/effort"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint)
            # Should return 401 Unauthorized for protected endpoints
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_protected_endpoint_with_invalid_auth(self, client):
        """Test accessing protected endpoints with invalid authentication"""
        headers = {"Authorization": "Bearer invalid_token"}
        
        protected_endpoints = [
            "/api/repositories",
            "/api/github/users"
        ]
        
        for endpoint in protected_endpoints:
            response = client.get(endpoint, headers=headers)
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_protected_endpoint_with_valid_auth(self, client, auth_headers):
        """Test accessing protected endpoints with valid authentication"""
        # Test that we can access protected endpoints with valid auth
        response = client.get("/api/repositories", headers=auth_headers)
        
        # Should not return 401 (might return 200, 404, or other valid status)
        assert response.status_code != status.HTTP_401_UNAUTHORIZED