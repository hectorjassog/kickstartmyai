"""Base API endpoints."""

from fastapi import APIRouter
from app.core.config import settings

router = APIRouter()


@router.get("/")
def read_root():
    """Root endpoint."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "docs": "/docs"
    }


@router.get("/info")
def get_info():
    """Get application information."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": "A FastAPI project with AI capabilities",
        "api_version": "v1"
    }
