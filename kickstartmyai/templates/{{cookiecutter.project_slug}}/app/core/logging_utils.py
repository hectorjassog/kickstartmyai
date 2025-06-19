"""Logging utilities for structured business logic logging."""

import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional
from contextlib import contextmanager

from app.core.config import settings


def get_logger(name: str) -> logging.Logger:
    """Get a configured logger instance."""
    return logging.getLogger(name)


def log_function_call(
    logger: Optional[logging.Logger] = None,
    level: int = logging.INFO,
    include_args: bool = False,
    include_result: bool = False
):
    """Decorator to log function calls with timing."""
    def decorator(func: Callable) -> Callable:
        nonlocal logger
        if logger is None:
            logger = get_logger(func.__module__)
            
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            log_data = {"function": func_name}
            if include_args:
                log_data["args"] = args
                log_data["kwargs"] = kwargs
            
            logger.info("Function call started", extra=log_data)
            
            try:
                result = await func(*args, **kwargs)
                duration = time.time() - start_time
                
                log_data["duration_ms"] = round(duration * 1000, 2)
                if include_result:
                    log_data["result"] = result
                    
                logger.info("Function call completed", extra=log_data)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                log_data.update({
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                logger.error("Function call failed", extra=log_data, exc_info=True)
                raise
                
        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            func_name = f"{func.__module__}.{func.__qualname__}"
            
            log_data = {"function": func_name}
            if include_args:
                log_data["args"] = args
                log_data["kwargs"] = kwargs
            
            logger.info("Function call started", extra=log_data)
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                
                log_data["duration_ms"] = round(duration * 1000, 2)
                if include_result:
                    log_data["result"] = result
                    
                logger.info("Function call completed", extra=log_data)
                return result
                
            except Exception as e:
                duration = time.time() - start_time
                log_data.update({
                    "duration_ms": round(duration * 1000, 2),
                    "error": str(e),
                    "error_type": type(e).__name__
                })
                logger.error("Function call failed", extra=log_data, exc_info=True)
                raise
        
        return async_wrapper if hasattr(func, '__await__') else sync_wrapper
    return decorator


@contextmanager
def log_operation(
    operation_name: str,
    logger: Optional[logging.Logger] = None,
    level: int = logging.INFO,
    **context_data
):
    """Context manager for logging operations with timing."""
    if logger is None:
        logger = get_logger(__name__)
    
    start_time = time.time()
    log_data = {"operation": operation_name, **context_data}
    
    logger.log(level, f"Operation started: {operation_name}", extra=log_data)
    
    try:
        yield log_data
        duration = time.time() - start_time
        log_data["duration_ms"] = round(duration * 1000, 2)
        logger.log(level, f"Operation completed: {operation_name}", extra=log_data)
        
    except Exception as e:
        duration = time.time() - start_time
        log_data.update({
            "duration_ms": round(duration * 1000, 2),
            "error": str(e),
            "error_type": type(e).__name__
        })
        logger.error(f"Operation failed: {operation_name}", extra=log_data, exc_info=True)
        raise


def log_ai_interaction(
    provider: str,
    model: str,
    tokens_used: int,
    cost: Optional[float] = None,
    logger: Optional[logging.Logger] = None
):
    """Log AI API interactions for monitoring and cost tracking."""
    if logger is None:
        logger = get_logger(__name__)
    
    log_data = {
        "ai_provider": provider,
        "ai_model": model,
        "tokens_used": tokens_used,
    }
    
    if cost is not None:
        log_data["cost_usd"] = cost
    
    logger.info("AI API interaction", extra=log_data)


def log_database_operation(
    operation: str,
    table: str,
    duration_ms: float,
    rows_affected: Optional[int] = None,
    logger: Optional[logging.Logger] = None
):
    """Log database operations for performance monitoring."""
    if logger is None:
        logger = get_logger(__name__)
    
    log_data = {
        "db_operation": operation,
        "db_table": table,
        "duration_ms": round(duration_ms, 2)
    }
    
    if rows_affected is not None:
        log_data["rows_affected"] = rows_affected
    
    logger.info("Database operation", extra=log_data)


class StructuredLogger:
    """Helper class for structured logging with context."""
    
    def __init__(self, logger: logging.Logger, **default_context):
        self.logger = logger
        self.default_context = default_context
    
    def _log(self, level: int, message: str, **extra_context):
        """Internal logging method with context merging."""
        context = {**self.default_context, **extra_context}
        self.logger.log(level, message, extra=context)
    
    def debug(self, message: str, **context):
        self._log(logging.DEBUG, message, **context)
    
    def info(self, message: str, **context):
        self._log(logging.INFO, message, **context)
    
    def warning(self, message: str, **context):
        self._log(logging.WARNING, message, **context)
    
    def error(self, message: str, **context):
        self._log(logging.ERROR, message, **context)
    
    def critical(self, message: str, **context):
        self._log(logging.CRITICAL, message, **context)


# Example usage patterns
def example_usage():
    """
    Example demonstrating various logging patterns.
    
    This function shows best practices for using the enhanced logging system.
    """
    
    # 1. Basic structured logging
    logger = get_logger(__name__)
    logger.info("Basic log message", extra={
        "user_id": "123",
        "action": "login",
        "ip_address": "192.168.1.1"
    })
    
    # 2. Using structured logger with context
    user_logger = StructuredLogger(logger, user_id="123", session_id="abc-456")
    user_logger.info("User performed action", action="create_conversation")
    user_logger.warning("Rate limit approaching", remaining_requests=5)
    
    # 3. Using operation context manager
    with log_operation("process_user_request", logger=logger, user_id="123"):
        # Simulate some work
        time.sleep(0.1)
        logger.info("Processing step completed", step="validation")
    
    # 4. Using function decorator
    @log_function_call(logger=logger, include_args=True)
    async def example_function(user_id: str, data: dict):
        logger.info("Processing user data", data_size=len(str(data)))
        return {"status": "success", "processed_items": 42}
    
    # 5. AI interaction logging
    log_ai_interaction(
        provider="openai",
        model="gpt-4",
        tokens_used=150,
        cost=0.003,
        logger=logger
    )
    
    # 6. Database operation logging
    log_database_operation(
        operation="SELECT",
        table="conversations",
        duration_ms=25.5,
        rows_affected=10,
        logger=logger
    )
    
    # 7. Error handling with context
    try:
        raise ValueError("Something went wrong")
    except Exception as e:
        logger.error(
            "Operation failed",
            extra={
                "error_type": type(e).__name__,
                "error_message": str(e),
                "user_id": "123",
                "operation": "example_operation"
            },
            exc_info=True
        )


"""
CONFIGURATION EXAMPLES:

1. Development with colors (text format):
   ENVIRONMENT=development
   LOG_FORMAT=text
   LOG_LEVEL=DEBUG

2. Development with pretty JSON:
   ENVIRONMENT=development  
   LOG_FORMAT=json
   LOG_LEVEL=DEBUG

3. Production with compact JSON:
   ENVIRONMENT=production
   LOG_FORMAT=json
   LOG_LEVEL=INFO

4. Production with text format:
   ENVIRONMENT=production
   LOG_FORMAT=text
   LOG_LEVEL=WARNING

The logging system will automatically:
- Add colors in development with text format
- Pretty-print JSON in development  
- Use compact JSON in production
- Include line numbers, module names, and timestamps
- Provide structured logging with extra context
- Support request IDs, correlation IDs, and performance metrics
"""
