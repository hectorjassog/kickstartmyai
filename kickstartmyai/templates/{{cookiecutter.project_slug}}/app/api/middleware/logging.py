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
        # JSON logging
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
                if hasattr(record, "correlation_id"):
                    log_obj["correlation_id"] = record.correlation_id
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
                
                # Pretty print for development, compact for production
                if settings.is_development():
                    return json.dumps(log_obj, indent=2, ensure_ascii=False)
                else:
                    return json.dumps(log_obj, separators=(',', ':'), ensure_ascii=False)
        
        formatter = JSONFormatter()
        
    else:
        # Enhanced text logging with colors for development
        if settings.is_development():
            try:
                import colorlog
                
                # Colorized formatter for development
                formatter = colorlog.ColoredFormatter(
                    "%(log_color)s%(asctime)s %(bold)s[%(levelname)-8s]%(reset)s "
                    "%(blue)s%(name)s:%(lineno)d%(reset)s - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                    log_colors={
                        'DEBUG': 'cyan',
                        'INFO': 'green',
                        'WARNING': 'yellow',
                        'ERROR': 'red',
                        'CRITICAL': 'red,bg_white',
                    },
                    secondary_log_colors={},
                    style='%'
                )
            except ImportError:
                # Fallback to enhanced standard formatter
                formatter = logging.Formatter(
                    "%(asctime)s [%(levelname)-8s] %(name)s:%(lineno)d - %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S"
                )
        else:
            # Production text format - compact and structured
            formatter = logging.Formatter(
                "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
                datefmt="%Y-%m-%d %H:%M:%S"
            )
    
    # Configure root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL))
    
    # Clear existing handlers
    root_logger.handlers.clear()
    
    # Add console handler
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    
    # Set console handler level based on environment
    if settings.is_development():
        console_handler.setLevel(logging.DEBUG)
    else:
        console_handler.setLevel(logging.INFO)
    
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if settings.LOG_FILE:
        from logging.handlers import RotatingFileHandler
        file_handler = RotatingFileHandler(
            settings.LOG_FILE,
            maxBytes=10*1024*1024,  # 10MB
            backupCount=5
        )
        
        # Always use JSON format for file logging for easier parsing
        json_formatter = JSONFormatter() if settings.LOG_FORMAT == "json" else logging.Formatter(
            "%(asctime)s [%(levelname)s] %(name)s:%(lineno)d - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"
        )
        file_handler.setFormatter(json_formatter)
        root_logger.addHandler(file_handler)
    
    # Set specific logger levels
    logging.getLogger("uvicorn").setLevel(logging.INFO)
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)  # Reduce noise
    logging.getLogger("sqlalchemy.engine").setLevel(
        logging.INFO if settings.DEBUG else logging.WARNING
    )
    
    # Set third-party library log levels to reduce noise
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    
    # Log the configuration for debugging
    logger.info(
        f"Logging configured - Format: {settings.LOG_FORMAT}, "
        f"Level: {settings.LOG_LEVEL}, Environment: {settings.ENVIRONMENT}"
    )


# Initialize logging
setup_logging()
