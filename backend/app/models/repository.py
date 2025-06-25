from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class RepositoryProvider(enum.Enum):
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    LOCAL = "local"

class Repository(Base):
    __tablename__ = "repositories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    full_name = Column(String(512), nullable=False)  # e.g., "owner/repo"
    url = Column(String(512), nullable=False)
    clone_url = Column(String(512))
    provider = Column(Enum(RepositoryProvider), nullable=False)
    external_id = Column(String(100))  # Provider's repository ID
    
    # Repository metadata
    description = Column(Text)
    default_branch = Column(String(100), default="main")
    is_private = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    
    # Sync information
    last_synced_at = Column(DateTime(timezone=True))
    sync_status = Column(String(50), default="pending")  # pending, syncing, completed, failed
    sync_error = Column(Text)
    
    # Ownership
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    owner = relationship("User", back_populates="repositories")
    commits = relationship("Commit", back_populates="repository")