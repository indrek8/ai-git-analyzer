from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class SelectionStatus(enum.Enum):
    SELECTED = "selected"        # User wants to monitor this repo
    DESELECTED = "deselected"    # User explicitly doesn't want to monitor
    PENDING = "pending"          # Not yet decided
    SYNCED = "synced"           # Repository has been added to monitoring

class RepositorySelection(Base):
    __tablename__ = "repository_selections"

    id = Column(Integer, primary_key=True, index=True)
    
    # Repository information from GitHub API
    github_repo_id = Column(Integer, nullable=False)  # GitHub's internal repo ID
    name = Column(String(255), nullable=False)
    full_name = Column(String(512), nullable=False)  # e.g., "owner/repo"
    description = Column(Text)
    url = Column(String(512), nullable=False)
    clone_url = Column(String(512))
    default_branch = Column(String(100), default="main")
    is_private = Column(Boolean, default=False)
    is_fork = Column(Boolean, default=False)
    is_archived = Column(Boolean, default=False)
    
    # Repository stats
    stargazers_count = Column(Integer, default=0)
    watchers_count = Column(Integer, default=0) 
    forks_count = Column(Integer, default=0)
    size = Column(Integer, default=0)  # Size in KB
    language = Column(String(100))
    
    # Selection status
    status = Column(Enum(SelectionStatus), default=SelectionStatus.PENDING)
    selected_at = Column(DateTime(timezone=True))
    
    # Link to actual repository record (when synced)
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=True)
    
    # Source - either from a GitHub user or organization
    github_user_id = Column(Integer, ForeignKey("github_users.id"), nullable=True)
    github_organization_id = Column(Integer, ForeignKey("github_organizations.id"), nullable=True)
    
    # Who made the selection
    selected_by_user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    repository = relationship("Repository", back_populates="selection")
    github_user = relationship("GitHubUser", back_populates="repository_selections")
    github_organization = relationship("GitHubOrganization", back_populates="repository_selections")  
    selected_by = relationship("User", foreign_keys=[selected_by_user_id])
    
    # Ensure each repo can only be selected once per source
    __table_args__ = (
        # Unique constraint to prevent duplicate selections
        # Either github_user_id or github_organization_id should be set, not both
    )