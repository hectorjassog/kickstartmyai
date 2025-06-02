"""
Pytest configuration and shared fixtures.

This module provides common test fixtures and configuration
for the entire test suite.
"""

import asyncio
import os
import pytest
import pytest_asyncio
from typing import AsyncGenerator, Generator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.config import settings
from app.db.base import Base
from app.db.session import get_db
from app.models.user import User
from app.core.security.password import get_password_hash


# Test database URL
TEST_DATABASE_URL = "sqlite+aiosqlite:///./test.db"

# Create test engine
test_engine = create_async_engine(
    TEST_DATABASE_URL,
    poolclass=StaticPool,
    connect_args={"check_same_thread": False},
    echo=False
)

# Test session maker
TestingSessionLocal = sessionmaker(
    test_engine,
    class_=AsyncSession,
    expire_on_commit=False
)


@pytest_asyncio.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="function")
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Create a fresh database session for each test."""
    # Create all tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture(scope="function")
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client with database override."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://test") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def test_user(db_session: AsyncSession) -> User:
    """Create a test user."""
    from app.crud.user import user_crud
    from app.schemas.user import UserCreate
    
    user_data = UserCreate(
        email="test@example.com",
        password="testpassword123",
        full_name="Test User"
    )
    
    return await user_crud.create(db_session, obj_in=user_data)


@pytest_asyncio.fixture
async def admin_user(db_session: AsyncSession) -> User:
    """Create an admin user."""
    from app.crud.user import user_crud
    from app.schemas.user import UserCreate
    
    user_data = UserCreate(
        email="admin@example.com",
        password="adminpassword123",
        full_name="Admin User"
    )
    
    user = await user_crud.create(db_session, obj_in=user_data)
    user.is_superuser = True
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    
    return user


@pytest_asyncio.fixture
async def auth_headers(test_user: User) -> dict:
    """Create authentication headers for test user."""
    from app.core.security.jwt_handler import create_access_token
    
    access_token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest_asyncio.fixture
async def admin_headers(admin_user: User) -> dict:
    """Create authentication headers for admin user."""
    from app.core.security.jwt_handler import create_access_token
    
    access_token = create_access_token(data={"sub": str(admin_user.id)})
    return {"Authorization": f"Bearer {access_token}"}


@pytest.fixture
def mock_openai_api():
    """Mock OpenAI API responses."""
    import respx
    import httpx
    
    def mock_chat_completion():
        return httpx.Response(
            200,
            json={
                "id": "chatcmpl-123",
                "object": "chat.completion",
                "created": 1677652288,
                "model": "gpt-4",
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "Hello! This is a test response."
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": 10,
                    "completion_tokens": 15,
                    "total_tokens": 25
                }
            }
        )
    
    with respx.mock() as respx_mock:
        respx_mock.post("https://api.openai.com/v1/chat/completions").mock(
            return_value=mock_chat_completion()
        )
        yield respx_mock


@pytest.fixture
def mock_anthropic_api():
    """Mock Anthropic API responses."""
    import respx
    import httpx
    
    def mock_message_response():
        return httpx.Response(
            200,
            json={
                "id": "msg_123",
                "type": "message",
                "role": "assistant",
                "content": [{
                    "type": "text",
                    "text": "Hello! This is a test response from Claude."
                }],
                "model": "claude-3-sonnet-20240229",
                "stop_reason": "end_turn",
                "stop_sequence": None,
                "usage": {
                    "input_tokens": 10,
                    "output_tokens": 15
                }
            }
        )
    
    with respx.mock() as respx_mock:
        respx_mock.post("https://api.anthropic.com/v1/messages").mock(
            return_value=mock_message_response()
        )
        yield respx_mock


@pytest.fixture
def mock_gemini_api():
    """Mock Google Gemini API responses."""
    import respx
    import httpx
    
    def mock_generate_response():
        return httpx.Response(
            200,
            json={
                "candidates": [{
                    "content": {
                        "parts": [{
                            "text": "Hello! This is a test response from Gemini."
                        }],
                        "role": "model"
                    },
                    "finishReason": "STOP",
                    "index": 0
                }],
                "usageMetadata": {
                    "promptTokenCount": 10,
                    "candidatesTokenCount": 15,
                    "totalTokenCount": 25
                }
            }
        )
    
    with respx.mock() as respx_mock:
        respx_mock.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent").mock(
            return_value=mock_generate_response()
        )
        yield respx_mock


# Environment setup for tests
@pytest.fixture(autouse=True)
def setup_test_env():
    """Set up test environment variables."""
    os.environ.update({
        "ENVIRONMENT": "testing",
        "DATABASE_URL": TEST_DATABASE_URL,
        "SECRET_KEY": "test-secret-key-for-testing-only",
        "OPENAI_API_KEY": "test-openai-key",
        "ANTHROPIC_API_KEY": "test-anthropic-key",
        "GEMINI_API_KEY": "test-gemini-key",
        "TOOLS_ENABLED": "true",
    })
    yield
    # Cleanup is handled automatically 