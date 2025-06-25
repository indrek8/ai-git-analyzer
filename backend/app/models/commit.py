from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.database import Base

class Commit(Base):
    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, index=True)
    
    # Git commit information
    sha = Column(String(40), unique=True, index=True, nullable=False)
    message = Column(Text, nullable=False)
    author_name = Column(String(255), nullable=False)
    author_email = Column(String(255), nullable=False)
    committer_name = Column(String(255))
    committer_email = Column(String(255))
    commit_date = Column(DateTime(timezone=True), nullable=False)
    
    # Repository relationship
    repository_id = Column(Integer, ForeignKey("repositories.id"), nullable=False)
    
    # Developer relationship (resolved from author email/name)
    developer_id = Column(Integer, ForeignKey("developers.id"), nullable=True)
    
    # Commit metrics
    lines_added = Column(Integer, default=0)
    lines_removed = Column(Integer, default=0)
    files_changed = Column(Integer, default=0)
    
    # File changes (JSON array of file paths)
    files_modified = Column(JSON)
    files_added = Column(JSON)
    files_deleted = Column(JSON)
    
    # Branch information
    branch = Column(String(255))
    
    # Parent commits
    parent_shas = Column(JSON)  # Array of parent commit SHAs
    is_merge = Column(Boolean, default=False)
    
    # Processing status
    is_analyzed = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    repository = relationship("Repository", back_populates="commits")
    developer = relationship("Developer", back_populates="commits")
    analysis = relationship("CommitAnalysis", back_populates="commit", uselist=False)