from minio import Minio
from minio.error import S3Error
from datetime import datetime
from src.core.config import get_settings
import io
import uuid


class MinIoService:
    def __init__(self):
        settings = get_settings()
        
        self.bucket_name = settings.MINIO_BUCKET_NAME
        
        self.minio_client = self.client = Minio(
            endpoint=settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=False
        )
        
        if not self.minio_client.bucket_exists(self.bucket_name):
            self.minio_client.make_bucket(self.bucket_name)
            print(f"✅ Created bucket: {self.bucket_name}")   

    def upload_face_image(self, image, ext, org_id, user_id, content_type = None, filename = None) -> str:
        upload_result = None
        
        timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
        unique_id = uuid.uuid4().hex[:6]
        object_name = f"{org_id}/{user_id}/{timestamp}_{unique_id}.{ext}"
        image_url = f"{self.bucket_name}/{object_name}"

        try:
            # Upload to MinIO
            upload_result = self.minio_client.put_object(
                bucket_name=self.bucket_name,
                object_name=object_name,
                data=io.BytesIO(image),
                length=len(image),
                content_type=content_type or f"image/{ext}",
                metadata={
                    'user_id': user_id,
                    'org_id': org_id,
                    'original_filename': filename or f"{timestamp}_{unique_id}.{ext}"
                }
            )
            
            print(f"✅ Uploaded {object_name} of size {upload_result} to bucket {self.bucket_name}")
            return image_url
        except S3Error as e:
            print(f"❌ MinIO upload error: {e}")
            return ""
        except Exception as e:
            print(f"❌ Unexpected error during upload: {e}")
            return ""
    
    def delete_org_images(self, org_id: str) -> int:
        """Delete all images for an organization"""
        deleted_count = 0
        try:
            objects = self.minio_client.list_objects(
                bucket_name=self.bucket_name,
                prefix=f"{org_id}/",
                recursive=True
            )
            
            for obj in objects:
                self.minio_client.remove_object(
                    bucket_name=self.bucket_name,
                    object_name=obj.object_name
                )
                deleted_count += 1
            
            print(f"Deleted {deleted_count} images for org {org_id}")
            return deleted_count
            
        except Exception as e:
            print(f"Error deleting org images: {e}")
            return deleted_count
        
    def delete_user_images(self, org_id: str, user_id: str) -> bool:
        """
        Delete all images for a given user from MinIO storage
        """
        try:
            objects = self.minio_client.list_objects(
                bucket_name=self.bucket_name,
                prefix=f"{org_id}/{user_id}/",
                recursive=True
            )
            
            for obj in objects:
                self.minio_client.remove_object(
                    bucket_name=self.bucket_name,
                    object_name=obj.object_name
                )
            
            print(f"✅ Deleted images for user {user_id} in org {org_id}")
            return True
            
        except S3Error as e:
            print(f"❌ MinIO delete error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during delete: {e}")
            return False
        

    def delete_face_image(self, image_url: str) -> bool:
        """
        Delete face image from MinIO storage
        
        Args:
            image_url: Full image URL like "face-images/cgv/4e4bc563-.../20251003_112321_b52f9a.jpg"
            
        Returns:
            True if deleted successfully, False otherwise
        """
        try:
            # Extract object name from URL
            # URL format: "face-images/org_id/user_id/filename.jpg"
            # We need: "org_id/user_id/filename.jpg"
            
            if image_url.startswith(f"{self.bucket_name}/"):
                object_name = image_url[len(self.bucket_name) + 1:]  # Remove "face-images/"
            else:
                object_name = image_url
            
            # Delete the object
            self.minio_client.remove_object(
                bucket_name=self.bucket_name,
                object_name=object_name
            )
            
            print(f"✅ Deleted {object_name} from bucket {self.bucket_name}")
            return True
            
        except S3Error as e:
            print(f"❌ MinIO delete error: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error during delete: {e}")
            return False
    
    