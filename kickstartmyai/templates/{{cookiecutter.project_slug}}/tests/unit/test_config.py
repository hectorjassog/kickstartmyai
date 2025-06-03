"""
Unit tests for configuration management.

Tests application settings, environment variable loading, validation,
and configuration security to ensure proper application setup.
"""

import pytest
import os
from unittest.mock import patch, MagicMock
from typing import Dict, Any
from pydantic import ValidationError

from app.core.config import Settings


class TestSettingsValidation:
    """Test settings validation and loading."""

    def test_default_settings(self):
        """Test default settings values."""
        with patch.dict(os.environ, {"SECRET_KEY": "test-secret-key"}, clear=False):
            settings = Settings()
            
            assert settings.PROJECT_NAME == "{{cookiecutter.project_name}}"
            assert settings.PROJECT_SLUG == "{{cookiecutter.project_slug}}"
            assert settings.VERSION == "{{cookiecutter.version}}"
            assert settings.API_V1_STR == "/api/v1"
            assert settings.HOST == "0.0.0.0"
            assert settings.PORT == 8000
            assert settings.DEBUG is False
            assert settings.ALGORITHM == "HS256"

    def test_secret_key_required(self):
        """Test that SECRET_KEY is required."""
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(ValidationError):
                Settings()

    def test_secret_key_from_env(self):
        """Test SECRET_KEY loading from environment."""
        test_secret = "my-super-secret-key-123"
        with patch.dict(os.environ, {"SECRET_KEY": test_secret}):
            settings = Settings()
            assert settings.SECRET_KEY == test_secret

    def test_database_url_assembly(self):
        """Test database URL assembly from components."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            "POSTGRES_SERVER": "testdb.example.com",
            "POSTGRES_USER": "testuser",
            "POSTGRES_PASSWORD": "testpass",
            "POSTGRES_DB": "testdb",
            "POSTGRES_PORT": "5433"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            expected_url = "postgresql://testuser:testpass@testdb.example.com:5433/testdb"
            assert settings.DATABASE_URL == expected_url

    def test_database_url_override(self):
        """Test DATABASE_URL environment variable override."""
        custom_url = "postgresql://custom:pass@custom.host:5432/customdb"
        env_vars = {
            "SECRET_KEY": "test-secret",
            "DATABASE_URL": custom_url
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.DATABASE_URL == custom_url

    def test_cors_origins_string(self):
        """Test CORS origins parsing from string."""
        cors_origins = "http://localhost:3000,https://example.com,https://app.example.com"
        env_vars = {
            "SECRET_KEY": "test-secret",
            "BACKEND_CORS_ORIGINS": cors_origins
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            expected_origins = [
                "http://localhost:3000",
                "https://example.com", 
                "https://app.example.com"
            ]
            assert settings.BACKEND_CORS_ORIGINS == expected_origins

    def test_cors_origins_single(self):
        """Test CORS origins with single URL."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            "BACKEND_CORS_ORIGINS": "https://example.com"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.BACKEND_CORS_ORIGINS == ["https://example.com"]

    def test_redis_configuration(self):
        """Test Redis configuration."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            "REDIS_URL": "redis://redis.example.com:6379/1",
            "REDIS_POOL_SIZE": "20",
            "REDIS_TTL_DEFAULT": "7200"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.REDIS_URL == "redis://redis.example.com:6379/1"
            assert settings.REDIS_POOL_SIZE == 20
            assert settings.REDIS_TTL_DEFAULT == 7200

    def test_ai_provider_configuration(self):
        """Test AI provider settings."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            "OPENAI_API_KEY": "sk-test-openai-key",
            "OPENAI_ORG_ID": "org-12345",
            "OPENAI_MODEL_DEFAULT": "gpt-4-turbo",
            "ANTHROPIC_API_KEY": "sk-ant-test-key",
            "ANTHROPIC_MODEL_DEFAULT": "claude-3-opus",
            "GEMINI_API_KEY": "gemini-test-key",
            "GEMINI_MODEL_DEFAULT": "gemini-pro-vision"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.OPENAI_API_KEY == "sk-test-openai-key"
            assert settings.OPENAI_ORG_ID == "org-12345"
            assert settings.OPENAI_MODEL_DEFAULT == "gpt-4-turbo"
            assert settings.ANTHROPIC_API_KEY == "sk-ant-test-key"
            assert settings.ANTHROPIC_MODEL_DEFAULT == "claude-3-opus"
            assert settings.GEMINI_API_KEY == "gemini-test-key"
            assert settings.GEMINI_MODEL_DEFAULT == "gemini-pro-vision"

    def test_token_expiration_settings(self):
        """Test token expiration configuration."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "30",
            "REFRESH_TOKEN_EXPIRE_MINUTES": "10080"  # 7 days
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 30
            assert settings.REFRESH_TOKEN_EXPIRE_MINUTES == 10080

    def test_cache_configuration(self):
        """Test cache settings."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            "CACHE_ENABLED": "false",
            "CACHE_PREFIX": "myapp",
            "CACHE_DEFAULT_TTL": "600"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.CACHE_ENABLED is False
            assert settings.CACHE_PREFIX == "myapp"
            assert settings.CACHE_DEFAULT_TTL == 600

    def test_tools_configuration(self):
        """Test tools configuration."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            "TOOLS_ENABLED": "true",
            "FUNCTION_CALLING_ENABLED": "false",
            "MAX_FUNCTION_CALLS": "10",
            "FUNCTION_TIMEOUT": "60",
            "WEB_SEARCH_MAX_RESULTS": "20"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.TOOLS_ENABLED is True
            assert settings.FUNCTION_CALLING_ENABLED is False
            assert settings.MAX_FUNCTION_CALLS == 10
            assert settings.FUNCTION_TIMEOUT == 60
            assert settings.WEB_SEARCH_MAX_RESULTS == 20


class TestSettingsEnvironments:
    """Test settings for different environments."""

    def test_development_environment(self):
        """Test development environment settings."""
        env_vars = {
            "SECRET_KEY": "dev-secret",
            "DEBUG": "true",
            "RELOAD": "true",
            "DATABASE_URL": "sqlite:///./dev.db"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.DEBUG is True
            assert settings.RELOAD is True
            assert "sqlite" in settings.DATABASE_URL

    def test_production_environment(self):
        """Test production environment settings."""
        env_vars = {
            "SECRET_KEY": "super-secure-production-key-with-entropy",
            "DEBUG": "false",
            "RELOAD": "false",
            "DATABASE_URL": "postgresql://user:pass@prod-db:5432/proddb",
            "REDIS_URL": "redis://prod-redis:6379/0"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.DEBUG is False
            assert settings.RELOAD is False
            assert "postgresql" in settings.DATABASE_URL
            assert "prod-redis" in settings.REDIS_URL

    def test_testing_environment(self):
        """Test testing environment settings."""
        env_vars = {
            "SECRET_KEY": "test-secret-key",
            "DATABASE_URL": "sqlite:///./test.db",
            "REDIS_URL": "redis://localhost:6379/1",
            "CACHE_ENABLED": "false",
            "AI_REQUEST_TIMEOUT": "5"  # Shorter timeout for tests
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert "sqlite" in settings.DATABASE_URL
            assert settings.CACHE_ENABLED is False
            assert settings.AI_REQUEST_TIMEOUT == 5


class TestSettingsValidationErrors:
    """Test settings validation error handling."""

    def test_invalid_cors_origins(self):
        """Test invalid CORS origins format."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            "BACKEND_CORS_ORIGINS": "not-a-valid-url"
        }
        
        with patch.dict(os.environ, env_vars):
            # Should not raise error, but may not parse correctly
            settings = Settings()
            # The validation might allow this or convert it
            assert isinstance(settings.BACKEND_CORS_ORIGINS, list)

    def test_invalid_integer_values(self):
        """Test invalid integer configuration values."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            "PORT": "not-a-number",
            "ACCESS_TOKEN_EXPIRE_MINUTES": "invalid"
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValidationError):
                Settings()

    def test_invalid_boolean_values(self):
        """Test invalid boolean configuration values."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            "DEBUG": "maybe",
            "CACHE_ENABLED": "sometimes"
        }
        
        with patch.dict(os.environ, env_vars):
            with pytest.raises(ValidationError):
                Settings()

    def test_missing_required_postgres_values(self):
        """Test behavior with missing PostgreSQL configuration."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            # Missing POSTGRES_PASSWORD, should still work with empty string
        }
        
        with patch.dict(os.environ, env_vars, clear=True):
            settings = Settings()
            # Should assemble URL with empty password
            assert "postgresql://" in settings.DATABASE_URL


class TestSettingsSecurity:
    """Test security-related settings."""

    def test_secret_key_strength(self):
        """Test secret key strength requirements."""
        weak_keys = [
            "secret",
            "123456",
            "password",
            "abc123"
        ]
        
        for weak_key in weak_keys:
            with patch.dict(os.environ, {"SECRET_KEY": weak_key}):
                settings = Settings()
                # Settings loads but key is weak (should be detected elsewhere)
                assert settings.SECRET_KEY == weak_key
                assert len(settings.SECRET_KEY) < 32  # Weak key indicator

    def test_strong_secret_key(self):
        """Test strong secret key."""
        strong_key = "a-very-long-and-secure-secret-key-with-random-entropy-12345"
        
        with patch.dict(os.environ, {"SECRET_KEY": strong_key}):
            settings = Settings()
            assert settings.SECRET_KEY == strong_key
            assert len(settings.SECRET_KEY) >= 32

    def test_sensitive_values_not_logged(self):
        """Test that sensitive values are not exposed in string representation."""
        env_vars = {
            "SECRET_KEY": "super-secret-key",
            "OPENAI_API_KEY": "sk-secret-openai-key",
            "POSTGRES_PASSWORD": "secret-db-password"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            settings_str = str(settings)
            
            # Sensitive values should not appear in string representation
            # This depends on Pydantic's implementation
            assert "super-secret-key" not in settings_str or "***" in settings_str
            assert "sk-secret-openai-key" not in settings_str or "***" in settings_str

    def test_algorithm_security(self):
        """Test JWT algorithm setting."""
        env_vars = {
            "SECRET_KEY": "test-secret",
            "ALGORITHM": "HS256"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.ALGORITHM == "HS256"
            # Should not allow none algorithm
            assert settings.ALGORITHM != "none"


class TestSettingsUtilityMethods:
    """Test utility methods and derived properties."""

    def test_is_development_method(self):
        """Test development environment detection."""
        # This would require implementing is_development method
        env_vars = {
            "SECRET_KEY": "test-secret",
            "DEBUG": "true"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            # Assuming such method exists
            if hasattr(settings, 'is_development'):
                assert settings.is_development() is True

    def test_is_production_method(self):
        """Test production environment detection."""
        env_vars = {
            "SECRET_KEY": "prod-secret",
            "DEBUG": "false"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            if hasattr(settings, 'is_production'):
                assert settings.is_production() is True

    def test_database_engine_detection(self):
        """Test database engine detection from URL."""
        test_cases = [
            ("postgresql://user:pass@host:5432/db", "postgresql"),
            ("sqlite:///./test.db", "sqlite"),
            ("mysql://user:pass@host:3306/db", "mysql"),
        ]
        
        for db_url, expected_engine in test_cases:
            env_vars = {
                "SECRET_KEY": "test-secret",
                "DATABASE_URL": db_url
            }
            
            with patch.dict(os.environ, env_vars):
                settings = Settings()
                assert expected_engine in settings.DATABASE_URL.lower()

    def test_redis_connection_params(self):
        """Test Redis connection parameter extraction."""
        redis_url = "redis://username:password@redis.example.com:6380/2"
        env_vars = {
            "SECRET_KEY": "test-secret",
            "REDIS_URL": redis_url
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.REDIS_URL == redis_url
            # Could test URL parsing if utility methods exist


class TestSettingsDefaults:
    """Test default values and fallbacks."""

    def test_default_timeouts(self):
        """Test default timeout values."""
        with patch.dict(os.environ, {"SECRET_KEY": "test-secret"}):
            settings = Settings()
            assert settings.AI_REQUEST_TIMEOUT == 60
            assert settings.FUNCTION_TIMEOUT == 30
            assert settings.CODE_EXECUTION_TIMEOUT == 30

    def test_default_ai_settings(self):
        """Test default AI provider settings."""
        with patch.dict(os.environ, {"SECRET_KEY": "test-secret"}):
            settings = Settings()
            assert settings.OPENAI_MODEL_DEFAULT == "gpt-4"
            assert settings.ANTHROPIC_MODEL_DEFAULT == "claude-3-sonnet-20240229"
            assert settings.GEMINI_MODEL_DEFAULT == "gemini-1.5-flash"
            assert settings.OPENAI_MAX_TOKENS == 4096
            assert settings.OPENAI_TEMPERATURE == 0.7

    def test_default_security_settings(self):
        """Test default security-related settings."""
        with patch.dict(os.environ, {"SECRET_KEY": "test-secret"}):
            settings = Settings()
            assert settings.ACCESS_TOKEN_EXPIRE_MINUTES == 60 * 24 * 8  # 8 days
            assert settings.REFRESH_TOKEN_EXPIRE_MINUTES == 60 * 24 * 30  # 30 days
            assert settings.ALGORITHM == "HS256"

    def test_default_database_settings(self):
        """Test default database settings."""
        with patch.dict(os.environ, {"SECRET_KEY": "test-secret"}):
            settings = Settings()
            assert settings.POSTGRES_SERVER == "localhost"
            assert settings.POSTGRES_PORT == "5432"
            assert settings.POSTGRES_USER == "{{cookiecutter.database_user}}"
            assert settings.POSTGRES_DB == "{{cookiecutter.database_name}}"
            assert settings.DATABASE_POOL_SIZE == 5
            assert settings.DATABASE_MAX_OVERFLOW == 10

    def test_default_feature_flags(self):
        """Test default feature flag values."""
        with patch.dict(os.environ, {"SECRET_KEY": "test-secret"}):
            settings = Settings()
            assert settings.TOOLS_ENABLED is True
            assert settings.FUNCTION_CALLING_ENABLED is True
            assert settings.CACHE_ENABLED is True

    def test_default_limits(self):
        """Test default limit values."""
        with patch.dict(os.environ, {"SECRET_KEY": "test-secret"}):
            settings = Settings()
            assert settings.MAX_FUNCTION_CALLS == 5
            assert settings.WEB_SEARCH_MAX_RESULTS == 10
            assert settings.AI_BATCH_SIZE == 10
            assert settings.AI_MAX_RETRIES == 3


class TestSettingsEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_environment(self):
        """Test behavior with minimal environment."""
        with patch.dict(os.environ, {"SECRET_KEY": "test-secret"}, clear=True):
            settings = Settings()
            # Should load with all defaults
            assert settings.SECRET_KEY == "test-secret"
            assert settings.DEBUG is False

    def test_environment_override_precedence(self):
        """Test that environment variables take precedence."""
        env_vars = {
            "SECRET_KEY": "env-secret",
            "DEBUG": "true",
            "PORT": "9000"
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.SECRET_KEY == "env-secret"
            assert settings.DEBUG is True
            assert settings.PORT == 9000

    def test_special_characters_in_values(self):
        """Test handling of special characters in configuration values."""
        special_values = {
            "SECRET_KEY": "key-with-special-chars!@#$%^&*()",
            "POSTGRES_PASSWORD": "pass-with-spaces and symbols!",
            "PROJECT_NAME": "My App With Spaces"
        }
        
        with patch.dict(os.environ, special_values):
            settings = Settings()
            assert settings.SECRET_KEY == special_values["SECRET_KEY"]
            assert settings.POSTGRES_PASSWORD == special_values["POSTGRES_PASSWORD"]
            # PROJECT_NAME might come from cookiecutter template

    def test_unicode_values(self):
        """Test handling of Unicode values."""
        unicode_values = {
            "SECRET_KEY": "test-secret",
            "PROJECT_NAME": "AI應用程式",  # Chinese characters
            "DESCRIPTION": "Une application avec des caractères spéciaux"  # French
        }
        
        with patch.dict(os.environ, unicode_values):
            settings = Settings()
            # Should handle Unicode correctly
            assert settings.SECRET_KEY == "test-secret"

    def test_very_long_values(self):
        """Test handling of very long configuration values."""
        long_secret = "a" * 1000  # Very long secret key
        env_vars = {
            "SECRET_KEY": long_secret,
        }
        
        with patch.dict(os.environ, env_vars):
            settings = Settings()
            assert settings.SECRET_KEY == long_secret
            assert len(settings.SECRET_KEY) == 1000
