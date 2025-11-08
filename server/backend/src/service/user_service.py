from sqlalchemy.orm import Session
from sqlalchemy import select, func, distinct
from typing import List, Optional, Tuple
from src.core.timezone import now_kst
from uuid import UUID
from src.core.logger import logger
from src.core.pagination import PaginationHelper, PaginationMeta
from src.model.user import User
from src.model.face import Face
from src.service.minio_service import MinIoService
from datetime import datetime
from src.message.message_producer_singleton import message_producer_singleton
from src.api.v1.user.schema import UserBase, UserCreateSchema, UserUpdateSchema, UserDeleteData, UserUpdateData
from src.api.v1.org.schema import OrgResponse
from src.core.exception import (
    UserRelatedWithAnotherOrgError,
    UserNotFoundError,
    InternalError
) 

class UserService:
    """Service for user CRUD operations"""
    
    def __init__(self, db: Session):
        self.db = db
        self.message_producer = message_producer_singleton.get_producer()
        self.minio_service = MinIoService()
    
    def create(self, user_data: UserCreateSchema) -> User:
        """Create a new user"""
        try:
            existing = self.get_by_user_id(user_data.user_id)
            if existing:
                logger.info(f"User {user_data.user_id} already exists")
                return existing
            
            new_user = User(
                user_id=user_data.user_id,
                org_id=user_data.org_id,
                is_active=user_data.is_active
            )
            
            self.db.add(new_user)
            self.db.commit()
            self.db.refresh(new_user)
            
            logger.info(f"Created user: {new_user.user_id}")
            return new_user
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error creating user: {e}")
            raise
    
    def get_or_create(self, user_id: str, org_id: str) -> Tuple[User, bool]:
        """Get existing user or create new one. Returns (user, is_new)"""
        user = self.get_by_user_id(user_id, org_id)
        if user:
            return user, False
        
        new_user = User(
            user_id=user_id,
            org_id=org_id,
            is_active=True
        )
        self.db.add(new_user)
        self.db.commit()
        self.db.refresh(new_user)
        
        logger.info(f"Created new user: {new_user.user_id}")
        return new_user, True

    def get_by_id(self, id: str) -> Optional[User]:
        """Get user by primary key (UUID)"""
        try:
            return self.db.get(User, id)
        except Exception as e:
            logger.error(f"Error fetching user by ID {id}: {e}")
            return None

    def get_by_user_id(self, user_id: str, org_id: Optional[str] = None) -> Optional[User]:
        """Get user by their external user_id. If exists on another org, log error."""
        try:
            query = select(User).where(User.user_id == user_id)
            user = self.db.execute(query).scalar_one_or_none()
            if user:
                if org_id is not None and user.org_id != org_id:
                    logger.error(f"User {user_id} exists on another org: {user.org_id}")
                    raise UserRelatedWithAnotherOrgError(f"User {user_id} exists on another org: {user.org_id}")
                return user
            return None
        except Exception as e:
            logger.error(f"Error fetching user {user_id}: {e}")
            raise
    
    def get_by_pk(self, pk: UUID) -> Optional[User]:
        """Get user by primary key (UUID)"""
        try:
            return self.db.get(User, pk)
        except Exception as e:
            logger.error(f"Error fetching user by PK {pk}: {e}")
            return None
    
    def get_by_user_id_and_org(self, user_id: str, org_id: str) -> Optional[User]:
        """Get user by user_id and org_id"""
        try:
            return self.db.execute(
                select(User).where(
                    User.user_id == user_id,
                    User.org_id == org_id
                )
            ).scalar_one_or_none()
        except Exception as e:
            logger.error(f"Error fetching user {user_id} for org {org_id}: {e}")
            return None
    
    def get_all_paginated(
        self,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[UserBase], PaginationMeta]:
        """Get paginated list of all users"""
        try:
            query = (
                self.db.query(
                    User,
                    func.count(Face.id).label('face_count')
                )
                .outerjoin(Face, User.id == Face.user_id)
                .group_by(User.id)
            )
            
            results, pagination = PaginationHelper.paginate_query(
                query, page=page, limit=limit
            )
            
            users = [
                UserBase.from_db_model(user, face_count=face_count)
                for user, face_count in results
            ]
            
            logger.info(f"Retrieved {len(users)} users, page {page}")
            return users, pagination
            
        except Exception as e:
            logger.error(f"Error getting all users: {e}")
            raise
    
    def get_all_organizations_paginated(
        self,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[OrgResponse], PaginationMeta]:
        """
        Get paginated organizations with user and face counts
        
        Args:
            page: Page number (starting from 1)
            limit: Number of items per page
            
        Returns:
            Tuple of (list of OrgResponse objects, PaginationMeta)
        """
        try:
            # Build query for organization statistics
            query = self.db.query(
                User.org_id,
                func.count(distinct(User.id)).label('user_count'),
                func.count(Face.id).label('face_count')
            ).outerjoin(
                Face, User.id == Face.user_id
            ).group_by(
                User.org_id
            )
            
            # Apply pagination
            results, pagination = PaginationHelper.paginate_query(
                query, page=page, limit=limit
            )
            
            # Convert to OrgResponse objects
            orgs_data = [
                OrgResponse(
                    org_id=org_id,
                    user_count=user_count,
                    face_count=face_count or 0
                )
                for org_id, user_count, face_count in results
            ]
            
            logger.info(f"Retrieved {len(orgs_data)} organizations (page {page}/{pagination.total_pages})")
            return orgs_data, pagination
            
        except Exception as e:
            logger.error(f"Error getting paginated organizations: {e}", exc_info=True)
            raise

    def get_by_org_paginated(
        self,
        org_id: str,
        page: int = 1,
        limit: int = 20
    ) -> Tuple[List[UserBase], PaginationMeta]:
        """Get paginated users for an organization"""
        try:
            query = (
                self.db.query(
                    User,
                    func.count(Face.id).label('face_count')
                )
                .outerjoin(Face, User.id == Face.user_id)
                .filter(User.org_id == org_id)
                .group_by(User.id)
            )
            
            results, pagination = PaginationHelper.paginate_query(
                query, page=page, limit=limit
            )
            
            users = [
                UserBase.from_db_model(user, face_count=face_count)
                for user, face_count in results
            ]
            
            return users, pagination
            
        except Exception as e:
            logger.error(f"Error getting users for org {org_id}: {e}")
            raise
    
    def get_by_org(self, org_id: str, skip: int = 0, limit: int = 100) -> List[User]:
        """Get users for an organization (simple list)"""
        try:
            return self.db.execute(
                select(User)
                .where(User.org_id == org_id)
                .offset(skip)
                .limit(limit)
            ).scalars().all()
        except Exception as e:
            logger.error(f"Error fetching users for org {org_id}: {e}")
            return []
    
    def update(self, user_id: str, user_data: UserUpdateSchema) -> UserUpdateData:
        """Update user information"""
        try:
            user = self.get_by_user_id(user_id)
            if not user:
                raise UserNotFoundError(f"사용자 {user_id}를 찾을 수 없습니다.")
            
            update_data = user_data.model_dump(exclude_unset=True)
            
            if not update_data:
                raise ValueError("업데이트할 필드를 제공해주세요.")
            
            for field, value in update_data.items():
                setattr(user, field, value)
            
            self.db.commit()
            self.db.refresh(user)
            
            logger.info(f"Updated user {user_id}: {update_data}")
            
            return UserUpdateData(
                user_id=user.user_id,
                org_id=user.org_id,
                is_active=user.is_active,
                message="사용자 정보가 성공적으로 업데이트되었습니다.",
                updated_at=now_kst()
            )
            
        except (UserNotFoundError, ValueError):
            self.db.rollback()
            raise
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error updating user {user_id}: {e}", exc_info=True)
            raise InternalError("사용자 정보 업데이트 중 오류가 발생했습니다.")
    
    def delete(self, user_id: str) -> UserDeleteData:
        """Delete user and all associated faces"""
        try:
            user = self.get_by_user_id(user_id)
            if not user:
                raise UserNotFoundError(f"사용자 {user_id}를 찾을 수 없습니다.")
            
            # Count faces before deletion
            face_count = self.db.query(Face).filter(Face.user_id == user.id).count()
            print(f"User {user_id} has {face_count} faces to delete")
            try:
                self.message_producer.delete_user(
                    company_id=user.org_id,
                    user_id=str(user.id)
                )
            except Exception as e:
                logger.warning(f"Failed to notify workers about user deletion: {e}")
            
            
            user_data = UserDeleteData(
                user_id=user.user_id,
                face_count=face_count,
                deleted_at=now_kst(),
                message=f"사용자가 성공적으로 삭제되었습니다."
            )
            
            self.db.query(Face).filter(Face.user_id == user.id).delete(synchronize_session=False)
            self.db.delete(user)
            self.db.commit()

            self.minio_service.delete_user_images(org_id=user.org_id, user_id=str(user.id))
            
            logger.info(f"Deleted user {user_id} and {face_count} faces via CASCADE")
            
            return user_data
            
        except (UserNotFoundError, InternalError):
            self.db.rollback()
            raise
        
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting user {user_id}: {e}", exc_info=True)
            raise InternalError("사용자 삭제 중 오류가 발생했습니다.")

    def delete_org(self, org_id: str) -> int:
        """Delete all users for a specific organization"""
        try:
            users_to_delete = self.db.query(User).filter(User.org_id == org_id).all()
            deleted_count = len(users_to_delete)
            
            if deleted_count == 0:
                logger.info(f"No users found for org {org_id}")
                return 0
            
            logger.info(f"Deleting {deleted_count} users for org {org_id}")
            
            try:
                self.message_producer.delete_company(company_id=org_id)
                logger.info(f"Notified workers about company {org_id} deletion")
            except Exception as e:
                logger.warning(f"Failed to notify workers about company deletion: {e}")
            
            self.db.query(Face).filter(
                Face.user_id.in_([user.id for user in users_to_delete])
            ).delete(synchronize_session=False)
            
            self.db.query(User).filter(User.org_id == org_id).delete(synchronize_session=False)
            
            self.db.commit()
            logger.info(f"Deleted {deleted_count} users and their faces from database for org {org_id}")
            
            self.minio_service.delete_org_images(org_id=org_id)
            
            return deleted_count
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error deleting users for org {org_id}: {e}", exc_info=True)
            raise InternalError("조직 사용자 삭제 중 오류가 발생했습니다.")
        