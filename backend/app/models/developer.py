from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Developer(Base):
    __tablename__ = "developers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False, index=True)
    
    # Link to user account (optional for external contributors)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    # Git identity information
    git_name = Column(String(255))  # Name as it appears in git commits
    git_email = Column(String(255))  # Email as it appears in git commits
    
    # Metadata
    is_merged = Column(Boolean, default=False)  # If this identity is merged with another
    merged_with_id = Column(Integer, ForeignKey("developers.id"), nullable=True)
    is_active = Column(Boolean, default=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    user = relationship("User", back_populates="developers")
    commits = relationship("Commit", back_populates="developer")
    merged_with = relationship("Developer", remote_side=[id])