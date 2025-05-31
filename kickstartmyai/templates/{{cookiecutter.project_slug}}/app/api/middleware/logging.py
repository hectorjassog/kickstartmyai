"""Logging middleware for request/response logging."""

import time
import logging
import uuid
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import StreamingResponse

from app.core.config import settings


logger = logging.getLogger(__name__)


class LoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for logging HTTP requests and responses."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process the request and log details."""
        
        # Generate request ID if not present
        request_id = request.headers.get("x-request-id", str(uuid.uuid4()))
        
        # Start timing
        start_time = time.time()
        
        # Get client info
        client_ip = request.client.host if request.client else "unknown"
        forwarded_for = request.headers.get("x-forwarded-for")
        real_ip = forwarded_for.split(",")[0].strip() if forwarded_for else client_ip
        user_agent = request.headers.get("user-agent", "unknown")
        
        # Log request
        logger.info(
            "Request started",
            extra={
                "request_id": request_id,
                "method": request.method,
                "url": str(request.url),
                "path": request.url.path,
                "query_params": dict(request.query_params),
                "client_ip": client_ip,
                "real_ip": real_ip,
                "user_agent": user_agent,
                "headers": dict(request.headers) if settings.DEBUG else None,
            }
        )
        
        # Process request
        try:
            response = await call_next(request)
            
            # Calculate processing time
            process_time = time.time() - start_time
            
            # Get response size if possible
            response_size = None
            if hasattr(response, "body"):
                response_size = len(response.body)
            elif isinstance(response, StreamingResponse):
                response_size = "streaming"
            
            # Log response
            logger.info(
                "Request completed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status_code": response.status_code,
                    "process_time": round(process_time * 1000, 2),  # ms
                    "response_size": response_size,
                    "client_ip": client_ip,
                    "real_ip": real_ip,
                }
            )
            
            # Add request ID to response headers
            response.headers["x-request-id"] = request_id
            response.headers["x-process-time"] = str(round(process_time * 1000, 2))
            
            return response
            
        except Exception as e:
            # Calculate processing time for errors
            process_time = time.time() - start_time
            
            # Log error
            logger.error(
                "Request failed",
                extra={
                    "request_id": request_id,
                    "method": request.method,
                    "path": request.url.path,
                    "error": str(e),
                    "error_type": type(e).__name__,
                    "process_time": round(process_time * 1000, 2),
                    "client_ip": client_ip,
                    "real_ip": real_ip,
                },
                exc_info=True
            )
            
            # Re-raise the exception
            raise


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Middleware for structured logging with additional context."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add structured logging context to the request."""
        
        # Add context to the request
        request.state.logging_context = {
            "service": settings.PROJECT_NAME,
            "version": settings.VERSION,
            "environment": settings.ENVIRONMENT,
            "request_id": request.headers.get("x-request-id", str(uuid.uuid4())),
            "user_id": None,  # Will be populated by auth middleware
            "correlation_id": request.headers.get("x-correlation-id"),
        }
        
        response = await call_next(request)
        return response


def setup_logging():
    """Setup application logging configuration."""
    
    # Configure logging format
    if settings.LOG_FORMAT == "json":
        # JSON logging for production
        import json
        
        class JSONFormatter(logging.Formatter):
            def format(self, record):
                log_obj = {
                    "timestamp": self.formatTime(record),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                    "module": record.module,
                    "function": record.funcName,
                    "line": record.lineno,
                }
                
                # Add extra fields
                if hasattr(record, "request_id"):
                    log_obj["request_id"] = record.request_id
                if hasattr(record, "user_id"):
                    log_obj["user_id"] = record.user_id
                if hasattr(record, "method"):
                    log_obj["http_method"] = record.method
                if hasattr(record, "path"):
                    log_obj["http_path"] = record.path
                if hasattr(record, "status_code"):
                    log_obj["http_status"] = record.status_code
                if hasattr(record, "process_time"):
                    log_obj["duration_ms"] = record.process_time
                
                # Add exception info
                if record.exc_info:
                    log_obj["exception"] = self.formatException(record.exc_info)
                
                return json.dumps(log_obj)
        
        formatter = JSONFormatter()
    else:
        # Standard logging for development
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if settings.LOG_FILE:
        file_handler = logging.FileHandler(settings.LOG_FILE)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )


# Initialize logging
setup_logging()
