from sqlalchemy import Column, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
import uuid
from ..database.core import Base

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, unique=True, nullable=False)
    user_id = Column(String, unique=True, nullable=False)
    org_id = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    faces = relationship("Face", backref="user", lazy="select")
    viewing_sessions = relationship("ViewingSession", back_populates="user", cascade="all, delete-orphan")
    analytics = relationship("Analytics", back_populates="user", cascade="all, delete-orphan", uselist=False)
    
    def __repr__(self):
        return f"<User(id={self.id}, user_id={self.user_id}, org_id={self.org_id}, is_active={self.is_active})>"