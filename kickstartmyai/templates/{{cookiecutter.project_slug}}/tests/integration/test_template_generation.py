"""
Template Generation Integration Tests

These tests validate that the cookiecutter template generates correctly
and the resulting project is functional without errors.
"""

import pytest
import tempfile
import subprocess
import os
import json
from pathlib import Path
from typing import Dict, Any


class TestTemplateGeneration:
    """Test cookiecutter template generation."""
    
    @pytest.fixture
    def temp_dir(self):
        """Create temporary directory for template generation."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir)
    
    @pytest.fixture
    def template_config(self) -> Dict[str, Any]:
        """Default template configuration."""
        return {
            "project_name": "Test AI Project",
            "project_slug": "test_ai_project",
            "description": "A test AI project generated from template",
            "author": "Test Author",
            "email": "test@example.com",
            "version": "0.1.0",
            "python_version": "3.11",
            "use_postgres": "y",
            "use_redis": "y",
            "use_docker": "y",
            "use_terraform": "y",
            "ai_providers": "openai,anthropic,gemini",
            "include_tools": "y"
        }
    
    def test_template_generates_successfully(self, temp_dir: Path, template_config: Dict[str, Any]):
        """Test that template generates without errors."""
        # Write cookiecutter config
        config_file = temp_dir / "cookiecutter.json"
        with open(config_file, 'w') as f:
            json.dump(template_config, f)
        
        # Get template path (relative to this test file)
        template_path = Path(__file__).parent.parent.parent / "templates"
        
        # Generate template
        result = subprocess.run([
            "cookiecutter",
            str(template_path),
            "--no-input",
            "--config-file", str(config_file),
            "--output-dir", str(temp_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Template generation failed: {result.stderr}"
        
        # Verify project directory was created
        project_dir = temp_dir / template_config["project_slug"]
        assert project_dir.exists(), "Project directory was not created"
        assert project_dir.is_dir(), "Project path is not a directory"
    
    def test_all_expected_files_created(self, temp_dir: Path, template_config: Dict[str, Any]):
        """Test that all expected files are created."""
        # Generate template
        self.test_template_generates_successfully(temp_dir, template_config)
        
        project_dir = temp_dir / template_config["project_slug"]
        
        # Expected files and directories
        expected_paths = [
            # Root files
            "README.md",
            "pyproject.toml",
            "requirements.txt",
            "Makefile",
            ".env.example",
            ".gitignore",
            "pytest.ini",
            
            # Application structure
            "app/__init__.py",
            "app/main.py",
            "app/core/config.py",
            "app/db/base.py",
            "app/models/user.py",
            "app/models/agent.py",
            "app/api/v1/api.py",
            "app/crud/user.py",
            "app/schemas/user.py",
            
            # AI components
            "app/ai/providers/__init__.py",
            "app/ai/providers/openai.py",
            "app/ai/providers/anthropic.py",
            "app/ai/providers/gemini.py",
            "app/ai/tools/__init__.py",
            "app/ai/tools/base.py",
            "app/ai/tools/manager.py",
            "app/ai/tools/builtin.py",
            
            # Tests
            "tests/__init__.py",
            "tests/conftest.py",
            "tests/unit/__init__.py",
            "tests/integration/__init__.py",
            
            # Database
            "alembic.ini",
            "alembic/env.py",
            "scripts/database/init_db.py",
            
            # Docker
            "Dockerfile",
            "docker-compose.yml",
            "docker-compose.prod.yml",
            
            # Terraform
            "terraform/main.tf",
            "terraform/variables.tf",
        ]
        
        for path_str in expected_paths:
            file_path = project_dir / path_str
            assert file_path.exists(), f"Expected file/directory not found: {path_str}"
    
    def test_variable_substitution(self, temp_dir: Path):
        """Test that template variables are correctly substituted."""
        config = {
            "project_name": "My Custom AI App",
            "project_slug": "my_custom_ai_app",
            "description": "Custom description for testing",
            "author": "Custom Author",
            "email": "custom@test.com",
            "version": "1.2.3"
        }
        
        # Generate template with custom config
        config_file = temp_dir / "cookiecutter.json"
        with open(config_file, 'w') as f:
            json.dump(config, f)
        
        template_path = Path(__file__).parent.parent.parent / "templates"
        
        result = subprocess.run([
            "cookiecutter",
            str(template_path),
            "--no-input",
            "--config-file", str(config_file),
            "--output-dir", str(temp_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0
        
        project_dir = temp_dir / config["project_slug"]
        
        # Check README.md for variable substitution
        readme_path = project_dir / "README.md"
        readme_content = readme_path.read_text()
        
        assert config["project_name"] in readme_content
        assert config["description"] in readme_content
        
        # Check pyproject.toml for variable substitution
        pyproject_path = project_dir / "pyproject.toml"
        pyproject_content = pyproject_path.read_text()
        
        assert config["project_name"] in pyproject_content
        assert config["version"] in pyproject_content
        assert config["author"] in pyproject_content
        assert config["email"] in pyproject_content
    
    def test_python_syntax_validation(self, temp_dir: Path, template_config: Dict[str, Any]):
        """Test that all generated Python files have valid syntax."""
        # Generate template
        self.test_template_generates_successfully(temp_dir, template_config)
        
        project_dir = temp_dir / template_config["project_slug"]
        
        # Find all Python files
        python_files = list(project_dir.rglob("*.py"))
        
        assert len(python_files) > 0, "No Python files found in generated project"
        
        # Validate syntax of each Python file
        for py_file in python_files:
            result = subprocess.run([
                "python", "-m", "py_compile", str(py_file)
            ], capture_output=True, text=True)
            
            assert result.returncode == 0, f"Syntax error in {py_file}: {result.stderr}"
    
    def test_dependencies_installation(self, temp_dir: Path, template_config: Dict[str, Any]):
        """Test that dependencies can be installed without conflicts."""
        # Generate template
        self.test_template_generates_successfully(temp_dir, template_config)
        
        project_dir = temp_dir / template_config["project_slug"]
        
        # Check that requirements.txt exists and is valid
        requirements_path = project_dir / "requirements.txt"
        assert requirements_path.exists()
        
        requirements_content = requirements_path.read_text()
        assert len(requirements_content.strip()) > 0, "requirements.txt is empty"
        
        # Validate requirement format (basic check)
        lines = [line.strip() for line in requirements_content.split('\n') if line.strip()]
        for line in lines:
            if not line.startswith('#'):  # Skip comments
                # Basic validation that each line looks like a requirement
                assert any(char in line for char in ['>=', '==', '~=', '>', '<']), \
                    f"Invalid requirement format: {line}"
    
    def test_database_configuration(self, temp_dir: Path, template_config: Dict[str, Any]):
        """Test database configuration files."""
        # Generate template
        self.test_template_generates_successfully(temp_dir, template_config)
        
        project_dir = temp_dir / template_config["project_slug"]
        
        # Check alembic configuration
        alembic_ini = project_dir / "alembic.ini"
        assert alembic_ini.exists()
        
        alembic_content = alembic_ini.read_text()
        assert "sqlalchemy.url" in alembic_content
        
        # Check alembic env.py
        alembic_env = project_dir / "alembic" / "env.py"
        assert alembic_env.exists()
        
        env_content = alembic_env.read_text()
        assert "target_metadata" in env_content
        assert "Base.metadata" in env_content
    
    def test_docker_configuration(self, temp_dir: Path, template_config: Dict[str, Any]):
        """Test Docker configuration files."""
        # Generate template
        self.test_template_generates_successfully(temp_dir, template_config)
        
        project_dir = temp_dir / template_config["project_slug"]
        
        # Check Dockerfile
        dockerfile = project_dir / "Dockerfile"
        assert dockerfile.exists()
        
        dockerfile_content = dockerfile.read_text()
        assert "FROM python:" in dockerfile_content
        assert "COPY requirements.txt" in dockerfile_content
        
        # Check docker-compose files
        compose_file = project_dir / "docker-compose.yml"
        assert compose_file.exists()
        
        compose_content = compose_file.read_text()
        assert "services:" in compose_content
        assert "postgres:" in compose_content or "postgresql:" in compose_content
        assert "redis:" in compose_content
    
    def test_ai_provider_configuration(self, temp_dir: Path, template_config: Dict[str, Any]):
        """Test AI provider configuration."""
        # Generate template
        self.test_template_generates_successfully(temp_dir, template_config)
        
        project_dir = temp_dir / template_config["project_slug"]
        
        # Check AI provider files
        openai_provider = project_dir / "app" / "ai" / "providers" / "openai.py"
        assert openai_provider.exists()
        
        anthropic_provider = project_dir / "app" / "ai" / "providers" / "anthropic.py"
        assert anthropic_provider.exists()
        
        gemini_provider = project_dir / "app" / "ai" / "providers" / "gemini.py"
        assert gemini_provider.exists()
        
        # Check that providers are properly configured
        openai_content = openai_provider.read_text()
        assert "OpenAIProvider" in openai_content
        assert "chat_completion" in openai_content
        
        # Check tool framework
        tools_base = project_dir / "app" / "ai" / "tools" / "base.py"
        assert tools_base.exists()
        
        tools_content = tools_base.read_text()
        assert "BaseTool" in tools_content
        assert "ToolRegistry" in tools_content
    
    def test_environment_file(self, temp_dir: Path, template_config: Dict[str, Any]):
        """Test environment configuration file."""
        # Generate template
        self.test_template_generates_successfully(temp_dir, template_config)
        
        project_dir = temp_dir / template_config["project_slug"]
        
        # Check .env.example
        env_example = project_dir / ".env.example"
        assert env_example.exists()
        
        env_content = env_example.read_text()
        
        # Check for essential environment variables
        essential_vars = [
            "SECRET_KEY",
            "DATABASE_URL",
            "REDIS_URL",
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "GEMINI_API_KEY",
            "ENVIRONMENT"
        ]
        
        for var in essential_vars:
            assert var in env_content, f"Essential environment variable {var} not found"
    
    @pytest.mark.slow
    def test_project_startup(self, temp_dir: Path, template_config: Dict[str, Any]):
        """Test that the generated project can start up (basic check)."""
        # Generate template
        self.test_template_generates_successfully(temp_dir, template_config)
        
        project_dir = temp_dir / template_config["project_slug"]
        
        # Create a minimal .env file for testing
        env_file = project_dir / ".env"
        env_content = """
SECRET_KEY=test-secret-key-for-testing-only
DATABASE_URL=sqlite:///./test.db
REDIS_URL=redis://localhost:6379/0
OPENAI_API_KEY=test-key
ANTHROPIC_API_KEY=test-key
GEMINI_API_KEY=test-key
ENVIRONMENT=testing
        """
        env_file.write_text(env_content.strip())
        
        # Test that we can import the main module without errors
        test_script = project_dir / "test_import.py"
        test_script.write_text("""
import sys
sys.path.insert(0, '.')

try:
    from app.main import app
    from app.core.config import settings
    from app.ai.providers.factory import get_ai_provider
    from app.ai.tools.registry import tool_registry
    print("SUCCESS: All imports successful")
except Exception as e:
    print(f"ERROR: Import failed - {e}")
    sys.exit(1)
        """)
        
        # Run the import test
        result = subprocess.run([
            "python", str(test_script)
        ], cwd=project_dir, capture_output=True, text=True)
        
        # Clean up test script
        test_script.unlink()
        
        assert "SUCCESS" in result.stdout, f"Import test failed: {result.stderr}"
    
    def test_makefile_targets(self, temp_dir: Path, template_config: Dict[str, Any]):
        """Test that Makefile targets are properly configured."""
        # Generate template
        self.test_template_generates_successfully(temp_dir, template_config)
        
        project_dir = temp_dir / template_config["project_slug"]
        
        # Check Makefile
        makefile = project_dir / "Makefile"
        assert makefile.exists()
        
        makefile_content = makefile.read_text()
        
        # Check for essential targets
        essential_targets = [
            "install",
            "dev",
            "test",
            "lint",
            "format",
            "db-init",
            "db-migrate",
            "docker-build",
            "docker-up"
        ]
        
        for target in essential_targets:
            assert f"{target}:" in makefile_content, f"Makefile target {target} not found"


class TestSpecialCharacters:
    """Test template generation with special characters and edge cases."""
    
    def test_project_name_with_spaces(self, temp_dir: Path):
        """Test project name with spaces."""
        config = {
            "project_name": "My AI Project With Spaces",
            "project_slug": "my_ai_project_with_spaces"
        }
        
        self._test_generation_with_config(temp_dir, config)
    
    def test_project_name_with_unicode(self, temp_dir: Path):
        """Test project name with unicode characters."""
        config = {
            "project_name": "AI Project ñáéíóú",
            "project_slug": "ai_project_unicode"
        }
        
        self._test_generation_with_config(temp_dir, config)
    
    def test_special_email_formats(self, temp_dir: Path):
        """Test various email formats."""
        emails = [
            "test@example.com",
            "test.user@example.co.uk",
            "test+tag@example.org"
        ]
        
        for email in emails:
            config = {
                "project_name": "Test Project",
                "project_slug": "test_project",
                "email": email
            }
            self._test_generation_with_config(temp_dir, config)
    
    def _test_generation_with_config(self, temp_dir: Path, config: Dict[str, Any]):
        """Helper method to test generation with custom config."""
        config_file = temp_dir / "test_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f)
        
        template_path = Path(__file__).parent.parent.parent / "templates"
        
        result = subprocess.run([
            "cookiecutter",
            str(template_path),
            "--no-input",
            "--config-file", str(config_file),
            "--output-dir", str(temp_dir)
        ], capture_output=True, text=True)
        
        assert result.returncode == 0, f"Template generation failed with config {config}: {result.stderr}" 