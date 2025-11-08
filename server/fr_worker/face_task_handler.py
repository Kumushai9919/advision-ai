#!/usr/bin/env python3
"""
Real Face Recognition Task Handler
Provides real implementations for all face recognition tasks
"""

import json
import hashlib
import random
import time
import logging
import base64
import cv2
import numpy as np
import insightface
import os
import requests
from PIL import Image
from typing import Dict, Any, List, Optional, Tuple
from broker import TaskHandler


class FaceTaskHandler(TaskHandler):
    """
    Real implementation of face recognition tasks
    Uses InsightFace for unified face detection and embedding generation
    """
    
    def __init__(self, worker_id: str):
        self.worker_id = worker_id
        self.logger = logging.getLogger(f'face_task_handler.{worker_id}')
        
        # In-memory storage for companies, users, and faces
        # In production, this would be a proper cache/database
        self.companies: Dict[str, Dict] = {}
        self.users: Dict[str, Dict[str, Dict]] = {}  # company_id -> user_id -> user_data
        self.faces: Dict[str, List[Dict]] = {}  # company_id -> list of face data
        
        # Real embeddings database
        self.embeddings: Dict[str, List[float]] = {}  # face_id -> embedding

        # Configuration thresholds from environment
        self.recognition_threshold = float(os.getenv('FACE_RECOGNITION_THRESHOLD', '0.7'))
        self.detection_threshold = float(os.getenv('FACE_DETECTION_THRESHOLD', '0.5'))

        self.logger.info(f"Recognition threshold: {self.recognition_threshold}")
        self.logger.info(f"Detection threshold: {self.detection_threshold}")

        # Face alignment reference points (standard 112x112 face template)
        self.reference_points = np.array([
            [38.2946, 51.6963],  # left eye
            [73.5318, 51.5014],  # right eye
            [56.0252, 71.7366],  # nose tip
            [41.5493, 92.3655],  # left mouth corner
            [70.7299, 92.2041]   # right mouth corner
        ], dtype=np.float32)

        # Initialize face processing models
        self._initialize_models()

        # Load initial data from configured source
        self._load_initial_data()

        self.logger.info(f"Face task handler initialized for worker: {worker_id}")
    
    def _initialize_models(self):
        """Initialize InsightFace model"""
        try:
            # Initialize InsightFace model (handles detection + embedding)
            self.insightface_app = insightface.app.FaceAnalysis(
                name='buffalo_sc',
                root='./models',
                providers=['CPUExecutionProvider']  # Use CPU for compatibility
            )
            self.insightface_app.prepare(ctx_id=0, det_size=(640, 640))

            self.logger.info("InsightFace model initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize InsightFace model: {e}")
            raise

    def _load_initial_data(self):
        """Load initial face recognition data from configured source"""
        data_source = os.getenv('DATA_SOURCE', 'LOCAL_FILE')

        self.logger.info(f"Loading initial data from source: {data_source}")

        try:
            if data_source == 'API':
                self._load_from_api()
            elif data_source == 'LOCAL_FILE':
                self._load_from_file()
            elif data_source == 'NONE':
                self.logger.info("DATA_SOURCE set to NONE, starting with empty cache")
            else:
                self.logger.warning(f"Unknown DATA_SOURCE: {data_source}, starting with empty cache")
        except Exception as e:
            self.logger.error(f"Failed to load initial data: {e}")
            self.logger.warning("Starting with empty cache")

    def _load_from_api(self):
        """Load initial data from backend API"""
        api_url = os.getenv('API_URL')
        api_key = os.getenv('API_KEY')
        api_timeout = int(os.getenv('API_TIMEOUT', '30'))

        if not api_url:
            self.logger.warning("API_URL not configured, skipping API data load")
            return

        self.logger.info(f"Fetching initial data from API: {api_url}")

        try:
            headers = {}
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'

            response = requests.get(api_url, headers=headers, timeout=api_timeout)
            response.raise_for_status()

            data = response.json()
            self._populate_cache(data.get('data', {}))

            self.logger.info("Successfully loaded data from API")

        except requests.Timeout:
            self.logger.error(f"API request timed out after {api_timeout} seconds")
            raise
        except requests.RequestException as e:
            self.logger.error(f"API request failed: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to process API response: {e}")
            raise

    def _load_from_file(self):
        """Load initial data from local JSON file"""
        data_file = os.getenv('DATA_FILE', 'data/initial_db.json')

        if not os.path.exists(data_file):
            self.logger.warning(f"Data file not found: {data_file}, starting with empty cache")
            return

        self.logger.info(f"Loading initial data from file: {data_file}")

        try:
            with open(data_file, 'r') as f:
                data = json.load(f)

            self._populate_cache(data.get('data', {}))

            self.logger.info(f"Successfully loaded data from file: {data_file}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in data file: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Failed to load data file: {e}")
            raise

    def _populate_cache(self, data: Dict[str, Any]):
        """Populate in-memory cache with loaded data"""
        try:
            # Load companies
            if 'companies' in data:
                self.companies = data['companies']
                self.logger.info(f"Loaded {len(self.companies)} companies")

            # Load users
            if 'users' in data:
                self.users = data['users']
                total_users = sum(len(users) for users in self.users.values())
                self.logger.info(f"Loaded {total_users} users across {len(self.users)} companies")

            # Load faces
            if 'faces' in data:
                self.faces = data['faces']
                total_faces = sum(len(faces) for faces in self.faces.values())
                self.logger.info(f"Loaded {total_faces} faces across {len(self.faces)} companies")

            # Load embeddings
            if 'embeddings' in data:
                self.embeddings = data['embeddings']
                self.logger.info(f"Loaded {len(self.embeddings)} embeddings")

            # Validate data consistency
            self._validate_data_consistency()

            # Log statistics
            self.logger.info("=" * 60)
            self.logger.info("Initial Data Statistics:")
            self.logger.info(f"  Companies: {len(self.companies)}")
            self.logger.info(f"  Total Users: {sum(len(users) for users in self.users.values())}")
            self.logger.info(f"  Total Faces: {sum(len(faces) for faces in self.faces.values())}")
            self.logger.info(f"  Total Embeddings: {len(self.embeddings)}")
            self.logger.info("=" * 60)

        except Exception as e:
            self.logger.error(f"Failed to populate cache: {e}")
            raise

    def _validate_data_consistency(self):
        """Validate consistency between loaded data structures"""
        issues = []

        # Check that all face_ids have embeddings
        for company_id, faces_list in self.faces.items():
            for face in faces_list:
                face_id = face.get('face_id')
                if face_id and face_id not in self.embeddings:
                    issues.append(f"Face {face_id} has no embedding")

        # Check that all user face references exist in faces
        for company_id, users in self.users.items():
            for user_id, user_data in users.items():
                for face_id in user_data.get('faces', []):
                    if face_id not in self.embeddings:
                        issues.append(f"User {user_id} references non-existent face {face_id}")

        if issues:
            self.logger.warning(f"Data consistency issues found: {len(issues)}")
            for issue in issues[:10]:  # Log first 10 issues
                self.logger.warning(f"  - {issue}")
        else:
            self.logger.info("Data consistency validation passed")
    
    def get_supported_tasks(self) -> List[str]:
        """Return list of supported task types"""
        return [
            # Management tasks (cache sync)
            'create_company',
            'delete_company', 
            'create_user',
            'delete_user',
            'add_face',
            'delete_face',
            
            # Processing tasks
            'face_recognition',
            'face_detection', 
            'face_embedding',
            'get_user_faces',
            'get_cache_stats',
            'health_check'
        ]
    
    def handle_task(self, task_type: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Handle a specific task and return result"""
        self.logger.info(f"Processing task: {task_type}")
        
        try:
            # Route to appropriate handler
            handler_method = f"_handle_{task_type}"
            if hasattr(self, handler_method):
                result = getattr(self, handler_method)(parameters)
                self.logger.info(f"Task {task_type} completed successfully")
                return result
            else:
                error_msg = f"Unsupported task type: {task_type}"
                self.logger.error(error_msg)
                return {"status": "error", "error": error_msg}
                
        except Exception as e:
            error_msg = f"Task {task_type} failed: {str(e)}"
            self.logger.error(error_msg)
            return {"status": "error", "error": error_msg}
    
    # =============================================================================
    # VALIDATION METHODS
    # =============================================================================
    
    def _validate_base64(self, image_base64: str) -> Dict[str, Any]:
        """
        Validate base64 string format
        Returns: {"valid": bool, "error": str or None}
        """
        if not image_base64:
            return {"valid": False, "error": "image_base64 is empty"}
        
        if not isinstance(image_base64, str):
            return {"valid": False, "error": "image_base64 must be a string"}
        
        # Check if it's valid base64
        try:
            # Remove potential data URL prefix (e.g., "data:image/jpeg;base64,")
            if ',' in image_base64:
                image_base64 = image_base64.split(',', 1)[1]
            
            # Attempt to decode
            decoded = base64.b64decode(image_base64, validate=True)
            
            if len(decoded) == 0:
                return {"valid": False, "error": "Decoded image data is empty"}
            
            # Check for common image file signatures
            # JPEG: FF D8 FF
            # PNG: 89 50 4E 47
            # WebP: RIFF....WEBP (52 49 46 46 at start, 57 45 42 50 at offset 8)
            is_jpeg = decoded[:3] == b'\xff\xd8\xff'
            is_png = decoded[:4] == b'\x89PNG'
            is_webp = len(decoded) > 12 and decoded[:4] == b'RIFF' and decoded[8:12] == b'WEBP'

            if not (is_jpeg or is_png or is_webp):
                return {"valid": False, "error": "Image data does not appear to be JPEG, PNG, or WebP format"}
            
            return {"valid": True, "error": None}
            
        except base64.binascii.Error:
            return {"valid": False, "error": "Invalid base64 encoding"}
        except Exception as e:
            return {"valid": False, "error": f"Base64 validation failed: {str(e)}"}
    
    def _validate_and_decode_image(self, image_base64: str) -> Tuple[bool, Optional[np.ndarray], Optional[str]]:
        """
        Validate and decode base64 image
        Returns: (success: bool, image: np.ndarray or None, error_msg: str or None)
        """
        # First validate base64 format
        validation = self._validate_base64(image_base64)
        if not validation["valid"]:
            return False, None, validation["error"]
        
        # Now try to decode as image
        try:
            image = self._base64_to_image(image_base64)
            
            # Validate image dimensions
            if image.shape[0] < 10 or image.shape[1] < 10:
                return False, None, "Image dimensions too small (minimum 10x10 pixels)"
            
            if image.shape[0] > 4096 or image.shape[1] > 4096:
                return False, None, "Image dimensions too large (maximum 4096x4096 pixels)"
            
            return True, image, None
            
        except Exception as e:
            return False, None, f"Failed to decode image: {str(e)}"
    
    def _detect_faces_in_image(self, image: np.ndarray) -> Tuple[bool, Optional[List], Optional[str]]:
        """
        Detect faces in image with validation
        Returns: (success: bool, faces: List or None, error_msg: str or None)
        """
        try:
            faces = self.insightface_app.get(image)
            
            if not faces or len(faces) == 0:
                return False, None, "No faces detected in image"
            
            return True, faces, None
            
        except Exception as e:
            return False, None, f"Face detection failed: {str(e)}"
    
    # =============================================================================
    # MANAGEMENT TASKS (Cache Synchronization)
    # =============================================================================
    
    def _handle_create_company(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new company"""
        company_id = params.get('company_id')
        
        if not company_id:
            return {"status": "error", "error": "company_id is required"}
        
        # Initialize company data structures
        self.companies[company_id] = {
            'created_at': int(time.time()),
            'worker_id': self.worker_id
        }
        self.users[company_id] = {}
        self.faces[company_id] = []
        
        self.logger.info(f"Company created: {company_id}")
        return {
            "status": "success", 
            "result": {"success": True, "company_id": company_id}
        }
    
    def _handle_delete_company(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete company and all associated data"""
        company_id = params.get('company_id')
        
        if not company_id:
            return {"status": "error", "error": "company_id is required"}
        
        # Clean up all company data
        if company_id in self.companies:
            # Remove all face embeddings for this company
            if company_id in self.faces:
                for face_data in self.faces[company_id]:
                    face_id = face_data.get('face_id')
                    if face_id in self.embeddings:
                        del self.embeddings[face_id]
            
            # Remove company data
            del self.companies[company_id]
            if company_id in self.users:
                del self.users[company_id]
            if company_id in self.faces:
                del self.faces[company_id]
        
        self.logger.info(f"Company deleted: {company_id}")
        return {
            "status": "success",
            "result": {"success": True, "company_id": company_id}
        }
    
    def _handle_create_user(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Create a new user with their first face"""
        company_id = params.get('company_id')
        user_id = params.get('user_id')
        face_id = params.get('face_id')
        image_base64 = params.get('image_base64')
        
        if not all([company_id, user_id, face_id, image_base64]):
            return {"status": "error", "error": "Missing required parameters: company_id, user_id, face_id, image_base64"}
        
        # Ensure company exists
        if company_id not in self.companies:
            return {"status": "error", "error": f"Company {company_id} does not exist"}
        
        # Validate and decode image
        success, image, error_msg = self._validate_and_decode_image(image_base64)
        if not success:
            return {"status": "error", "error": error_msg}
        
        # Detect faces
        success, faces, error_msg = self._detect_faces_in_image(image)
        if not success:
            return {"status": "error", "error": error_msg}
        
        # Get best face
        best_face = max(faces, key=lambda x: x.det_score)
        
        # Generate embedding with alignment
        try:
            embedding = self._generate_embedding_with_alignment(image, best_face)
        except Exception as e:
            return {"status": "error", "error": f"Failed to generate embedding: {str(e)}"}
        
        # Extract face info
        bbox = self._extract_bbox(best_face)
        
        # Store user data
        if company_id not in self.users:
            self.users[company_id] = {}
        
        self.users[str(company_id)][str(user_id)] = {
            'user_id': user_id,
            'faces': [face_id],
            'created_at': int(time.time())
        }
        
        # Store face data with detection info
        face_data = {
            'face_id': face_id,
            'user_id': user_id,
            'created_at': int(time.time()),
            'bbox': bbox,
            'confidence': float(best_face.det_score),
            'keypoints': best_face.kps.tolist() if hasattr(best_face, 'kps') else None
        }
        
        if company_id not in self.faces:
            self.faces[company_id] = []
        self.faces[company_id].append(face_data)
        
        # Store embedding
        self.embeddings[str(face_id)] = embedding
        
        self.logger.info(f"User created: {user_id} in company {company_id} with face {face_id}")
        return {
            "status": "success",
            "result": {"embedding": embedding, "user_id": user_id}
        }
    
    def _handle_delete_user(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete user and all their faces"""
        company_id = params.get('company_id')
        user_id = params.get('user_id')
        
        if not all([company_id, user_id]):
            return {"status": "error", "error": "Missing required parameters: company_id, user_id"}
        
        # Remove user and all their faces
        success = False
        if company_id in self.users and user_id in self.users[company_id]:
            user_data = self.users[company_id][user_id]
            
            # Remove all face embeddings for this user
            for face_id in user_data.get('faces', []):
                if face_id in self.embeddings:
                    del self.embeddings[face_id]
            
            # Remove faces from company faces list
            if company_id in self.faces:
                self.faces[company_id] = [
                    face for face in self.faces[company_id] 
                    if face.get('user_id') != user_id
                ]
            
            # Remove user
            del self.users[company_id][user_id]
            success = True
        
        self.logger.info(f"User deleted: {user_id} from company {company_id}")
        return {
            "status": "success",
            "result": {"success": success, "user_id": user_id}
        }
    
    def _handle_add_face(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Add additional face to existing user"""
        company_id = params.get('company_id')
        user_id = params.get('user_id')
        face_id = params.get('face_id')
        image_base64 = params.get('image_base64')
        
        if not all([company_id, user_id, face_id, image_base64]):
            return {"status": "error", "error": "Missing required parameters: company_id, user_id, face_id, image_base64"}
        
        # Check if user exists
        if (company_id not in self.users or 
            user_id not in self.users[company_id]):
            return {"status": "error", "error": f"User {user_id} not found in company {company_id}"}
        
        # Validate and decode image
        success, image, error_msg = self._validate_and_decode_image(image_base64)
        if not success:
            return {"status": "error", "error": error_msg}
        
        # Detect faces
        success, faces, error_msg = self._detect_faces_in_image(image)
        if not success:
            return {"status": "error", "error": error_msg}
        
        # Get best face
        best_face = max(faces, key=lambda x: x.det_score)
        
        # Generate embedding with alignment
        try:
            embedding = self._generate_embedding_with_alignment(image, best_face)
        except Exception as e:
            return {"status": "error", "error": f"Failed to generate embedding: {str(e)}"}
        
        # Extract face info
        bbox = self._extract_bbox(best_face)
        
        # Add face to user
        self.users[str(company_id)][str(user_id)]['faces'].append(face_id)
        
        # Store face data with detection info
        face_data = {
            'face_id': face_id,
            'user_id': user_id,
            'created_at': int(time.time()),
            'bbox': bbox,
            'confidence': float(best_face.det_score),
            'keypoints': best_face.kps.tolist() if hasattr(best_face, 'kps') else None
        }
        self.faces[company_id].append(face_data)
        
        # Store embedding
        self.embeddings[str(face_id)] = embedding
        
        self.logger.info(f"Face added: {face_id} to user {user_id}")
        return {
            "status": "success",
            "result": {"embedding": embedding, "face_id": face_id}
        }
    
    def _handle_delete_face(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Delete specific face from user"""
        company_id = params.get('company_id')
        user_id = params.get('user_id')
        face_id = params.get('face_id')
        
        if not all([company_id, user_id, face_id]):
            return {"status": "error", "error": "Missing required parameters: company_id, user_id, face_id"}
        
        success = False
        
        # Remove face from user's face list
        if (company_id in self.users and 
            user_id in self.users[company_id] and
            face_id in self.users[company_id][user_id].get('faces', [])):
            
            self.users[company_id][user_id]['faces'].remove(face_id)
            success = True
        
        # Remove from company faces
        if company_id in self.faces:
            self.faces[company_id] = [
                face for face in self.faces[company_id] 
                if face.get('face_id') != face_id
            ]
        
        # Remove embedding
        if face_id in self.embeddings:
            del self.embeddings[face_id]
            success = True
        
        self.logger.info(f"Face deleted: {face_id}")
        return {
            "status": "success",
            "result": {"success": success, "face_id": face_id}
        }
    
    # =============================================================================
    # PROCESSING TASKS
    # =============================================================================
    
    def _handle_face_recognition(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Face recognition - find matching user"""
        company_id = params.get('company_id')
        image_base64 = params.get('image_base64')
        
        if not all([company_id, image_base64]):
            return {"status": "error", "error": "Missing required parameters: company_id, image_base64"}
        
        # Check if company exists
        if company_id not in self.companies:
            return {"status": "error", "error": f"Company {company_id} not found"}
        
        # Validate and decode image
        success, image, error_msg = self._validate_and_decode_image(image_base64)
        if not success:
            return {"status": "error", "error": error_msg}
        
        # Detect faces
        success, faces, error_msg = self._detect_faces_in_image(image)
        if not success:
            return {"status": "error", "error": error_msg}
        
        # Get best face
        best_face = max(faces, key=lambda x: x.det_score)
        
        # Generate embedding with alignment
        try:
            query_embedding = self._generate_embedding_with_alignment(image, best_face)
        except Exception as e:
            return {"status": "error", "error": f"Failed to generate embedding: {str(e)}"}
        
        # Extract bbox
        bbox = self._extract_bbox(best_face)
        
        # Real recognition logic
        best_match = None
        best_confidence = 0.0
        
        # Search through all faces in the company
        if company_id in self.faces:
            for face_data in self.faces[company_id]:
                face_id = face_data['face_id']
                if face_id in self.embeddings:
                    # Real similarity calculation
                    confidence = self._calculate_real_similarity(
                        query_embedding, self.embeddings[face_id]
                    )
                    
                    if confidence > best_confidence:
                        best_confidence = confidence
                        best_match = face_data['user_id']
        
        # Use configurable recognition threshold
        if best_confidence >= self.recognition_threshold:
            user_id = best_match
        else:
            user_id = None

        self.logger.info(f"Face recognition: user={user_id}, confidence={best_confidence:.3f}, threshold={self.recognition_threshold}")
        return {
            "status": "success",
            "result": {
                "user_id": user_id,
                "confidence": best_confidence,
                "bbox": bbox
            }
        }
    
    def _handle_face_detection(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Real face detection using InsightFace"""
        image_base64 = params.get('image_base64')
        
        if not image_base64:
            return {"status": "error", "error": "image_base64 is required"}
        
        # Validate and decode image
        success, image, error_msg = self._validate_and_decode_image(image_base64)
        if not success:
            return {"status": "error", "error": error_msg}
        
        try:
            # Use InsightFace for face detection
            faces = self.insightface_app.get(image)
            
            # Extract bboxes from detected faces
            bboxes = []
            for face in faces:
                bbox = self._extract_bbox(face)
                bboxes.append(bbox)
            
            face_count = len(faces)
            
            self.logger.info(f"InsightFace detection: {face_count} faces found")
            return {
                "status": "success", 
                "result": {
                    "faces_detected": face_count,
                    "bboxes": bboxes
                }
            }
            
        except Exception as e:
            self.logger.error(f"InsightFace detection failed: {e}")
            return {
                "status": "error",
                "error": f"Face detection failed: {str(e)}"
            }
    
    def _handle_face_embedding(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Generate face embedding from image"""
        image_base64 = params.get('image_base64')
        
        if not image_base64:
            return {"status": "error", "error": "image_base64 is required"}
        
        # Validate and decode image
        success, image, error_msg = self._validate_and_decode_image(image_base64)
        if not success:
            return {"status": "error", "error": error_msg}
        
        # Detect faces
        success, faces, error_msg = self._detect_faces_in_image(image)
        if not success:
            return {"status": "error", "error": error_msg}
        
        # Get best face
        best_face = max(faces, key=lambda x: x.det_score)
        
        # Generate embedding with alignment
        try:
            embedding = self._generate_embedding_with_alignment(image, best_face)
            
            self.logger.info(f"Generated embedding with {len(embedding)} dimensions")
            return {
                "status": "success",
                "result": {"embedding": embedding}
            }
            
        except Exception as e:
            self.logger.error(f"Face embedding generation failed: {e}")
            return {
                "status": "error",
                "error": f"Face embedding generation failed: {str(e)}"
            }
    
    def _handle_get_user_faces(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get list of face IDs for a user"""
        company_id = params.get('company_id')
        user_id = params.get('user_id')
        
        if not all([company_id, user_id]):
            return {"status": "error", "error": "Missing required parameters: company_id, user_id"}
        
        face_ids = []
        if (company_id in self.users and 
            user_id in self.users[company_id]):
            face_ids = self.users[company_id][user_id].get('faces', [])
        
        return {
            "status": "success",
            "result": {"face_ids": face_ids}
        }
    
    def _handle_get_cache_stats(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Get cache statistics"""
        total_users = sum(len(users) for users in self.users.values())
        total_faces = sum(len(faces) for faces in self.faces.values())
        
        stats = {
            "worker_id": self.worker_id,
            "companies": len(self.companies),
            "total_users": total_users,
            "total_faces": total_faces,
            "total_embeddings": len(self.embeddings),
            "uptime": int(time.time()),  # Mock uptime
            "memory_usage": {
                "companies": len(str(self.companies)),
                "users": len(str(self.users)), 
                "faces": len(str(self.faces)),
                "embeddings": len(str(self.embeddings))
            }
        }
        
        return {"status": "success", "result": stats}
    
    def _handle_health_check(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Health check"""
        return {
            "status": "success",
            "result": {
                "worker_id": self.worker_id,
                "status": "healthy",
                "timestamp": int(time.time() * 1000),
                "version": "1.0.0-real"
            }
        }
    
    # =============================================================================
    # FACE PROCESSING METHODS
    # =============================================================================
    
    def _base64_to_image(self, image_base64: str) -> np.ndarray:
        """Convert base64 string to OpenCV image"""
        try:
            # Remove potential data URL prefix
            if ',' in image_base64:
                image_base64 = image_base64.split(',', 1)[1]
            
            # Decode base64 to bytes
            image_bytes = base64.b64decode(image_base64)
            
            # Convert bytes to numpy array
            nparr = np.frombuffer(image_bytes, np.uint8)
            
            # Decode image
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            
            if image is None:
                raise ValueError("Failed to decode image from base64")
            
            # Convert BGR to RGB for InsightFace
            image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            
            return image_rgb
            
        except Exception as e:
            self.logger.error(f"Failed to convert base64 to image: {e}")
            raise ValueError(f"Invalid image data: {e}")
    
    def _extract_bbox(self, face) -> List[int]:
        """Extract bounding box from face detection result"""
        return [
            int(face.bbox[0]),  # x
            int(face.bbox[1]),  # y
            int(face.bbox[2] - face.bbox[0]),  # width
            int(face.bbox[3] - face.bbox[1])   # height
        ]
    
    def _align_face(self, image: np.ndarray, face, target_size: Tuple[int, int] = (112, 112)) -> np.ndarray:
        """
        Align face using detected keypoints to normalize pose and orientation
        
        Args:
            image: Input image (RGB)
            face: InsightFace detection result with keypoints
            target_size: Output size for aligned face (default: 112x112)
        
        Returns:
            Aligned face image (RGB, uint8)
        """
        try:
            from skimage import transform as trans
            
            # Get detected keypoints (5 points: left eye, right eye, nose, left mouth, right mouth)
            src_pts = face.kps.astype(np.float32)
            
            # Use reference points scaled to target size
            scale_x = target_size[0] / 112.0
            scale_y = target_size[1] / 112.0
            dst_pts = self.reference_points * [scale_x, scale_y]
            
            # Compute similarity transformation matrix
            tform = trans.SimilarityTransform()
            tform.estimate(src_pts, dst_pts)
            
            # Apply transformation to align face
            aligned_face = trans.warp(
                image, 
                tform.inverse, 
                output_shape=target_size,
                mode='edge',
                preserve_range=True
            )
            
            # Convert to uint8
            aligned_face = aligned_face.astype(np.uint8)
            
            self.logger.debug(f"Face aligned to {target_size}")
            return aligned_face
            
        except Exception as e:
            self.logger.warning(f"Face alignment failed, using original crop: {e}")
            # Fallback: just crop the face region
            bbox = face.bbox.astype(int)
            x1, y1, x2, y2 = bbox[0], bbox[1], bbox[2], bbox[3]
            
            # Add padding
            h, w = image.shape[:2]
            padding = 20
            x1 = max(0, x1 - padding)
            y1 = max(0, y1 - padding)
            x2 = min(w, x2 + padding)
            y2 = min(h, y2 + padding)
            
            face_crop = image[y1:y2, x1:x2]
            
            # Resize to target size
            face_crop = cv2.resize(face_crop, target_size, interpolation=cv2.INTER_LINEAR)
            
            return face_crop
    
    def _generate_embedding_with_alignment(self, image: np.ndarray, face) -> List[float]:
        """
        Generate face embedding with proper alignment
        
        Args:
            image: Original image (RGB)
            face: InsightFace detection result
        
        Returns:
            Face embedding vector
        """
        try:
            # First align the face
            aligned_face = self._align_face(image, face)
            
            # Get embedding from aligned face
            # Re-detect on aligned face to get embedding
            aligned_faces = self.insightface_app.get(aligned_face)
            
            if not aligned_faces:
                # Fallback: use original embedding if re-detection fails
                self.logger.warning("Re-detection on aligned face failed, using original embedding")
                embedding = face.embedding.tolist()
            else:
                # Use embedding from aligned face
                aligned_face_obj = aligned_faces[0]
                embedding = aligned_face_obj.embedding.tolist()
            
            self.logger.info(f"Generated embedding with alignment: {len(embedding)} dimensions")
            return embedding
            
        except Exception as e:
            self.logger.error(f"Failed to generate embedding with alignment: {e}")
            raise ValueError(f"Embedding generation failed: {e}")
    
    def _calculate_real_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate real cosine similarity between embeddings"""
        try:
            if len(embedding1) != len(embedding2):
                self.logger.warning(f"Embedding dimension mismatch: {len(embedding1)} vs {len(embedding2)}")
                return 0.0
        
            # Convert to numpy arrays for efficient calculation
            emb1 = np.array(embedding1)
            emb2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(emb1, emb2)
            norm1 = np.linalg.norm(emb1)
            norm2 = np.linalg.norm(emb2)
            
            if norm1 == 0 or norm2 == 0:
                self.logger.warning("Zero norm detected in embedding")
                return 0.0
            
            similarity = dot_product / (norm1 * norm2)
            
            # Ensure similarity is between 0 and 1
            similarity = max(0.0, min(1.0, similarity))
            
            return float(similarity)
            
        except Exception as e:
            self.logger.error(f"Similarity calculation failed: {e}")
            return 0.0