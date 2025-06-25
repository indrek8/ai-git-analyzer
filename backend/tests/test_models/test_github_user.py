import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models.github_user import GitHubUser
from app.models.user import User
from app.api.auth import get_password_hash

class TestGitHubUserModel:
    """Test cases for GitHubUser model"""
    
    def test_create_github_user(self, test_db, test_user, github_user_data):
        """Test creating a GitHub user"""
        github_user = GitHubUser(
            username=github_user_data["username"],
            github_id=github_user_data["github_id"],
            display_name=github_user_data["display_name"],
            avatar_url=github_user_data["avatar_url"],
            public_repos=github_user_data["public_repos"],
            added_by_user_id=test_user.id
        )
        
        test_db.add(github_user)
        test_db.commit()
        test_db.refresh(github_user)
        
        assert github_user.id is not None
        assert github_user.username == github_user_data["username"]
        assert github_user.github_id == github_user_data["github_id"]
        assert github_user.display_name == github_user_data["display_name"]
        assert github_user.avatar_url == github_user_data["avatar_url"]
        assert github_user.public_repos == github_user_data["public_repos"]
        assert github_user.is_active is True
        assert github_user.added_by_user_id == test_user.id
        assert github_user.created_at is not None
    
    def test_github_user_defaults(self, test_db, test_user):
        """Test default values for GitHub user fields"""
        github_user = GitHubUser(
            username="testuser",
            github_id=123456,
            added_by_user_id=test_user.id
        )
        
        test_db.add(github_user)
        test_db.commit()
        test_db.refresh(github_user)
        
        assert github_user.is_active is True
        assert github_user.display_name is None
        assert github_user.avatar_url is None
        assert github_user.public_repos == 0
        assert github_user.last_synced_at is None
    
    def test_unique_github_id_constraint(self, test_db, test_user, github_user_data):
        """Test that github_id must be unique"""
        # Create first GitHub user
        github_user1 = GitHubUser(
            username="user1",
            github_id=github_user_data["github_id"],
            added_by_user_id=test_user.id
        )
        test_db.add(github_user1)
        test_db.commit()
        
        # Try to create second GitHub user with same github_id
        github_user2 = GitHubUser(
            username="user2",
            github_id=github_user_data["github_id"],  # Same github_id
            added_by_user_id=test_user.id
        )
        test_db.add(github_user2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_unique_username_constraint(self, test_db, test_user, github_user_data):
        """Test that username must be unique among GitHub users"""
        # Create first GitHub user
        github_user1 = GitHubUser(
            username=github_user_data["username"],
            github_id=123456,
            added_by_user_id=test_user.id
        )
        test_db.add(github_user1)
        test_db.commit()
        
        # Try to create second GitHub user with same username
        github_user2 = GitHubUser(
            username=github_user_data["username"],  # Same username
            github_id=789012,
            added_by_user_id=test_user.id
        )
        test_db.add(github_user2)
        
        with pytest.raises(IntegrityError):
            test_db.commit()
    
    def test_github_user_relationship_with_user(self, test_db, test_user, github_user_data):
        """Test relationship between GitHubUser and User"""
        github_user = GitHubUser(
            username=github_user_data["username"],
            github_id=github_user_data["github_id"],
            added_by_user_id=test_user.id
        )
        
        test_db.add(github_user)
        test_db.commit()
        test_db.refresh(github_user)
        
        # Test foreign key relationship
        assert github_user.added_by_user_id == test_user.id
        
        # Test that we can access the related user
        # Note: This requires the relationship to be properly defined in the model
        if hasattr(github_user, 'added_by'):
            assert github_user.added_by.username == test_user.username
    
    def test_update_sync_timestamp(self, test_db, test_github_user):
        """Test updating last_synced_at timestamp"""
        original_sync_time = test_github_user.last_synced_at
        
        # Update sync timestamp
        sync_time = datetime.utcnow()
        test_github_user.last_synced_at = sync_time
        test_db.commit()
        test_db.refresh(test_github_user)
        
        assert test_github_user.last_synced_at == sync_time
        assert test_github_user.last_synced_at != original_sync_time
    
    def test_update_repository_count(self, test_db, test_github_user):
        """Test updating public repository count"""
        original_count = test_github_user.public_repos
        new_count = 50
        
        test_github_user.public_repos = new_count
        test_db.commit()
        test_db.refresh(test_github_user)
        
        assert test_github_user.public_repos == new_count
        assert test_github_user.public_repos != original_count
    
    def test_deactivate_github_user(self, test_db, test_github_user):
        """Test deactivating a GitHub user"""
        assert test_github_user.is_active is True
        
        test_github_user.is_active = False
        test_db.commit()
        test_db.refresh(test_github_user)
        
        assert test_github_user.is_active is False
    
    def test_github_user_profile_update(self, test_db, test_github_user):
        """Test updating GitHub user profile information"""
        new_display_name = "Updated Display Name"
        new_avatar_url = "https://github.com/images/updated.jpg"
        
        test_github_user.display_name = new_display_name
        test_github_user.avatar_url = new_avatar_url
        test_db.commit()
        test_db.refresh(test_github_user)
        
        assert test_github_user.display_name == new_display_name
        assert test_github_user.avatar_url == new_avatar_url
    
    def test_delete_github_user(self, test_db, test_github_user):
        """Test deleting a GitHub user"""
        github_user_id = test_github_user.id
        
        test_db.delete(test_github_user)
        test_db.commit()
        
        # Verify the user is deleted
        deleted_user = test_db.query(GitHubUser).filter(GitHubUser.id == github_user_id).first()
        assert deleted_user is None