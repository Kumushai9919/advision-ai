from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Date, Index
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
from ..database.core import Base 

class Detection(Base):
    """Store INDIVIDUAL detection events - this is your raw data"""
    __tablename__ = "detections"
    
    id = Column(Integer, primary_key=True, index=True)
    face_id = Column(UUID(as_uuid=True), ForeignKey("faces.id"), index=True)
    billboard_id = Column(Integer, ForeignKey("billboards.id"), index=True)
    
    # STORE THESE STATICALLY
    detected_at = Column(DateTime, default=datetime.utcnow, index=True)
    view_duration = Column(Float)  # seconds - IMPORTANT: store this!
    confidence_score = Column(Float)  # face matching confidence
    
    # Relationships
    face = relationship("Face", back_populates="detections")
    billboard = relationship("Billboard", back_populates="detections")
    
    # Indexes for fast queries
    __table_args__ = (
        Index('idx_billboard_date', 'billboard_id', 'detected_at'),
        Index('idx_face_billboard', 'face_id', 'billboard_id'),
    )
