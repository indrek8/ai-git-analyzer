from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Float, JSON, Enum
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
from app.database import Base

class CommitType(enum.Enum):
    FEATURE = "feature"
    BUGFIX = "bugfix"
    REFACTOR = "refactor"
    DOCUMENTATION = "documentation"
    TEST = "test"
    STYLE = "style"
    CHORE = "chore"
    HOTFIX = "hotfix"
    MERGE = "merge"
    UNKNOWN = "unknown"

class ComplexityLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    VERY_HIGH = "very_high"

class CommitAnalysis(Base):
    __tablename__ = "commit_analysis"

    id = Column(Integer, primary_key=True, index=True)
    commit_id = Column(Integer, ForeignKey("commits.id"), nullable=False)
    
    # AI Classification
    commit_type = Column(Enum(CommitType), nullable=False)
    complexity_level = Column(Enum(ComplexityLevel), nullable=False)
    effort_score = Column(Float, nullable=False)  # 0-100 scale
    
    # AI-generated insights
    summary = Column(Text)  # AI-generated summary of the commit
    technical_description = Column(Text)  # Technical details
    impact_assessment = Column(Text)  # Potential impact of the changes
    
    # Code quality metrics
    code_quality_score = Column(Float)  # 0-100 scale
    maintainability_score = Column(Float)  # 0-100 scale
    
    # Technology/language breakdown
    languages_used = Column(JSON)  # {"python": 80, "javascript": 20}
    frameworks_detected = Column(JSON)  # Array of detected frameworks
    
    # Risk assessment
    risk_level = Column(String(20))  # low, medium, high
    risk_factors = Column(JSON)  # Array of risk factors
    
    # AI model information
    model_used = Column(String(100))  # Which AI model was used for analysis
    model_version = Column(String(50))
    confidence_score = Column(Float)  # 0-1 scale
    
    # Processing information
    analysis_date = Column(DateTime(timezone=True), server_default=func.now())
    processing_time_ms = Column(Integer)  # Time taken to analyze
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    commit = relationship("Commit", back_populates="analysis")