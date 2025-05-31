"""Health check endpoints."""

from fastapi import HTTPException, status
from sqlalchemy import text
from app.db.session import SessionLocal
from app.core.config import settings


async def health_check():
    """Basic health check endpoint."""
    try:
        # Check database connection
        db = SessionLocal()
        db.execute(text("SELECT 1"))
        db.close()
        
        return {
            "status": "healthy",
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "database": "connected"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Health check failed: {str(e)}"
        )


async def readiness_check():
    """Readiness check for Kubernetes."""
    # Add more comprehensive checks here
    return {"status": "ready"}


async def liveness_check():
    """Liveness check for Kubernetes."""
    return {"status": "alive"}
