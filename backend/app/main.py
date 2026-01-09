"""
TeacherAssist V2 Backend API

FastAPI application for AI-powered presentation generation
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes import generation, health, pexels, presentations, scripts, templates
from app.core.config import settings
from app.services.llm_service import shutdown_llm_service
from app.services.pexels_service import shutdown_pexels_service

# Configure logging
logging.basicConfig(
    level=logging.INFO if not settings.debug else logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    logger.info(f"Starting {settings.app_name} v{settings.app_version}")
    logger.info(f"LLM Provider: {settings.llm_provider}")
    logger.info(f"Debug Mode: {settings.debug}")

    yield

    # Shutdown
    logger.info("Shutting down application...")
    await shutdown_llm_service()
    await shutdown_pexels_service()
    logger.info("Shutdown complete")


# Create FastAPI app
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered presentation generation from Markdown",
    lifespan=lifespan,
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # TODO: Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register routers
app.include_router(health.router)
app.include_router(generation.router)
app.include_router(templates.router)
app.include_router(presentations.router)
app.include_router(pexels.router)
app.include_router(scripts.router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",  # nosec B104 - Development server only
        port=8000,
        reload=settings.debug,
    )
