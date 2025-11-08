from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Float
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime, timezone
from ..database.core import Base 


class Face(Base):
    __tablename__ = "faces"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    image_url = Column(String, nullable=False)
    registered_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc))
    embedding = Column(ARRAY(Float), nullable=False)
    
    # Relationships
    detections = relationship("Detection", back_populates="face", cascade="all, delete-orphan")
    viewing_sessions = relationship("ViewingSession", back_populates="face", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Face(id={self.id}, user_id={self.user_id}, image_url={self.image_url})>"