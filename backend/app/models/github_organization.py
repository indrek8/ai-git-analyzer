from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class GitHubOrganization(Base):
    __tablename__ = "github_organizations"

    id = Column(Integer, primary_key=True, index=True)
    login = Column(String(255), nullable=False, index=True)  # GitHub org login name
    github_id = Column(Integer, nullable=False, unique=True)  # GitHub's internal org ID
    
    # Organization metadata from GitHub API
    display_name = Column(String(255))
    description = Column(Text)
    email = Column(String(255))
    avatar_url = Column(String(512))
    blog = Column(String(512))
    location = Column(String(255))
    company = Column(String(255))
    
    # Organization stats
    public_repos = Column(Integer, default=0)
    public_gists = Column(Integer, default=0)
    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    
    # Access tokens for private repositories (OAuth)
    access_token = Column(Text)  # Encrypted OAuth token
    token_expires_at = Column(DateTime(timezone=True))
    refresh_token = Column(Text)  # For token refresh
    scopes = Column(Text)  # Comma-separated list of granted scopes
    
    # Monitoring configuration
    is_active = Column(Boolean, default=True)
    auto_sync = Column(Boolean, default=True)
    last_synced_at = Column(DateTime(timezone=True))
    
    # Access control
    added_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    added_by = relationship("User", foreign_keys=[added_by_user_id])
    repository_selections = relationship("RepositorySelection", back_populates="github_organization")