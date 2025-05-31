"""
{{cookiecutter.project_name}} - FastAPI Main Application

This is the main FastAPI application entry point for {{cookiecutter.project_name}}.
"""

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.events import startup_handler, shutdown_handler
from app.api.middleware.cors import setup_cors
from app.api.middleware.logging import LoggingMiddleware
from app.api.middleware.error_handling import ErrorHandlingMiddleware
from app.api.middleware.rate_limiting import RateLimitingMiddleware
from app.api.v1.api import api_router
from app.monitoring.health_checks import health_check


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    await startup_handler()
    yield
    # Shutdown
    await shutdown_handler()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="{{cookiecutter.project_name}}",
        description="{{cookiecutter.project_description}}",
        version="{{cookiecutter.version}}",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        docs_url="/docs",
        redoc_url="/redoc",
        lifespan=lifespan,
    )
    
    # Setup middleware
    app.add_middleware(ErrorHandlingMiddleware)
    app.add_middleware(LoggingMiddleware)
    app.add_middleware(RateLimitingMiddleware)
    setup_cors(app)
    
    # Include routers
    app.include_router(api_router, prefix=settings.API_V1_STR)
    
    # Health check endpoint
    app.get("/health")(health_check)
    
    return app


app = create_application()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info",
    )
