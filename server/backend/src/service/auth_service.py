from sqlalchemy.orm import Session
from uuid import uuid4
from datetime import datetime
from src.core.timezone import now_kst
import base64

from src.core.logger import logger
from src.service.user_service import UserService
from src.service.face_service import FaceService
from src.service.minio_service import MinIoService
from src.message.message_producer_singleton import message_producer_singleton
from src.api.v1.auth.schema import (
    FaceRegisterResponse,
    FaceRegisterData,
    FaceDetectResponse,
    FaceDetectData
)
from src.core.exception import (
    FaceNotDetectedError,
    UserNotFoundError,
    InternalError,
    UserRelatedWithAnotherOrgError
)

class AuthService:
    """Service for authentication operations (register and detect)"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        self.face_service = FaceService(db)
        self.message_producer = message_producer_singleton.get_producer()
        self.minio_service = MinIoService()
    
    def register(
        self,
        image_content: bytes,
        ext: str,
        user_id: str,
        org_id: str,
        start_time: str,
        end_time: str,
        duration: int
    ) -> FaceRegisterResponse:
        """
        Register a face for a user
        
        Steps:
        1. Ensure organization exists in workers
        2. Get or create user
        3. Process face and get embedding from workers
        4. Upload image to MinIO
        5. Create face record in database
        """
        try:
            self._ensure_org_exists(org_id)
            user, is_new_user = self.user_service.get_or_create(user_id, org_id)
            
            face_id = str(uuid4())
            image_base64 = base64.b64encode(image_content).decode("utf-8")
            print("starting to create or add face")
            if is_new_user:
                print("creating new user in workers")
                embedding = self.message_producer.create_user(
                    company_id=org_id,
                    user_id=str(user.id),
                    face_id=face_id,
                    image_base64=image_base64
                )
            else:
                print("adding face to existing user in workers")
                embedding = self.message_producer.add_face(
                    company_id=org_id,
                    user_id=str(user.id),
                    face_id=face_id,
                    image_base64=image_base64
                )
            
            print("received embedding from workers")
            image_url = self.minio_service.upload_face_image(
                image_content, ext, org_id, str(user.id),
                content_type=f"image/{ext}"
            )
            
            if not image_url:
                raise InternalError("Failed to upload image to storage")
            
            self.face_service.create(
                face_id=face_id,
                user_id=user.id,
                image_url=image_url,
                embedding=embedding
            )
            
            logger.info(f"Successfully registered face for user {user_id}")
            
            return FaceRegisterResponse(
                success=True,
                data=FaceRegisterData(
                    face_id=face_id,
                    user_id=user_id,
                    org_id=org_id,
                    message="사용자 얼굴이 성공적으로 등록되었습니다.",
                    registered_at=now_kst()
                )
            )
            
        except (FaceNotDetectedError, UserNotFoundError, InternalError, UserRelatedWithAnotherOrgError):
            self.db.rollback()
            raise

        except Exception as e:
            self.db.rollback()
            logger.error(f"Error registering face for user {user_id}: {e}")
            raise InternalError("Failed to register face")

    def detect(self, image_content: bytes, org_id: str) -> FaceDetectResponse:
        """Detect and recognize a face in an image"""
        try:
            self._ensure_org_exists(org_id, create_if_missing=False)

            image_base64 = base64.b64encode(image_content).decode("utf-8")
            user_id, confidence, bbox = self.message_producer.recognize_face(
                company_id=org_id,
                image_base64=image_base64
            )
            
            if not user_id:
                raise FaceNotDetectedError("이미지에서 얼굴을 인식할 수 없습니다.")
            
            user = self.user_service.get_by_id(id=user_id)
            
            if not user:
                raise UserNotFoundError()
            
            return FaceDetectResponse(
                success=True,
                data=FaceDetectData(
                    user_id=user.user_id,
                    org_id=org_id,
                    confidence=confidence,
                    message="얼굴이 성공적으로 인식되었습니다.",
                    detected_at=now_kst()
                )
            )
            
        except (FaceNotDetectedError, UserNotFoundError, InternalError):
            self.db.rollback()
            raise
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error detecting face for org {org_id}: {e}", exc_info=True)
            raise InternalError("얼굴 인식 중 오류가 발생했습니다.")
    
    def _ensure_org_exists(self, org_id: str, create_if_missing: bool = True):
        """Ensure organization exists in workers"""
        try:
            users = self.user_service.get_by_org(org_id, limit=1)
            
            if not users and create_if_missing:
                print("creating new company in workers")
                self.message_producer.create_company(org_id)
            elif not users and not create_if_missing:
                raise InternalError(f"조직 {org_id}가 존재하지 않습니다.")
                
        except Exception as e:
            logger.error(f"Error ensuring org {org_id} exists: {e}")
            raise
