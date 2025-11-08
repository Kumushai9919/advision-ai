from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from ..database.core import Base


class Analytics(Base):
    """Store analytics data for user visits/detections"""
    __tablename__ = "analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'), nullable=False, index=True)
    org_id = Column(String, nullable=False, index=True)
    
    # Visit tracking
    visit_count = Column(Integer, default=0, nullable=False)
    
    # Timestamps
    first_seen = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="analytics")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_user_org', 'user_id', 'org_id'),
        Index('idx_org_visit_count', 'org_id', 'visit_count'),
        Index('idx_last_seen', 'last_seen'),
    )
    
    def __repr__(self):
        return f"<Analytics(id={self.id}, user_id={self.user_id}, org_id={self.org_id}, visit_count={self.visit_count})>"
