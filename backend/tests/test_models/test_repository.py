import pytest
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from app.models.repository import Repository
from app.models.user import User

class TestRepositoryModel:
    """Test cases for Repository model"""
    
    def test_create_repository(self, test_db, test_user, repository_data):
        """Test creating a repository"""
        from app.models.repository import RepositoryProvider
        repository = Repository(
            name=repository_data["name"],
            full_name=repository_data["full_name"],
            description=repository_data["description"],
            url=repository_data["url"],
            external_id=repository_data["external_id"],
            is_private=repository_data["is_private"],
            provider=RepositoryProvider.GITHUB,
            owner_id=test_user.id
        )
        
        test_db.add(repository)
        test_db.commit()
        test_db.refresh(repository)
        
        assert repository.id is not None
        assert repository.name == repository_data["name"]
        assert repository.full_name == repository_data["full_name"]
        assert repository.description == repository_data["description"]
        assert repository.url == repository_data["url"]
        assert repository.external_id == repository_data["external_id"]
        assert repository.is_private == repository_data["is_private"]
        assert repository.provider == RepositoryProvider.GITHUB
        assert repository.owner_id == test_user.id
        assert repository.created_at is not None
    
    def test_repository_defaults(self, test_db, test_user):
        """Test default values for repository fields"""
        from app.models.repository import RepositoryProvider
        repository = Repository(
            name="test-repo",
            full_name="user/test-repo",
            url="https://github.com/user/test-repo",
            provider=RepositoryProvider.GITHUB,
            owner_id=test_user.id
        )
        
        test_db.add(repository)
        test_db.commit()
        test_db.refresh(repository)
        
        assert repository.description is None
        assert repository.default_branch == "main"
        assert repository.is_private is False
        assert repository.provider == RepositoryProvider.GITHUB
        assert repository.is_active is True
        assert repository.last_synced_at is None
        assert repository.sync_status == "pending"
    
    def test_unique_external_id_constraint(self, test_db, test_user, repository_data):
        """Test that external_id can be duplicate (no unique constraint)"""
        from app.models.repository import RepositoryProvider
        # Create first repository
        repo1 = Repository(
            name="repo1",
            full_name="user/repo1",
            url="https://github.com/user/repo1",
            external_id=repository_data["external_id"],
            provider=RepositoryProvider.GITHUB,
            owner_id=test_user.id
        )
        test_db.add(repo1)
        test_db.commit()
        
        # Create second repository with same external_id (should be allowed)
        repo2 = Repository(
            name="repo2",
            full_name="user/repo2",
            url="https://github.com/user/repo2",
            external_id=repository_data["external_id"],  # Same external_id
            provider=RepositoryProvider.GITHUB,
            owner_id=test_user.id
        )
        test_db.add(repo2)
        test_db.commit()  # Should not raise an error
        
        # Verify both repositories exist
        repos = test_db.query(Repository).filter(Repository.external_id == repository_data["external_id"]).all()
        assert len(repos) == 2
    
    def test_repository_relationship_with_user(self, test_db, test_user, repository_data):
        """Test relationship between Repository and User"""
        repository = Repository(
            name=repository_data["name"],
            url=repository_data["url"],
            owner_id=test_user.id
        )
        
        test_db.add(repository)
        test_db.commit()
        test_db.refresh(repository)
        
        # Test foreign key relationship
        assert repository.owner_id == test_user.id
        
        # Test that we can access the related user
        if hasattr(repository, 'owner'):
            assert repository.owner.username == test_user.username
    
    def test_repository_sync_status(self, test_db, test_repository):
        """Test repository sync status tracking"""
        # Initially not synced
        assert test_repository.last_synced_at is None
        
        # Update sync timestamp
        sync_time = datetime.utcnow()
        test_repository.last_synced_at = sync_time
        test_repository.sync_status = "completed"
        test_db.commit()
        test_db.refresh(test_repository)
        
        assert test_repository.last_synced_at == sync_time
        assert test_repository.sync_status == "completed"
    
    def test_repository_statistics_update(self, test_db, test_repository):
        """Test updating repository statistics"""
        original_stars = test_repository.stars
        original_forks = test_repository.forks
        
        new_stars = 100
        new_forks = 25
        
        test_repository.stars = new_stars
        test_repository.forks = new_forks
        test_db.commit()
        test_db.refresh(test_repository)
        
        assert test_repository.stars == new_stars
        assert test_repository.forks == new_forks
        assert test_repository.stars != original_stars
        assert test_repository.forks != original_forks
    
    def test_repository_language_update(self, test_db, test_repository):
        """Test updating repository language"""
        new_language = "TypeScript"
        
        test_repository.language = new_language
        test_db.commit()
        test_db.refresh(test_repository)
        
        assert test_repository.language == new_language
    
    def test_private_repository(self, test_db, test_user):
        """Test creating a private repository"""
        repository = Repository(
            name="private-repo",
            url="https://github.com/user/private-repo",
            is_private=True,
            owner_id=test_user.id
        )
        
        test_db.add(repository)
        test_db.commit()
        test_db.refresh(repository)
        
        assert repository.is_private is True
    
    def test_deactivate_repository(self, test_db, test_repository):
        """Test deactivating a repository"""
        assert test_repository.is_active is True
        
        test_repository.is_active = False
        test_db.commit()
        test_db.refresh(test_repository)
        
        assert test_repository.is_active is False
    
    def test_different_providers(self, test_db, test_user):
        """Test repositories from different providers"""
        providers = ["github", "gitlab", "bitbucket"]
        
        for provider in providers:
            repository = Repository(
                name=f"repo-{provider}",
                url=f"https://{provider}.com/user/repo-{provider}",
                provider=provider,
                owner_id=test_user.id
            )
            test_db.add(repository)
        
        test_db.commit()
        
        # Verify all repositories were created with correct providers
        repos = test_db.query(Repository).filter(Repository.owner_id == test_user.id).all()
        assert len(repos) == 3
        
        repo_providers = [repo.provider for repo in repos]
        for provider in providers:
            assert provider in repo_providers
    
    def test_repository_full_name_format(self, test_db, test_user):
        """Test repository full name format"""
        repository = Repository(
            name="my-awesome-repo",
            full_name="username/my-awesome-repo",
            url="https://github.com/username/my-awesome-repo",
            owner_id=test_user.id
        )
        
        test_db.add(repository)
        test_db.commit()
        test_db.refresh(repository)
        
        assert "/" in repository.full_name
        assert repository.name in repository.full_name
    
    def test_delete_repository(self, test_db, test_repository):
        """Test deleting a repository"""
        repository_id = test_repository.id
        
        test_db.delete(test_repository)
        test_db.commit()
        
        # Verify the repository is deleted
        deleted_repo = test_db.query(Repository).filter(Repository.id == repository_id).first()
        assert deleted_repo is None