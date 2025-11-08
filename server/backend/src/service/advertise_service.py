from sqlalchemy.orm import Session
from sqlalchemy import func, and_, distinct, case
from sqlalchemy import select
from uuid import uuid4
from datetime import datetime, timedelta, date
from typing import Optional, Tuple, Dict, List
import base64

from src.core.logger import logger
from src.core.timezone import now_kst
from src.service.user_service import UserService
from src.service.face_service import FaceService
from src.service.minio_service import MinIoService
from src.message.message_producer_singleton import message_producer_singleton
from src.model.detection import Detection
from src.model.billboard import Billboard
from src.model.face import Face
from src.model.viewing_session import ViewingSession
from src.model.analytics import Analytics
from src.model.user import User
from src.core.exception import (
    FaceNotDetectedError,
    UserNotFoundError,
    InternalError
)


class AdvertiseService:
    """Service for handling advertise-related operations (viewer registration and facility detection)"""
    
    def __init__(self, db: Session):
        self.db = db
        self.user_service = UserService(db)
        self.face_service = FaceService(db)
        self.message_producer = message_producer_singleton.get_producer()
        self.minio_service = MinIoService()
    
    def register_viewer(
        self,
        image_base64: str,
        start_time: str,
        end_time: str,
        duration: int,
        org_id: str = "default_org"
    ) -> dict:
        """
        Register a viewer and create a viewing session
        
        IMPORTANT: This function uses a recognize-first approach:
        1. First attempts to recognize the face in the image
        2. If recognized, reuses the existing user and creates a new session
        3. If not recognized, creates a new user, face, and session
        """
        try:
            # Ensure organization exists
            self._ensure_org_exists(org_id)
            
            logger.info(f"Attempting to register viewer for org: {org_id}")
            
            # Step 1: Try to recognize face first
            logger.info("Calling recognize_face to check if face already exists...")
            user_id, confidence, bbox = self.message_producer.recognize_face(
                company_id=org_id,
                image_base64=image_base64
            )
            
            logger.info(f"[RECOGNIZE RESULT] user_id: {user_id}, confidence: {confidence}, bbox: {bbox}")
            
            # Store face_id for later use
            face_id = None
            
            # Step 2: Handle recognized face
            if user_id:
                logger.info(f"✅ Face recognized with confidence {confidence}! Using existing user: {user_id}")
                
                # Get user by user_id (string like "viewer_xxx"), not by UUID
                user = self.user_service.get_by_user_id(user_id=user_id, org_id=org_id)
                
                if not user:
                    logger.error(f"⚠️ CRITICAL: User {user_id} recognized by worker but not found in database!")
                    raise InternalError(f"Data inconsistency: User {user_id} exists in worker but not in database")
                
                # Get existing face
                face = self.db.query(Face).filter(Face.user_id == user.id).first()
                
                if not face:
                    logger.error(f"⚠️ CRITICAL: User {user_id} exists but has no face record!")
                    raise InternalError(f"Data inconsistency: User {user_id} has no face record")
                
                # Get the face_id from the face record (use whatever field name your model has)
                face_id = str(face.id)  # or face.face_id if that field exists
                
                logger.info(f"✅ Using existing user {user.user_id} (UUID: {user.id}) with face_id {face_id}")
            
            else:
                # Step 3: No face recognized - create new user and face
                logger.info("❌ No existing face recognized, creating new viewer")
                
                user_id_str = f"viewer_{uuid4()}"
                face_id = str(uuid4())
                
                logger.info(f"Creating new viewer with user_id: {user_id_str}, face_id: {face_id}")
                
                # Create user in database first
                user, is_new_user = self.user_service.get_or_create(user_id_str, org_id)
                logger.info(f"User created in DB: user_id={user.user_id}, UUID={user.id}, is_new={is_new_user}")
                
                # Register user with worker (create_user adds the face)
                logger.info(f"Registering user in worker: company_id={org_id}, user_id={user.user_id}, face_id={face_id}")
                embedding = self.message_producer.create_user(
                    company_id=org_id,
                    user_id=user.user_id,  # Use external user_id, not internal UUID
                    face_id=face_id,
                    image_base64=image_base64
                )
                
                if not embedding:
                    logger.error("⚠️ Worker returned empty embedding!")
                    raise InternalError("Failed to create face embedding")
                
                logger.info(f"✅ Worker returned embedding of length: {len(embedding)}")
                
                # Create face record in database
                face = self.face_service.create(
                    face_id=face_id,
                    user_id=user.id,
                    image_url="image_url",
                    embedding=embedding
                )
                
                logger.info(f"✅ Face record created in DB: face_id={face_id}, db_id={face.id}")
            
            # Step 4: Create viewing session record
            viewing_session = ViewingSession(
                user_id=user.id,
                face_id=face.id,  # Use face.id (the database ID)
                start_time=datetime.fromisoformat(start_time) if start_time else now_kst(),
                end_time=datetime.fromisoformat(end_time) if end_time else now_kst(),
                duration=float(duration)
            )
            
            self.db.add(viewing_session)
            self.db.commit()
            self.db.refresh(viewing_session)
            
            logger.info(f"✅ Successfully created viewing session {viewing_session.id} for user {user.user_id}")
            
            return {
                "success": True,
                "face_id": str(face.id),  # Use face.id instead of face.face_id
                "user_id": user.user_id,
                "org_id": org_id,
                "start_time": start_time,
                "end_time": end_time,
                "duration": duration,
                "image_url": "",
                "session_id": viewing_session.id,
                "registered_at": now_kst().isoformat(),
                "is_new_user": user_id is None,  # Indicate if this was a new registration
                "confidence": confidence if confidence else 0.0,  # Include confidence for debugging
                "message": f"{'New viewer registered' if user_id is None else 'Existing viewer session created'}"
            }
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"❌ Error registering viewer: {e}", exc_info=True)
            raise InternalError(f"Failed to register viewer: {str(e)}")
    
    def track_viewer(
        self,
        image_base64: str,
        org_id: str
    ) -> dict:
        """
        Detect a face at a facility and log the detection
        
        Steps:
        1. Recognize face using workers
        2. Match detected face against existing embeddings
        3. Return detection details
        
        Args:
            image_base64: Base64 encoded image
            org_id: Organization ID (default: "default_org")
        
        Returns:
            dict with detection details or failure message
        """
        try:
            logger.info(f"Detecting face for org: {org_id}")
            
            # Ensure organization exists
            self._ensure_org_exists(org_id, create_if_missing=False)
            
            # Recognize face using worker
            user_id, confidence, bbox = self.message_producer.recognize_face(
                company_id=org_id,
                image_base64=image_base64
            )
            
            logger.info(f"[TRACK] Recognize result: user_id={user_id}, confidence={confidence}")
            
            if not user_id:
                logger.warning("No face detected in the image")
                return {
                    "success": False,
                    "org_id": org_id,
                    "facility_id": "unknown",
                    "start_time": now_kst().isoformat(),
                    "end_time": now_kst().isoformat(),
                    "duration": 0.0,
                    "message": "No face detected in the image",
                }
            
            # Get user from database by user_id (string), not UUID
            user = self.user_service.get_by_user_id(user_id=user_id, org_id=org_id)
            
            if not user:
                logger.warning(f"User {user_id} not found in database")
                raise UserNotFoundError(f"User {user_id} not found")
            
            # Get the user's face
            face = self.db.query(Face).filter(Face.user_id == user.id).first()
            face_id_value = None
            if face:
                face_id_value = str(face.id) if hasattr(face.id, '__str__') else face.id
            
            # Create or update analytics record
            analytics = self.db.query(Analytics).filter(
                Analytics.user_id == user.id,
                Analytics.org_id == org_id
            ).first()
            
            if analytics:
                # Update existing analytics - increment visit count
                analytics.visit_count += 1
                analytics.last_seen = now_kst()
                analytics.updated_at = now_kst()
                logger.info(f"Updated analytics for user {user.user_id}: visit_count={analytics.visit_count}")
            else:
                # Create new analytics record
                analytics = Analytics(
                    user_id=user.id,
                    org_id=org_id,
                    visit_count=1,  # First visit
                    first_seen=now_kst(),
                    last_seen=now_kst()
                )
                self.db.add(analytics)
                logger.info(f"Created new analytics for user {user.user_id}: visit_count=1")
            
            self.db.commit()
            self.db.refresh(analytics)
            
            logger.info(f"Successfully detected user {user.user_id} with {analytics.visit_count} total visits")
            
            return {
                "success": True,
                "user_id": user.user_id,
                "org_id": org_id,
                "facility_id": "default_facility",  # Can be made dynamic if needed
                "confidence": confidence,
                "bbox": bbox,
                "visit_count": analytics.visit_count,
                "start_time": now_kst().isoformat(),
                "end_time": now_kst().isoformat(),
                "duration": 0.0,  # Can be calculated if needed
                "detected_at": now_kst().isoformat(),
                "message": f"Face detected successfully - Visit #{analytics.visit_count}"
            }
            
        except (UserNotFoundError, InternalError):
            self.db.rollback()
            raise
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error detecting facility visitor: {e}", exc_info=True)
            raise InternalError(f"Failed to detect facility visitor: {str(e)}")

    
    def _ensure_org_exists(self, org_id: str, create_if_missing: bool = True) -> None:
        """Ensure organization exists in workers"""
        try:
            if create_if_missing:
                self.message_producer.create_company(org_id)
            logger.info(f"Organization {org_id} verified/created")
        except Exception as e:
            logger.error(f"Error ensuring org exists: {e}")
            if not create_if_missing:
                raise InternalError(f"Organization {org_id} not found")
    
    def _get_or_create_billboard(self, billboard_id: str) -> Billboard:
        """Get or create a billboard record"""
        try:
            # Try to get existing billboard
            billboard = self.db.query(Billboard).filter(
                Billboard.billboard_id == billboard_id
            ).first()
            
            if billboard:
                logger.info(f"Found existing billboard: {billboard_id}")
                return billboard
            
            # Create new billboard
            new_billboard = Billboard(
                billboard_id=billboard_id,
                name=f"Billboard {billboard_id}",
                location=f"Facility {billboard_id}",
                created_at=now_kst()
            )
            
            self.db.add(new_billboard)
            self.db.commit()
            self.db.refresh(new_billboard)
            
            logger.info(f"Created new billboard: {billboard_id}")
            return new_billboard
            
        except Exception as e:
            self.db.rollback()
            logger.error(f"Error getting/creating billboard: {e}")
            raise InternalError("Failed to get/create billboard")
    
    def get_analytics(
        self,
        org_id: str,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> dict:
        """
        Get analytics data for an organization
        
        Args:
            org_id: Organization ID
            start_date: Start date for the period (defaults to 7 days ago)
            end_date: End date for the period (defaults to now)
        
        Returns:
            dict with analytics data including summary and daily history
        """
        try:
            # Default to last 7 days if not provided
            if end_date is None:
                end_date = now_kst()
            if start_date is None:
                start_date = end_date - timedelta(days=7)
            
            # Ensure dates are at start/end of day
            start_date = start_date.replace(hour=0, minute=0, second=0, microsecond=0)
            end_date = end_date.replace(hour=23, minute=59, second=59, microsecond=999999)
            
            days = (end_date.date() - start_date.date()).days + 1
            
            logger.info(f"Getting analytics for org {org_id} from {start_date} to {end_date} ({days} days)")
            
            # 1. Total viewers (all time) - unique users for this org
            total_viewers = self.db.query(func.count(distinct(User.id))).filter(
                User.org_id == org_id
            ).scalar() or 0
            
            # 2. Total viewers in current period (for comparison with previous period)
            prev_start = start_date - timedelta(days=days)
            prev_end = start_date - timedelta(seconds=1)
            
            # Count unique viewers in current period
            current_period_viewers = self.db.query(func.count(distinct(ViewingSession.user_id))).join(
                User, ViewingSession.user_id == User.id
            ).filter(
                and_(
                    User.org_id == org_id,
                    ViewingSession.start_time >= start_date,
                    ViewingSession.start_time <= end_date
                )
            ).scalar() or 0
            
            # Count unique viewers in previous period
            prev_total_viewers = self.db.query(func.count(distinct(ViewingSession.user_id))).join(
                User, ViewingSession.user_id == User.id
            ).filter(
                and_(
                    User.org_id == org_id,
                    ViewingSession.start_time >= prev_start,
                    ViewingSession.start_time <= prev_end
                )
            ).scalar() or 0
            
            # Calculate percentage difference for total viewers (current period vs previous period)
            if prev_total_viewers > 0:
                difference_total_viewers_percentage = int(
                    ((current_period_viewers - prev_total_viewers) / prev_total_viewers) * 100
                )
            else:
                difference_total_viewers_percentage = 0 if current_period_viewers == 0 else 100
            
            # 3. New viewers in the period (users with first viewing session in period)
            # Get users who had their first session in this period
            first_sessions = self.db.query(
                ViewingSession.user_id,
                func.min(ViewingSession.start_time).label('first_session')
            ).join(
                User, ViewingSession.user_id == User.id
            ).filter(
                User.org_id == org_id
            ).group_by(ViewingSession.user_id).subquery()
            
            new_viewers = self.db.query(func.count(distinct(first_sessions.c.user_id))).filter(
                and_(
                    first_sessions.c.first_session >= start_date,
                    first_sessions.c.first_session <= end_date
                )
            ).scalar() or 0
            
            # 4. Total customers (users with visit_count > 1 in Analytics)
            total_customers = self.db.query(func.count(distinct(Analytics.user_id))).filter(
                and_(
                    Analytics.org_id == org_id,
                    Analytics.visit_count > 1
                )
            ).scalar() or 0
            
            # Previous period customers
            prev_customers = self.db.query(func.count(distinct(Analytics.user_id))).filter(
                and_(
                    Analytics.org_id == org_id,
                    Analytics.visit_count > 1,
                    Analytics.last_seen <= prev_end
                )
            ).scalar() or 0
            
            # Calculate percentage difference for customers
            if prev_customers > 0:
                difference_total_customers_percentage = int(
                    ((total_customers - prev_customers) / prev_customers) * 100
                )
            else:
                difference_total_customers_percentage = 0 if total_customers == 0 else 100
            
            # 5. Average view time (in minutes) for the period
            avg_duration_result = self.db.query(
                func.avg(ViewingSession.duration)
            ).join(
                User, ViewingSession.user_id == User.id
            ).filter(
                and_(
                    User.org_id == org_id,
                    ViewingSession.start_time >= start_date,
                    ViewingSession.start_time <= end_date
                )
            ).scalar()
            
            average_view_time = int((avg_duration_result or 0) / 60)  # Convert seconds to minutes
            
            # Previous period average view time
            prev_avg_duration = self.db.query(
                func.avg(ViewingSession.duration)
            ).join(
                User, ViewingSession.user_id == User.id
            ).filter(
                and_(
                    User.org_id == org_id,
                    ViewingSession.start_time >= prev_start,
                    ViewingSession.start_time <= prev_end
                )
            ).scalar() or 0
            
            prev_avg_view_time = int(prev_avg_duration / 60) if prev_avg_duration else 0
            
            # Calculate percentage difference for average view time
            if prev_avg_view_time > 0:
                difference_average_view_time = int(
                    ((average_view_time - prev_avg_view_time) / prev_avg_view_time) * 100
                )
            else:
                difference_average_view_time = 0 if average_view_time == 0 else 100
            
            # 6. Daily history
            daily_history = []
            current_date = start_date.date()
            end_date_only = end_date.date()
            
            # Get daily aggregates
            daily_stats = self.db.query(
                func.date(ViewingSession.start_time).label('date'),
                func.count(distinct(ViewingSession.user_id)).label('viewers'),
                func.avg(ViewingSession.duration).label('avg_duration')
            ).join(
                User, ViewingSession.user_id == User.id
            ).filter(
                and_(
                    User.org_id == org_id,
                    ViewingSession.start_time >= start_date,
                    ViewingSession.start_time <= end_date
                )
            ).group_by(
                func.date(ViewingSession.start_time)
            ).all()
            
            # Create a dict for quick lookup
            daily_stats_dict = {
                stat.date: {
                    'viewers': stat.viewers,
                    'avg_duration': stat.avg_duration
                }
                for stat in daily_stats
            }
            
            # Get daily customers (users with visit_count > 1 who visited that day)
            daily_customers_query = self.db.query(
                func.date(ViewingSession.start_time).label('date'),
                func.count(distinct(ViewingSession.user_id)).label('customers')
            ).join(
                User, ViewingSession.user_id == User.id
            ).join(
                Analytics, and_(
                    Analytics.user_id == User.id,
                    Analytics.org_id == org_id,
                    Analytics.visit_count > 1
                )
            ).filter(
                and_(
                    User.org_id == org_id,
                    ViewingSession.start_time >= start_date,
                    ViewingSession.start_time <= end_date
                )
            ).group_by(
                func.date(ViewingSession.start_time)
            ).all()
            
            daily_customers_dict = {
                stat.date: stat.customers
                for stat in daily_customers_query
            }
            
            # Generate daily history for all days in period
            day_names = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
            
            while current_date <= end_date_only:
                day_stats = daily_stats_dict.get(current_date, {'viewers': 0, 'avg_duration': 0})
                customers = daily_customers_dict.get(current_date, 0)
                avg_view_time = int((day_stats['avg_duration'] or 0) / 60)  # Convert to minutes
                
                day_of_week = day_names[current_date.weekday()]
                
                daily_history.append({
                    'date': current_date.strftime('%Y-%m-%d'),
                    'day_of_week': day_of_week,
                    'viewers': day_stats['viewers'],
                    'customers': customers,
                    'average_view_time': avg_view_time
                })
                
                current_date += timedelta(days=1)
            
            return {
                'success': True,
                'org_id': org_id,
                'period': {
                    'start': start_date.isoformat() + 'Z',
                    'end': end_date.isoformat() + 'Z',
                    'days': days
                },
                'data': {
                    'summary': {
                        'total_viewers': total_viewers,
                        'difference_total_viewers_percentage': difference_total_viewers_percentage,
                        'total_new_viewers': new_viewers,
                        'total_customers': total_customers,
                        'difference_total_customers_percentage': difference_total_customers_percentage,
                        'average_view_time': average_view_time,
                        'difference_average_view_time': difference_average_view_time
                    },
                    'daily_history': daily_history
                }
            }
            
        except Exception as e:
            logger.error(f"Error getting analytics: {e}", exc_info=True)
            raise InternalError(f"Failed to get analytics: {str(e)}")
