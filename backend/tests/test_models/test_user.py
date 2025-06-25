import pytest
from sqlalchemy.exc import IntegrityError
from app.models.user import User
from app.api.auth import get_password_hash, verify_password

class TestUserModel:
    """Test cases for User model"""
    
    def test_create_user(self, test_db, test_user_data):
        """Test creating a user"""
        user = User(
            username=test_user_data["username"],
            email=test_user_data["email"],
            hashed_password=get_password_hash(test_user_data["password"]),
            full_name=test_user_data["full_name"]
        )
        
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        assert user.id is not None
        assert user.username == test_user_data["username"]
        assert user.email == test_user_data["email"]
        assert user.full_name == test_user_data["full_name"]
        assert user.is_active is True
        assert user.is_admin is False
        assert user.created_at is not None
    
    def test_user_password_hashing(self, test_db):
        """Test password hashing and verification"""
        password = "test_password_123"
        hashed = get_password_hash(password)
        
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hashed
        )
        
        test_db.add(user)
        test_db.commit()
        
        # Verify password
        assert verify_password(password, user.hashed_password)
        assert not verify_password("wrong_password", user.hashed_password)
    
    def test_unique_username_constraint(self, test_db, test_user_data):
        """Test that username must be unique"""
        # Create first user
        user1 = User(
            username=test_user_data["username"],
            email="user1@example.com",
            hashed_password=get_password_hash("password1")
        )
        test_db.add(user1)
        test_db.commit()
        
        # Try to create second user with same username
        user2 = User(
            username=test_user_data["username"],  # Same username
            email="user2@example.com",
            hashed_password=get_password_hash("password2")
        )
        test_db.add(user2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_unique_email_constraint(self, test_db, test_user_data):
        """Test that email must be unique"""
        # Create first user
        user1 = User(
            username="user1",
            email=test_user_data["email"],
            hashed_password=get_password_hash("password1")
        )
        test_db.add(user1)
        test_db.commit()
        
        # Try to create second user with same email
        user2 = User(
            username="user2",
            email=test_user_data["email"],  # Same email
            hashed_password=get_password_hash("password2")
        )
        test_db.add(user2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_user_defaults(self, test_db):
        """Test default values for user fields"""
        user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=get_password_hash("password")
        )
        
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        assert user.is_active is True
        assert user.is_admin is False
        assert user.full_name is None
        assert user.github_token is None
    
    def test_user_github_token(self, test_db, test_user_data):
        """Test storing GitHub token"""
        user = User(
            username=test_user_data["username"],
            email=test_user_data["email"],
            hashed_password=get_password_hash(test_user_data["password"]),
            github_token=test_user_data["github_token"]
        )
        
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        assert user.github_token == test_user_data["github_token"]
    
    def test_admin_user(self, test_db):
        """Test admin user creation"""
        admin = User(
            username="admin",
            email="admin@example.com",
            hashed_password=get_password_hash("admin_password"),
            is_admin=True
        )
        
        test_db.add(admin)
        test_db.commit()
        test_db.refresh(admin)
        
        assert admin.is_admin is True
        assert admin.is_active is True
    
    def test_inactive_user(self, test_db):
        """Test inactive user"""
        user = User(
            username="inactive_user",
            email="inactive@example.com",
            hashed_password=get_password_hash("password"),
            is_active=False
        )
        
        test_db.add(user)
        test_db.commit()
        test_db.refresh(user)
        
        assert user.is_active is False
    
    def test_user_str_representation(self, test_db, test_user_data):
        """Test user string representation"""
        user = User(
            username=test_user_data["username"],
            email=test_user_data["email"],
            hashed_password=get_password_hash(test_user_data["password"]),
            full_name=test_user_data["full_name"]
        )
        
        # The User model should have a meaningful string representation
        # This will pass if __str__ or __repr__ is properly implemented
        str_repr = str(user)
        assert test_user_data["username"] in str_repr or test_user_data["email"] in str_repr