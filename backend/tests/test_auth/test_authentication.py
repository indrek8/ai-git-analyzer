import pytest
from datetime import datetime, timedelta
from jose import jwt
from fastapi import HTTPException, status
from app.api.auth import (
    get_password_hash, 
    verify_password, 
    create_access_token, 
    get_current_user,
    authenticate_user
)
from app.config import settings
from app.models.user import User

class TestPasswordUtils:
    """Test password hashing and verification utilities"""
    
    def test_password_hashing(self):
        """Test password hashing"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        assert hashed != password
        assert len(hashed) > 50  # bcrypt hashes are typically 60 characters
        assert hashed.startswith("$2b$")  # bcrypt prefix
    
    def test_password_verification(self):
        """Test password verification"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        # Correct password should verify
        assert verify_password(password, hashed) is True
        
        # Wrong password should not verify
        assert verify_password("wrong_password", hashed) is False
        assert verify_password("", hashed) is False
    
    def test_different_passwords_different_hashes(self):
        """Test that same password produces different hashes (salt)"""
        password = "same_password"
        hash1 = get_password_hash(password)
        hash2 = get_password_hash(password)
        
        # Hashes should be different due to salt
        assert hash1 != hash2
        
        # But both should verify the same password
        assert verify_password(password, hash1) is True
        assert verify_password(password, hash2) is True

class TestJWTTokens:
    """Test JWT token creation and validation"""
    
    def test_create_access_token(self):
        """Test creating access token"""
        username = "testuser"
        token = create_access_token(data={"sub": username})
        
        assert token is not None
        assert isinstance(token, str)
        assert len(token) > 50  # JWT tokens are fairly long
    
    def test_token_contains_correct_data(self):
        """Test that token contains correct user data"""
        username = "testuser"
        token = create_access_token(data={"sub": username})
        
        # Decode token (without verification for testing)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        
        assert payload["sub"] == username
        assert "exp" in payload  # Expiration should be set
    
    def test_token_expiration(self):
        """Test token expiration time"""
        username = "testuser"
        expires_delta = timedelta(minutes=15)
        token = create_access_token(data={"sub": username}, expires_delta=expires_delta)
        
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        
        # Should expire in approximately 15 minutes
        expected_exp = datetime.utcnow() + expires_delta
        time_diff = abs((exp_datetime - expected_exp).total_seconds())
        
        # Allow 5 seconds tolerance for test execution time
        assert time_diff < 5
    
    def test_token_with_custom_expiration(self):
        """Test token with custom expiration"""
        username = "testuser"
        custom_expires = timedelta(hours=1)
        token = create_access_token(data={"sub": username}, expires_delta=custom_expires)
        
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        exp_timestamp = payload["exp"]
        exp_datetime = datetime.fromtimestamp(exp_timestamp)
        
        # Should expire in approximately 1 hour
        expected_exp = datetime.utcnow() + custom_expires
        time_diff = abs((exp_datetime - expected_exp).total_seconds())
        
        # Allow 5 seconds tolerance
        assert time_diff < 5

class TestUserAuthentication:
    """Test user authentication functions"""
    
    def test_authenticate_user_success(self, test_db, test_user, test_user_data):
        """Test successful user authentication"""
        user = authenticate_user(test_db, test_user_data["username"], test_user_data["password"])
        
        assert user is not None
        assert user.username == test_user_data["username"]
        assert user.email == test_user_data["email"]
    
    def test_authenticate_user_wrong_password(self, test_db, test_user, test_user_data):
        """Test authentication with wrong password"""
        user = authenticate_user(test_db, test_user_data["username"], "wrong_password")
        
        assert user is False
    
    def test_authenticate_user_nonexistent(self, test_db):
        """Test authentication with non-existent user"""
        user = authenticate_user(test_db, "nonexistent_user", "any_password")
        
        assert user is False
    
    def test_authenticate_inactive_user(self, test_db, test_user_data):
        """Test authentication with inactive user"""
        # Create inactive user
        inactive_user = User(
            username=test_user_data["username"] + "_inactive",
            email="inactive@test.com",
            hashed_password=get_password_hash(test_user_data["password"]),
            is_active=False
        )
        test_db.add(inactive_user)
        test_db.commit()
        
        user = authenticate_user(test_db, inactive_user.username, test_user_data["password"])
        
        assert user is False

class TestGetCurrentUser:
    """Test getting current user from token"""
    
    def test_get_current_user_success(self, test_db, test_user):
        """Test getting current user with valid token"""
        # Create token for user
        token = create_access_token(data={"sub": test_user.username})
        
        # Get current user
        current_user = get_current_user(token=token, db=test_db)
        
        assert current_user is not None
        assert current_user.username == test_user.username
        assert current_user.id == test_user.id
    
    def test_get_current_user_invalid_token(self, test_db):
        """Test getting current user with invalid token"""
        invalid_token = "invalid.token.here"
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=invalid_token, db=test_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_expired_token(self, test_db, test_user):
        """Test getting current user with expired token"""
        # Create expired token
        expired_delta = timedelta(minutes=-1)  # Expired 1 minute ago
        expired_token = create_access_token(
            data={"sub": test_user.username}, 
            expires_delta=expired_delta
        )
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=expired_token, db=test_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_nonexistent_user(self, test_db):
        """Test getting current user for non-existent user"""
        # Create token for non-existent user
        token = create_access_token(data={"sub": "nonexistent_user"})
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=test_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_inactive_user(self, test_db, test_user_data):
        """Test getting current user for inactive user"""
        # Create inactive user
        inactive_user = User(
            username=test_user_data["username"] + "_inactive",
            email="inactive@test.com",
            hashed_password=get_password_hash(test_user_data["password"]),
            is_active=False
        )
        test_db.add(inactive_user)
        test_db.commit()
        
        # Create token for inactive user
        token = create_access_token(data={"sub": inactive_user.username})
        
        with pytest.raises(HTTPException) as exc_info:
            get_current_user(token=token, db=test_db)
        
        assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_get_current_user_malformed_token(self, test_db):
        """Test getting current user with malformed token"""
        malformed_tokens = [
            "",
            "not.a.token",
            "eyJ0eXAiOiJKV1QiLCJhbGciOiJIUzI1NiJ9",  # Incomplete token
            "bearer_token_without_bearer_prefix"
        ]
        
        for token in malformed_tokens:
            with pytest.raises(HTTPException) as exc_info:
                get_current_user(token=token, db=test_db)
            
            assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED