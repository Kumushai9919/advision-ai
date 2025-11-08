from typing import Annotated, Generator
from sqlalchemy.exc import SQLAlchemyError
from src.core.config import get_settings
from fastapi import Depends
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from src.core.logger import logger

settings = get_settings()

DATABASE_URL = settings.DATABASE_URL

# ✅ Configure engine for concurrent requests
engine = create_engine(
    DATABASE_URL,
    pool_size=50,              # ✅ Handle up to 50 concurrent connections
    max_overflow=20,           # ✅ Allow 20 extra connections if needed (total: 70)
    pool_pre_ping=True,        # ✅ Verify connections are alive before using
    pool_recycle=3600,         # ✅ Recycle connections after 1 hour
    echo=False,                # Set to True for SQL query logging
    connect_args={
        "connect_timeout": 10,  # ✅ Connection timeout in seconds
        "application_name": "face_auth_api"  # ✅ Identify app in pg_stat_activity
    }
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """
    Dependency function to get database session.
    Ensures proper cleanup of database connections.
    """
    db = SessionLocal()
    try:
        logger.debug("📊 Database session created")
        yield db
        db.commit()  # ✅ Commit successful transactions
    except SQLAlchemyError as e:
        logger.error(f"❌ Database error: {e}", exc_info=True)
        db.rollback()
        raise
    except Exception as e:
        logger.error(f"❌ Unexpected error: {e}", exc_info=True)
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug("📊 Database session closed")
        
DbSession = Annotated[Session, Depends(get_db)]