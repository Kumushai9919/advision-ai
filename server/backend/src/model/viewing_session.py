from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from ..database.core import Base


class ViewingSession(Base):
    """Store individual viewing sessions for viewers"""
    __tablename__ = "viewing_sessions"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete='CASCADE'), nullable=False, index=True)
    face_id = Column(UUID(as_uuid=True), ForeignKey("faces.id", ondelete='CASCADE'), nullable=True, index=True)
    
    # Session timing data
    start_time = Column(DateTime, nullable=False, index=True)
    end_time = Column(DateTime, nullable=False)
    duration = Column(Float, nullable=False)  # Duration in seconds
    
    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # Optional: store any additional session metadata
    session_metadata = Column(String, nullable=True)  # Can store JSON string if needed
    
    # Relationships
    user = relationship("User", back_populates="viewing_sessions")
    face = relationship("Face", back_populates="viewing_sessions")
    
    # Indexes for efficient queries
    __table_args__ = (
        Index('idx_user_start_time', 'user_id', 'start_time'),
        Index('idx_face_session', 'face_id', 'start_time'),
        Index('idx_created_at', 'created_at'),
    )
    
    def __repr__(self):
        return f"<ViewingSession(id={self.id}, user_id={self.user_id}, start={self.start_time}, duration={self.duration})>"
