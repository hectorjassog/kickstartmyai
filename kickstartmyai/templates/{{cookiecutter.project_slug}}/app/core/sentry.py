"""
Sentry integration for error tracking and performance monitoring.
Cost-optimized configuration to stay within budget.
"""

import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
from sentry_sdk.integrations.asyncio import AsyncioIntegration
from sentry_sdk.integrations.httpx import HttpxIntegration
from sentry_sdk.integrations.redis import RedisIntegration
from sentry_sdk.integrations.logging import LoggingIntegration
import logging

from app.core.config import settings


def init_sentry() -> None:
    """Initialize Sentry for error tracking and performance monitoring."""
    
    if not settings.SENTRY_DSN:
        logging.info("Sentry DSN not configured, skipping Sentry initialization")
        return
    
    # Cost-optimized Sentry configuration
    sentry_sdk.init(
        dsn=settings.SENTRY_DSN,
        environment=settings.SENTRY_ENVIRONMENT,
        release=settings.SENTRY_RELEASE,
        
        # Sampling rates for cost optimization
        sample_rate=settings.SENTRY_SAMPLE_RATE,  # Error sampling
        traces_sample_rate=settings.SENTRY_TRACES_SAMPLE_RATE,  # Performance sampling
        
        # Integrations
        integrations=[
            FastApiIntegration(auto_enabling_integrations=False),
            SqlalchemyIntegration(),
            AsyncioIntegration(),
            HttpxIntegration(),
            RedisIntegration(),
            LoggingIntegration(
                level=logging.INFO,  # Capture info and above
                event_level=logging.ERROR  # Only send errors as events
            ),
        ],
        
        # Cost optimization settings
        attach_stacktrace=True,
        send_default_pii=False,  # Privacy and cost optimization
        max_breadcrumbs=25,  # Reduced from default 100
        
        # Custom tags for better filtering
        tags={
            "component": "{{cookiecutter.project_slug}}",
            "cost_optimized": "true"
        },
        
        # Before send hooks for filtering
        before_send=filter_events,
        before_send_transaction=filter_transactions,
    )
    
    logging.info(f"Sentry initialized for environment: {settings.SENTRY_ENVIRONMENT}")


def filter_events(event, hint):
    """Filter events to reduce noise and costs."""
    
    # Skip health check errors
    if event.get('request', {}).get('url', '').endswith('/health'):
        return None
    
    # Skip common client errors to reduce noise
    if event.get('exception', {}).get('values'):
        for exc in event['exception']['values']:
            exc_type = exc.get('type', '')
            if exc_type in ['ValidationError', 'HTTPException']:
                # Only log server errors (5xx), skip client errors (4xx)
                return None
    
    # Rate limit certain error types
    error_message = event.get('message', '')
    if 'timeout' in error_message.lower():
        # Sample timeout errors to reduce volume
        import random
        if random.random() > 0.1:  # Only capture 10% of timeout errors
            return None
    
    return event


def filter_transactions(event, hint):
    """Filter transactions to reduce performance monitoring costs."""
    
    # Skip health check transactions
    transaction_name = event.get('transaction', '')
    if '/health' in transaction_name:
        return None
    
    # Skip static file requests
    if any(ext in transaction_name for ext in ['.css', '.js', '.png', '.jpg', '.ico']):
        return None
    
    # Sample long-running transactions less frequently
    duration = event.get('timestamp', 0) - event.get('start_timestamp', 0)
    if duration > 10:  # Transactions longer than 10 seconds
        import random
        if random.random() > 0.05:  # Only capture 5% of slow transactions
            return None
    
    return event


def capture_message(message: str, level: str = "info", **kwargs):
    """Capture a message with cost-aware sampling."""
    if settings.SENTRY_DSN:
        sentry_sdk.capture_message(message, level=level, **kwargs)


def capture_exception(exception: Exception = None, **kwargs):
    """Capture an exception with additional context."""
    if settings.SENTRY_DSN:
        sentry_sdk.capture_exception(exception, **kwargs)


def set_user_context(user_id: str, email: str = None, **kwargs):
    """Set user context for error tracking."""
    if settings.SENTRY_DSN:
        sentry_sdk.set_user({
            "id": user_id,
            "email": email,
            **kwargs
        })


def set_tag(key: str, value: str):
    """Set a tag for the current scope."""
    if settings.SENTRY_DSN:
        sentry_sdk.set_tag(key, value)


def set_context(name: str, context: dict):
    """Set context information."""
    if settings.SENTRY_DSN:
        sentry_sdk.set_context(name, context)


class SentryMiddleware:
    """FastAPI middleware for Sentry integration."""
    
    def __init__(self, app):
        self.app = app
    
    async def __call__(self, scope, receive, send):
        if scope["type"] == "http" and settings.SENTRY_DSN:
            # Set request context
            request_info = {
                "method": scope.get("method"),
                "path": scope.get("path"),
                "query_string": scope.get("query_string", b"").decode(),
            }
            set_context("request", request_info)
            
            # Set performance tags
            set_tag("request_method", scope.get("method", "unknown"))
            set_tag("cost_optimized", "true")
        
        await self.app(scope, receive, send)