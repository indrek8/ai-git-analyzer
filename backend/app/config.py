from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql://postgres:password@postgres:5432/git_analyzer"
    
    # Redis
    redis_url: str = "redis://redis:6379/0"
    
    # Security
    secret_key: str = "your-secret-key-change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    
    # API Keys
    openai_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    
    # GitHub Integration
    github_client_id: Optional[str] = None
    github_client_secret: Optional[str] = None
    github_oauth_redirect_uri: str = "http://localhost:8000/api/github/oauth/callback"
    github_oauth_scopes: str = "repo,read:org,read:user,user:email"
    
    # GitLab Integration
    gitlab_client_id: Optional[str] = None
    gitlab_client_secret: Optional[str] = None
    
    # Application
    debug: bool = True
    log_level: str = "INFO"
    frontend_url: str = "http://localhost:3000"
    
    class Config:
        env_file = ".env"

settings = Settings()