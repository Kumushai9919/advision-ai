from sqlalchemy.orm import Session
from sqlalchemy import and_
from typing import List, Optional, Tuple
from uuid import UUID
from src.core.logger import logger
from src.core.pagination import PaginationHelper, PaginationMeta
from src.model.face import Face
from src.model.user import User
from src.api.v1.user.schema import FaceBase, FaceCreateSchema, FaceDeleteData
from src.service.minio_service import MinIoService
from src.message.message_producer_singleton import message_producer_singleton
from src.core.exception import (
    FaceNotFoundError,
    InternalError,
    UserNotFoundError,
    WorkerError
)

class FaceService:
    """Service for face CRUD operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.message_producer = message_producer_singleton.get_producer()
        self.minio_service = MinIoService()
    
    def create(
        self,
        face_id: str,
        user_id: UUID,
        image_url: str,
        embedding: List[float]
    ) -> Face:
        """Create a new face record"""
        try:
            new_face = Face(
                id=face_id,
                user_id=user_id,
                image_url=image_url,
                embedding=embedding
            )
            
            self.db.add(new_face)
            self.db.commit()
            self.db.refresh(new_face)
            
            logger.info(f"Created face {face_id} for user {user_id}")
            return new_face
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating face: {e}")
            raise
    
    def get_by_id(self, face_id: UUID) -> Optional[Face]:
        """Get face by ID"""
        try:
            return self.db.get(Face, face_id)
        except Exception as e:
            logger.error(f"Error fetching face {face_id}: {e}")
            return None
    
    def get_by_user_paginated(
        self,
        user_id: UUID,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[FaceBase], PaginationMeta]:
        """Get paginated faces for a user"""
        try:
            query = (
                self.db.query(Face)
                .filter(Face.user_id == user_id)
                .order_by(Face.registered_at.desc())
            )
            
            faces, pagination = PaginationHelper.paginate_query(
                query, page=page, limit=limit
            )
            
            face_responses = [
                FaceBase.from_db_model(face) 
                for face in faces
            ]
            
            logger.info(f"Retrieved {len(faces)} faces for user {user_id}")
            return face_responses, pagination

        except Exception as e:
            logger.error(f"Error fetching faces for user {user_id}: {e}")
            raise
    
    def delete(self, user: User, face_id: UUID) -> FaceDeleteData:
        """Delete a specific face and remove user if no faces remain"""
        try:
            # Find the face
            face = self.db.query(Face).filter(
                and_(
                    Face.id == face_id,
                    Face.user_id == user.id
                )
            ).first()
            
            if not face:
                raise FaceNotFoundError(f"Face {face_id} not found for user {user.user_id}")

            # Count remaining faces BEFORE deletion
            remaining_faces = self.db.query(Face).filter(Face.user_id == user.id).count()

            # Delete face record
            self.db.delete(face)
            
            user_deleted = False
            
            # If this was last face, delete user as well
            if remaining_faces <= 1:
                self.db.delete(user)
                user_deleted = True
                logger.info(f"Deleted user {user.user_id} as no faces remain")
            
            
            try:
                self.message_producer.delete_face(
                    company_id=user.org_id,
                    user_id=str(user.id),
                    face_id=str(face_id)
                )
                
                if user_deleted:
                    self.message_producer.delete_user(
                        company_id=user.org_id,
                        user_id=str(user.id)
                    )
            except Exception as e:
                logger.warning(f"Failed to notify workers about deletion: {e}")
                raise WorkerError()
            
            # Commit database changes first
            self.db.commit()
            
            # Delete image from MinIO (after commit)
            try:
                self.minio_service.delete_face_image(face.image_url)
            except Exception as e:
                logger.warning(f"Failed to delete image from storage: {e}")
            
            logger.info(f"Successfully deleted face {face_id}")
            
            return FaceDeleteData(
                face_id=face_id,
                user_id=user.user_id,
                message=f"얼굴 성공적으로 삭제되었습니다.{' 사용자도 삭제되었습니다.' if user_deleted else ''}"
            )
            
        except (FaceNotFoundError, UserNotFoundError):
            # Re-raise custom exceptions without wrapping
            self.db.rollback()
            raise
            
        except Exception as e:
            # Only catch truly unexpected errors
            self.db.rollback()
            logger.error(f"Unexpected error deleting face {face_id}: {e}", exc_info=True)
            raise InternalError("얼굴 인식 중 오류가 발생했습니다.")
    
    def count_by_user(self, user_id: UUID) -> int:
        """Count faces for a user"""
        try:
            return self.db.query(Face).filter(Face.user_id == user_id).count()
        except Exception as e:
            logger.error(f"Error counting faces: {e}")
            return 0
    
    def validate_embedding(self, embedding: List[float]) -> List[float]:
        """Validate and normalize embedding"""
        if not embedding:
            raise ValueError("Embedding cannot be empty")
        
        try:
            return [float(x) for x in embedding]
        except (TypeError, ValueError) as e:
            raise ValueError(f"Invalid embedding format: {e}")