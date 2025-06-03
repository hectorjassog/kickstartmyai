"""
End-to-End Test Configuration

Fixtures and utilities specific to E2E testing.
"""
import asyncio
import os
import subprocess
import time
from typing import AsyncGenerator, Dict, Any, Optional
import httpx
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

from app.core.config import get_settings
from app.db.base import Base


class E2ETestEnvironment:
    """Manages E2E test environment with real services."""
    
    def __init__(self):
        self.postgres_container: Optional[PostgresContainer] = None
        self.redis_container: Optional[RedisContainer] = None
        self.app_process: Optional[subprocess.Popen] = None
        self.base_url = "http://localhost:8001"
        
    async def start(self) -> Dict[str, Any]:
        """Start all required services for E2E testing."""
        # Start PostgreSQL container
        self.postgres_container = PostgresContainer("postgres:14")
        self.postgres_container.start()
        
        # Start Redis container
        self.redis_container = RedisContainer("redis:7")
        self.redis_container.start()
        
        # Set environment variables
        db_url = self.postgres_container.get_connection_url()
        redis_url = self.redis_container.get_connection_url()
        
        env = os.environ.copy()
        env.update({
            "DATABASE_URL": db_url,
            "REDIS_URL": redis_url,
            "ENVIRONMENT": "testing",
            "SECRET_KEY": "test-secret-key-for-e2e-testing",
            "JWT_SECRET_KEY": "test-jwt-secret-for-e2e",
            "OPENAI_API_KEY": "test-openai-key",
            "ANTHROPIC_API_KEY": "test-anthropic-key",
            "GOOGLE_API_KEY": "test-google-key",
        })
        
        # Run database migrations
        migration_cmd = [
            "python", "-m", "alembic", "upgrade", "head"
        ]
        subprocess.run(migration_cmd, env=env, check=True)
        
        # Start the FastAPI application
        self.app_process = subprocess.Popen(
            ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8001"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        # Wait for application to be ready
        await self._wait_for_app_ready()
        
        return {
            "base_url": self.base_url,
            "db_url": db_url,
            "redis_url": redis_url,
        }
    
    async def stop(self):
        """Stop all services."""
        if self.app_process:
            self.app_process.terminate()
            self.app_process.wait(timeout=10)
        
        if self.postgres_container:
            self.postgres_container.stop()
        
        if self.redis_container:
            self.redis_container.stop()
    
    async def _wait_for_app_ready(self, max_attempts: int = 30):
        """Wait for the application to be ready."""
        for attempt in range(max_attempts):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(f"{self.base_url}/health")
                    if response.status_code == 200:
                        return
            except httpx.ConnectError:
                pass
            
            await asyncio.sleep(1)
        
        raise RuntimeError("Application failed to start within timeout")


@pytest.fixture(scope="session")
async def e2e_environment() -> AsyncGenerator[Dict[str, Any], None]:
    """Provide E2E test environment."""
    env = E2ETestEnvironment()
    
    try:
        config = await env.start()
        yield config
    finally:
        await env.stop()


@pytest.fixture
async def e2e_client(e2e_environment: Dict[str, Any]) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide HTTP client for E2E testing."""
    async with httpx.AsyncClient(
        base_url=e2e_environment["base_url"],
        timeout=30.0
    ) as client:
        yield client


@pytest.fixture
async def authenticated_e2e_client(e2e_client: httpx.AsyncClient) -> AsyncGenerator[httpx.AsyncClient, None]:
    """Provide authenticated HTTP client for E2E testing."""
    # Register a test user
    user_data = {
        "email": "e2e-test@example.com",
        "password": "E2eTestPassword123!",
        "full_name": "E2E Test User"
    }
    
    register_response = await e2e_client.post("/api/v1/auth/register", json=user_data)
    assert register_response.status_code == 201
    
    # Login to get tokens
    login_data = {
        "username": user_data["email"],
        "password": user_data["password"]
    }
    
    login_response = await e2e_client.post("/api/v1/auth/login", data=login_data)
    assert login_response.status_code == 200
    
    tokens = login_response.json()
    access_token = tokens["access_token"]
    
    # Update client headers
    e2e_client.headers.update({
        "Authorization": f"Bearer {access_token}"
    })
    
    yield e2e_client


class E2ETestUser:
    """Helper class for E2E user management."""
    
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.email: Optional[str] = None
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_id: Optional[int] = None
    
    async def register(self, email: str, password: str, full_name: str) -> Dict[str, Any]:
        """Register a new user."""
        user_data = {
            "email": email,
            "password": password,
            "full_name": full_name
        }
        
        response = await self.client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 201
        
        user = response.json()
        self.email = email
        self.user_id = user["id"]
        
        return user
    
    async def login(self, password: str) -> Dict[str, Any]:
        """Login user and update client headers."""
        login_data = {
            "username": self.email,
            "password": password
        }
        
        response = await self.client.post("/api/v1/auth/login", data=login_data)
        assert response.status_code == 200
        
        tokens = response.json()
        self.access_token = tokens["access_token"]
        self.refresh_token = tokens["refresh_token"]
        
        # Update client headers
        self.client.headers.update({
            "Authorization": f"Bearer {self.access_token}"
        })
        
        return tokens
    
    async def logout(self):
        """Logout user and clear headers."""
        if self.access_token:
            await self.client.post("/api/v1/auth/logout")
            self.client.headers.pop("Authorization", None)
            self.access_token = None
            self.refresh_token = None


@pytest.fixture
async def e2e_user(e2e_client: httpx.AsyncClient) -> AsyncGenerator[E2ETestUser, None]:
    """Provide E2E test user helper."""
    user = E2ETestUser(e2e_client)
    yield user
    
    # Cleanup
    await user.logout()
