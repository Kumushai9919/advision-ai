from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from .database.core import engine, Base
from src.core.logger import logger
from src.core.config import get_settings
from src.api.v1.auth.controller import router as auth_router
from src.api.v1.user.controller import router as user_router
from src.api.v1.worker.controller import router as worker_router
from src.api.v1.org.controller import router as org_router
from src.api.v1.analytics.controller import router as analytics_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting up...")
    Base.metadata.create_all(bind=engine)
    yield
    logger.info("Shutting down...")

app = FastAPI(lifespan=lifespan)
settings = get_settings()

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000", "http://14.138.145.45:3000", "https://advision.solutionaix.com"],  # Add your frontend URLs
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    auth_router,
    prefix=f"{settings.API_V1_PREFIX}",
    tags=["auth"]
)

app.include_router(
    user_router,
    prefix=f"{settings.API_V1_PREFIX}/users",
    tags=["users"]
)

app.include_router(
    analytics_router,
    prefix=f"{settings.API_V1_PREFIX}/analytics",
    tags=["analytics"]
)

app.include_router(
    worker_router,
    prefix=f"{settings.API_V1_PREFIX}/worker",
    tags=["worker"]
)

app.include_router(
    org_router,
    prefix=f"{settings.API_V1_PREFIX}/orgs",
    tags=["orgs"]
)

@app.get("/api/v1/health")
def read_root():
    return {
            "status": "healthy",
            "version": settings.VERSION,
        }