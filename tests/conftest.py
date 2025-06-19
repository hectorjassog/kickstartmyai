"""Pytest configuration and fixtures."""

import tempfile
import shutil
from pathlib import Path
import pytest


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = Path(tempfile.mkdtemp())
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture
def sample_cookiecutter_context():
    """Sample context for cookiecutter template."""
    return {
        "project_name": "Test AI Project",
        "project_slug": "test-ai-project",
        "project_description": "A test AI project",
        "author_name": "Test Author",
        "author_email": "test@example.com",
        "version": "0.1.0",
        "database_type": "postgresql",
        "database_name": "test_db",
        "database_user": "test_user",
        "include_redis": "y",
        "include_monitoring": "y",
        "include_terraform": "y",
        "aws_region": "us-east-1",
        "environment": "development"
    }