from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey
from sqlalchemy.orm import relationship  
from sqlalchemy.sql import func
from app.database import Base

class GitHubUser(Base):
    __tablename__ = "github_users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), nullable=False, index=True)
    github_id = Column(Integer, nullable=False, unique=True)  # GitHub's internal user ID
    
    # User metadata from GitHub API
    display_name = Column(String(255))
    email = Column(String(255))
    avatar_url = Column(String(512))
    bio = Column(Text)
    company = Column(String(255))
    location = Column(String(255))
    blog = Column(String(512))
    
    # Repository stats
    public_repos = Column(Integer, default=0)
    public_gists = Column(Integer, default=0)
    followers = Column(Integer, default=0)
    following = Column(Integer, default=0)
    
    # Monitoring configuration
    is_active = Column(Boolean, default=True)
    auto_sync = Column(Boolean, default=True)  # Auto-sync new repositories
    last_synced_at = Column(DateTime(timezone=True))
    
    # Access control
    added_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    added_by = relationship("User", foreign_keys=[added_by_user_id])
    repository_selections = relationship("RepositorySelection", back_populates="github_user")