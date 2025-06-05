"""Timing middleware for performance monitoring."""

import time
from typing import Callable
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

from app.core.config import settings


class TimingMiddleware(BaseHTTPMiddleware):
    """Middleware for measuring request processing time."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Measure and record request processing time."""
        
        # Start timing
        start_time = time.perf_counter()
        
        # Add timing context to request
        request.state.start_time = start_time
        
        # Process request
        response = await call_next(request)
        
        # Calculate processing time
        end_time = time.perf_counter()
        process_time = end_time - start_time
        
        # Add timing headers
        response.headers["X-Process-Time"] = str(round(process_time * 1000, 2))  # milliseconds
        
        # Add timing to request state for logging
        request.state.process_time = process_time
        
        # Log slow requests
        if process_time > 1.0:  # Log requests taking more than 1 second
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Slow request detected: {request.method} {request.url.path} "
                f"took {process_time:.3f}s",
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "process_time": process_time,
                    "status_code": response.status_code,
                }
            )
        
        return response


class PerformanceMiddleware(BaseHTTPMiddleware):
    """Advanced performance monitoring middleware."""
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.slow_request_threshold = kwargs.get("slow_request_threshold", 1.0)
        self.very_slow_request_threshold = kwargs.get("very_slow_request_threshold", 5.0)
        self.enable_detailed_timing = kwargs.get("enable_detailed_timing", settings.DEBUG)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor request performance with detailed metrics."""
        
        # Start detailed timing
        timings = {
            "start_time": time.perf_counter(),
            "middleware_start": time.perf_counter(),
        }
        
        # Add performance context to request
        request.state.performance_timings = timings
        
        # Middleware processing time
        middleware_time = time.perf_counter() - timings["middleware_start"]
        timings["middleware_time"] = middleware_time
        
        # Mark start of application processing
        timings["app_start"] = time.perf_counter()
        
        # Process request
        response = await call_next(request)
        
        # Calculate final timings
        end_time = time.perf_counter()
        total_time = end_time - timings["start_time"]
        app_time = end_time - timings["app_start"]
        
        timings.update({
            "end_time": end_time,
            "total_time": total_time,
            "app_time": app_time,
        })
        
        # Add performance headers
        response.headers["X-Response-Time"] = str(round(total_time * 1000, 2))
        
        if self.enable_detailed_timing:
            response.headers["X-App-Time"] = str(round(app_time * 1000, 2))
            response.headers["X-Middleware-Time"] = str(round(middleware_time * 1000, 2))
        
        # Performance logging
        self._log_performance(request, response, timings)
        
        # Store metrics for monitoring
        if settings.METRICS_ENABLED:
            self._record_metrics(request, response, timings)
        
        return response
    
    def _log_performance(self, request: Request, response: Response, timings: dict):
        """Log performance metrics."""
        import logging
        logger = logging.getLogger("performance")
        
        total_time = timings["total_time"]
        
        # Determine log level based on response time
        if total_time >= self.very_slow_request_threshold:
            log_level = logging.ERROR
            log_message = "Very slow request"
        elif total_time >= self.slow_request_threshold:
            log_level = logging.WARNING
            log_message = "Slow request"
        else:
            log_level = logging.INFO
            log_message = "Request completed"
        
        # Log with performance data
        logger.log(
            log_level,
            f"{log_message}: {request.method} {request.url.path} "
            f"({total_time:.3f}s)",
            extra={
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "total_time_ms": round(total_time * 1000, 2),
                "app_time_ms": round(timings["app_time"] * 1000, 2),
                "middleware_time_ms": round(timings["middleware_time"] * 1000, 2),
                "performance_category": self._get_performance_category(total_time),
            }
        )
    
    def _get_performance_category(self, total_time: float) -> str:
        """Categorize request performance."""
        if total_time >= self.very_slow_request_threshold:
            return "very_slow"
        elif total_time >= self.slow_request_threshold:
            return "slow"
        elif total_time >= 0.5:
            return "moderate"
        elif total_time >= 0.1:
            return "fast"
        else:
            return "very_fast"
    
    def _record_metrics(self, request: Request, response: Response, timings: dict):
        """Record metrics for monitoring systems."""
        # This would integrate with Prometheus, StatsD, or other metrics systems
        # For now, we'll just store in request state for potential collection
        
        metrics = {
            "endpoint": f"{request.method} {request.url.path}",
            "status_code": response.status_code,
            "response_time": timings["total_time"],
            "timestamp": timings["start_time"],
        }
        
        # Store in request state
        request.state.metrics = metrics
        
        # TODO: Send to metrics collection system
        # Example: send_to_prometheus(metrics) or send_to_statsd(metrics)


class ResourceMonitoringMiddleware(BaseHTTPMiddleware):
    """Middleware for monitoring resource usage during requests."""
    
    def __init__(self, app, **kwargs):
        super().__init__(app)
        self.enable_memory_monitoring = kwargs.get("enable_memory_monitoring", False)
        self.enable_cpu_monitoring = kwargs.get("enable_cpu_monitoring", False)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Monitor resource usage during request processing."""
        
        import psutil
        import os
        
        # Get initial resource usage
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss if self.enable_memory_monitoring else None
        initial_cpu = process.cpu_percent() if self.enable_cpu_monitoring else None
        
        # Process request
        response = await call_next(request)
        
        # Get final resource usage
        if self.enable_memory_monitoring:
            final_memory = process.memory_info().rss
            memory_diff = final_memory - initial_memory
            response.headers["X-Memory-Usage"] = str(memory_diff)
        
        if self.enable_cpu_monitoring:
            final_cpu = process.cpu_percent()
            response.headers["X-CPU-Usage"] = str(final_cpu)
        
        return response


class RequestTracingMiddleware(BaseHTTPMiddleware):
    """Middleware for distributed tracing."""
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Add tracing context to requests."""
        
        import uuid
        
        # Get or create trace ID
        trace_id = request.headers.get("x-trace-id", str(uuid.uuid4()))
        span_id = str(uuid.uuid4())
        
        # Add tracing context to request
        request.state.trace_id = trace_id
        request.state.span_id = span_id
        request.state.parent_span_id = request.headers.get("x-parent-span-id")
        
        # Process request
        response = await call_next(request)
        
        # Add tracing headers to response
        response.headers["X-Trace-ID"] = trace_id
        response.headers["X-Span-ID"] = span_id
        
        return response
