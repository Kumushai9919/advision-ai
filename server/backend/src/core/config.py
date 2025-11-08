from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):
    APP_NAME: str = "Kiosk Face Auth - FastAPI"
    VERSION: str = "1.0.0"
    DATABASE_URL: str = "sqlite:///./test.db"
    API_V1_PREFIX: str = "/api/v1"
    MEDIA_ROOT: str = "/data/images"
    
    # MinIO settings
    MINIO_ENDPOINT: str = "minio:9000"
    MINIO_ACCESS_KEY: str = "face_auth_admin"
    MINIO_SECRET_KEY: str = "fvsGtRTY"
    MINIO_BUCKET_NAME: str = "face-images"
    
    # RabbitMQ settings
    RABBITMQ_HOST: str = "rabbitmq"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USERNAME: str = "face_user"
    RABBITMQ_PASSWORD: str = "secure_password"
    RABBITMQ_VHOST: str = "/face_recognition"

    model_config = SettingsConfigDict(env_file=".env")
    
@lru_cache
def get_settings():
    return Settings()