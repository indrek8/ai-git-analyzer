import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from fastapi.testclient import TestClient
from faker import Faker

from app.main import app
from app.database import Base, get_db
from app.models.user import User
from app.models.github_user import GitHubUser
from app.models.github_organization import GitHubOrganization
from app.models.repository import Repository
from app.models.repository_selection import RepositorySelection
from app.api.auth import get_password_hash

# Test database URL - using SQLite in memory for fast tests
TEST_DATABASE_URL = "sqlite:///:memory:"

fake = Faker()

@pytest.fixture(scope="session")
def test_engine():
    """Create test database engine"""
    engine = create_engine(
        TEST_DATABASE_URL,
        connect_args={"check_same_thread": False}  # Required for SQLite
    )
    Base.metadata.create_all(bind=engine)
    return engine

@pytest.fixture(scope="function")
def test_db(test_engine):
    """Create test database session"""
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)
    db = TestingSessionLocal()
    
    # Clean up tables before each test
    for table in reversed(Base.metadata.sorted_tables):
        db.execute(table.delete())
    db.commit()
    
    try:
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def client(test_db):
    """Create test client with test database"""
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()

# User fixtures
@pytest.fixture
def test_user_data():
    """Generate test user data"""
    return {
        "username": fake.user_name(),
        "email": fake.email(),
        "password": "testpassword123",
        "full_name": fake.name(),
        "github_token": fake.sha256()[:40]  # Simulate GitHub token
    }

@pytest.fixture
def test_user(test_db, test_user_data):
    """Create a test user in the database"""
    user = User(
        username=test_user_data["username"],
        email=test_user_data["email"],
        hashed_password=get_password_hash(test_user_data["password"]),
        full_name=test_user_data["full_name"],
        github_token=test_user_data["github_token"],
        is_active=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

@pytest.fixture
def admin_user(test_db):
    """Create an admin user for testing"""
    user = User(
        username="admin",
        email="admin@test.com",
        hashed_password=get_password_hash("admin123"),
        full_name="Admin User",
        is_active=True,
        is_admin=True
    )
    test_db.add(user)
    test_db.commit()
    test_db.refresh(user)
    return user

# Authentication fixtures
@pytest.fixture
def auth_token(client, admin_user):
    """Get authentication token for admin user"""
    response = client.post(
        "/api/auth/login",
        data={"username": "admin", "password": "admin123"}
    )
    return response.json()["access_token"]

@pytest.fixture
def auth_headers(auth_token):
    """Get authorization headers with token"""
    return {"Authorization": f"Bearer {auth_token}"}

# GitHub fixtures
@pytest.fixture
def github_user_data():
    """Generate GitHub user test data"""
    return {
        "username": fake.user_name(),
        "github_id": fake.random_int(min=1000, max=999999),
        "display_name": fake.name(),
        "avatar_url": fake.image_url(),
        "public_repos": fake.random_int(min=0, max=100),
        "is_active": True
    }

@pytest.fixture
def test_github_user(test_db, test_user, github_user_data):
    """Create a test GitHub user"""
    github_user = GitHubUser(
        username=github_user_data["username"],
        github_id=github_user_data["github_id"],
        display_name=github_user_data["display_name"],
        avatar_url=github_user_data["avatar_url"],
        public_repos=github_user_data["public_repos"],
        is_active=github_user_data["is_active"],
        added_by_user_id=test_user.id
    )
    test_db.add(github_user)
    test_db.commit()
    test_db.refresh(github_user)
    return github_user

@pytest.fixture
def github_org_data():
    """Generate GitHub organization test data"""
    return {
        "login": fake.company().lower().replace(" ", ""),
        "github_id": fake.random_int(min=1000, max=999999),
        "display_name": fake.company(),
        "avatar_url": fake.image_url(),
        "public_repos": fake.random_int(min=5, max=500),
        "access_token": fake.sha256()[:40]
    }

@pytest.fixture
def test_github_org(test_db, test_user, github_org_data):
    """Create a test GitHub organization"""
    github_org = GitHubOrganization(
        login=github_org_data["login"],
        github_id=github_org_data["github_id"],
        display_name=github_org_data["display_name"],
        avatar_url=github_org_data["avatar_url"],
        public_repos=github_org_data["public_repos"],
        access_token=github_org_data["access_token"],
        added_by_user_id=test_user.id
    )
    test_db.add(github_org)
    test_db.commit()
    test_db.refresh(github_org)
    return github_org

# Repository fixtures
@pytest.fixture
def repository_data():
    """Generate repository test data"""
    return {
        "name": fake.slug(),
        "full_name": f"{fake.user_name()}/{fake.slug()}",
        "description": fake.sentence(),
        "url": fake.url(),
        "external_id": str(fake.random_int(min=1000, max=999999)),
        "is_private": False,
        "provider": "github"
    }

@pytest.fixture
def test_repository(test_db, test_user, repository_data):
    """Create a test repository"""
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
    return repository

# Mock fixtures for external services
@pytest.fixture
def mock_github_api():
    """Mock GitHub API responses"""
    return {
        "user": {
            "login": "testuser",
            "id": 123456,
            "name": "Test User",
            "avatar_url": "https://github.com/images/test.jpg",
            "public_repos": 25
        },
        "repos": [
            {
                "id": 1,
                "name": "test-repo",
                "full_name": "testuser/test-repo",
                "description": "A test repository",
                "html_url": "https://github.com/testuser/test-repo",
                "language": "Python",
                "stargazers_count": 10,
                "forks_count": 2,
                "private": False
            }
        ]
    }

# Test helper functions
def create_test_user(db, **kwargs):
    """Helper function to create test users"""
    defaults = {
        "username": fake.user_name(),
        "email": fake.email(),
        "hashed_password": get_password_hash("testpass"),
        "full_name": fake.name(),
        "is_active": True
    }
    defaults.update(kwargs)
    
    user = User(**defaults)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user