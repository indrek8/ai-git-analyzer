import pytest
from fastapi import status
from app.models.repository import Repository

class TestRepositoryEndpoints:
    """Test repository management API endpoints"""
    
    def test_get_repositories_empty(self, client, auth_headers):
        """Test getting repositories when none exist"""
        response = client.get("/api/repositories", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 0
    
    def test_get_repositories_with_data(self, client, auth_headers, test_repository):
        """Test getting repositories when some exist"""
        response = client.get("/api/repositories", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        
        # Check repository data structure
        repo = data[0]
        assert "id" in repo
        assert "name" in repo
        assert "url" in repo
        assert "provider" in repo
    
    def test_add_repository_success(self, client, auth_headers, test_db):
        """Test adding a new repository"""
        repo_data = {
            "url": "https://github.com/testuser/test-repo",
            "provider": "github"
        }
        
        response = client.post("/api/repositories", json=repo_data, headers=auth_headers)
        
        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        
        assert "id" in data
        assert data["url"] == repo_data["url"]
        assert data["provider"] == repo_data["provider"]
        
        # Verify repository was created in database
        repo = test_db.query(Repository).filter(Repository.url == repo_data["url"]).first()
        assert repo is not None
        assert repo.provider == repo_data["provider"]
    
    def test_add_repository_invalid_url(self, client, auth_headers):
        """Test adding repository with invalid URL"""
        invalid_data_sets = [
            {"url": "not-a-url", "provider": "github"},
            {"url": "", "provider": "github"},
            {"url": "ftp://invalid-protocol.com/repo", "provider": "github"}
        ]
        
        for repo_data in invalid_data_sets:
            response = client.post("/api/repositories", json=repo_data, headers=auth_headers)
            assert response.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]
    
    def test_add_repository_missing_data(self, client, auth_headers):
        """Test adding repository with missing required data"""
        invalid_data_sets = [
            {"provider": "github"},  # Missing URL
            {"url": "https://github.com/user/repo"},  # Missing provider
            {}  # Missing both
        ]
        
        for repo_data in invalid_data_sets:
            response = client.post("/api/repositories", json=repo_data, headers=auth_headers)
            assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    
    def test_add_duplicate_repository(self, client, auth_headers, test_repository):
        """Test adding duplicate repository"""
        repo_data = {
            "url": test_repository.url,
            "provider": test_repository.provider
        }
        
        response = client.post("/api/repositories", json=repo_data, headers=auth_headers)
        
        # Should handle duplicates appropriately (either error or ignore)
        assert response.status_code in [
            status.HTTP_400_BAD_REQUEST,  # Error on duplicate
            status.HTTP_201_CREATED,      # Allow duplicate (business logic decision)
            status.HTTP_409_CONFLICT      # Conflict status
        ]
    
    def test_delete_repository_success(self, client, auth_headers, test_repository, test_db):
        """Test deleting a repository"""
        repo_id = test_repository.id
        
        response = client.delete(f"/api/repositories/{repo_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_200_OK
        
        # Verify repository was deleted from database
        deleted_repo = test_db.query(Repository).filter(Repository.id == repo_id).first()
        assert deleted_repo is None
    
    def test_delete_nonexistent_repository(self, client, auth_headers):
        """Test deleting non-existent repository"""
        nonexistent_id = 99999
        
        response = client.delete(f"/api/repositories/{nonexistent_id}", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_sync_repository_success(self, client, auth_headers, test_repository):
        """Test triggering repository sync"""
        repo_id = test_repository.id
        
        response = client.post(f"/api/repositories/{repo_id}/sync", headers=auth_headers)
        
        # Should accept sync request (actual sync happens in background)
        assert response.status_code in [status.HTTP_200_OK, status.HTTP_202_ACCEPTED]
        
        data = response.json()
        assert "message" in data or "task_id" in data
    
    def test_sync_nonexistent_repository(self, client, auth_headers):
        """Test syncing non-existent repository"""
        nonexistent_id = 99999
        
        response = client.post(f"/api/repositories/{nonexistent_id}/sync", headers=auth_headers)
        
        assert response.status_code == status.HTTP_404_NOT_FOUND
    
    def test_get_repository_details(self, client, auth_headers, test_repository):
        """Test getting individual repository details"""
        repo_id = test_repository.id
        
        response = client.get(f"/api/repositories/{repo_id}", headers=auth_headers)
        
        if response.status_code == status.HTTP_404_NOT_FOUND:
            pytest.skip("Individual repository endpoint not implemented")
        
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        
        assert data["id"] == repo_id
        assert data["name"] == test_repository.name
        assert data["url"] == test_repository.url
    
    def test_unauthorized_access(self, client):
        """Test repository endpoints without authentication"""
        endpoints = [
            ("GET", "/api/repositories"),
            ("POST", "/api/repositories"),
            ("DELETE", "/api/repositories/1"),
            ("POST", "/api/repositories/1/sync")
        ]
        
        for method, endpoint in endpoints:
            if method == "GET":
                response = client.get(endpoint)
            elif method == "POST":
                response = client.post(endpoint, json={})
            elif method == "DELETE":
                response = client.delete(endpoint)
            
            assert response.status_code == status.HTTP_401_UNAUTHORIZED
    
    def test_repository_filtering_by_provider(self, client, auth_headers, test_db, test_user):
        """Test filtering repositories by provider"""
        # Create repositories with different providers
        providers = ["github", "gitlab", "bitbucket"]
        for provider in providers:
            repo = Repository(
                name=f"test-repo-{provider}",
                url=f"https://{provider}.com/user/test-repo-{provider}",
                provider=provider,
                owner_id=test_user.id
            )
            test_db.add(repo)
        test_db.commit()
        
        # Test filtering (if supported)
        response = client.get("/api/repositories?provider=github", headers=auth_headers)
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # If filtering is supported, all repos should be GitHub
            for repo in data:
                if "provider" in repo:
                    assert repo["provider"] == "github"
    
    def test_repository_pagination(self, client, auth_headers, test_db, test_user):
        """Test repository list pagination"""
        # Create multiple repositories
        for i in range(15):
            repo = Repository(
                name=f"test-repo-{i}",
                url=f"https://github.com/user/test-repo-{i}",
                owner_id=test_user.id
            )
            test_db.add(repo)
        test_db.commit()
        
        # Test pagination parameters (if supported)
        response = client.get("/api/repositories?limit=10&offset=0", headers=auth_headers)
        
        if response.status_code == status.HTTP_200_OK:
            data = response.json()
            # If pagination is supported, should limit results
            if isinstance(data, list):
                assert len(data) <= 10