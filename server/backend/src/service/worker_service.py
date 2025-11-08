from sqlalchemy.orm import Session
from sqlalchemy import select, distinct
from typing import Dict, List
from collections import defaultdict
from sqlalchemy.orm import joinedload
from src.core.logger import logger
from src.model.user import User
from src.model.face import Face
from src.api.v1.worker.schema import FaceData, ExportData, UserFaceData

class WorkerService:
    def __init__(self, db: Session):
        self.db = db
        
    def init_worker(self) -> ExportData:
        """
        Export all face recognition data in the specified format
        
        Returns:
            ExportData with companies, users, faces, and embeddings
        """
        try:
            # Get all unique companies
            companies = self.db.query(distinct(User.org_id)).all()
            company_list = {org_id[0]: {} for org_id in companies}
            
            # Build users, faces, and embeddings structures
            users_dict = defaultdict(dict)
            faces_dict = defaultdict(list)
            embeddings_dict = {}
            
            # Get all users with their faces
            users = self.db.query(User).all()
            
            for user in users:
                # Get faces for this user
                faces = self.db.query(Face).filter(Face.user_id == user.id).all()
                
                if faces:  # Only include users with faces
                    face_ids = []
                    
                    for face in faces:
                        face_id = str(face.id)
                        face_ids.append(face_id)
                        
                        # Add to faces dict (organized by company)
                        faces_dict[user.org_id].append(FaceData(
                            face_id=face_id,
                            user_id=str(user.id)  # ✅ Convert to string
                        ))
                        
                        # Add embedding to embeddings dict
                        embeddings_dict[face_id] = face.embedding
                    
                    # Add user to users dict
                    users_dict[user.org_id][str(user.id)] = UserFaceData(  # ✅ Convert dict key to string
                        user_id=str(user.id),  # ✅ Convert to string
                        faces=face_ids
                    )
            
            logger.info(f"Exported {len(company_list)} companies, "
                    f"{sum(len(users) for users in users_dict.values())} users, "
                    f"{sum(len(faces) for faces in faces_dict.values())} faces, "
                    f"{len(embeddings_dict)} embeddings")
            
            return ExportData(
                companies=company_list,
                users=dict(users_dict),
                faces=dict(faces_dict),
                embeddings=embeddings_dict
            )
            
        except Exception as e:
            logger.error(f"Error exporting data: {e}", exc_info=True)
            raise
        