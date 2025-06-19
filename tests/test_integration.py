"""Integration tests for KickStartMyAI."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch

from kickstartmyai.core.generator import ProjectGenerator


class TestIntegration:
    """Integration tests for the complete flow."""

    @pytest.fixture
    def temp_output_dir(self):
        """Create temporary output directory."""
        temp_dir = Path(tempfile.mkdtemp())
        yield temp_dir
        shutil.rmtree(temp_dir, ignore_errors=True)

    @pytest.fixture
    def minimal_context(self):
        """Minimal valid context for testing."""
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

    def test_template_structure_exists(self):
        """Test that template structure exists."""
        generator = ProjectGenerator()
        template_dir = generator.template_dir
        
        # Check main template files exist
        assert (template_dir / "cookiecutter.json").exists()
        assert (template_dir / "{{cookiecutter.project_slug}}").exists()
        
        # Check key template directories exist
        project_template = template_dir / "{{cookiecutter.project_slug}}"
        assert (project_template / "app").exists()
        assert (project_template / "tests").exists()
        assert (project_template / "docker").exists()
        assert (project_template / "terraform").exists()

    def test_cookiecutter_json_valid(self):
        """Test that cookiecutter.json is valid."""
        generator = ProjectGenerator()
        context = generator.get_context()
        
        # Check required fields exist
        required_fields = [
            "project_name",
            "project_slug", 
            "author_name",
            "author_email",
            "database_type",
            "aws_region"
        ]
        
        for field in required_fields:
            assert field in context, f"Required field '{field}' missing from cookiecutter.json"

    def test_template_renders_without_errors(self, temp_output_dir, minimal_context):
        """Test that template renders without Jinja2 errors."""
        generator = ProjectGenerator()
        
        # This should not raise any Jinja2 template errors
        try:
            result_path = generator.generate_project(
                output_dir=str(temp_output_dir),
                context=minimal_context
            )
            assert Path(result_path).exists()
        except Exception as e:
            pytest.fail(f"Template rendering failed: {e}")

    def test_generated_project_structure(self, temp_output_dir, minimal_context):
        """Test that generated project has correct structure."""
        generator = ProjectGenerator()
        result_path = generator.generate_project(
            output_dir=str(temp_output_dir),
            context=minimal_context
        )
        
        project_dir = Path(result_path)
        
        # Check main directories exist
        assert (project_dir / "app").exists()
        assert (project_dir / "tests").exists()
        assert (project_dir / "docker").exists()
        assert (project_dir / "terraform").exists()
        assert (project_dir / "scripts").exists()
        
        # Check main files exist
        assert (project_dir / "README.md").exists()
        assert (project_dir / "Dockerfile").exists()
        assert (project_dir / "docker-compose.yml").exists()
        assert (project_dir / "Makefile").exists()
        assert (project_dir / "pyproject.toml").exists()
        assert (project_dir / "requirements.txt").exists()

    def test_generated_project_ai_structure(self, temp_output_dir, minimal_context):
        """Test that generated project has correct AI structure."""
        generator = ProjectGenerator()
        result_path = generator.generate_project(
            output_dir=str(temp_output_dir),
            context=minimal_context
        )
        
        project_dir = Path(result_path)
        app_dir = project_dir / "app"
        
        # Check AI-specific directories
        assert (app_dir / "ai").exists()
        assert (app_dir / "ai" / "providers").exists()
        assert (app_dir / "ai" / "services").exists()
        assert (app_dir / "ai" / "tools").exists()
        assert (app_dir / "ai" / "core").exists()
        
        # Check AI service files
        ai_services = app_dir / "ai" / "services"
        assert (ai_services / "execution_engine.py").exists()
        assert (ai_services / "chat_service.py").exists()
        assert (ai_services / "llm_service.py").exists()

    def test_generated_project_configuration_files(self, temp_output_dir, minimal_context):
        """Test that configuration files are properly generated."""
        generator = ProjectGenerator()
        result_path = generator.generate_project(
            output_dir=str(temp_output_dir),
            context=minimal_context
        )
        
        project_dir = Path(result_path)
        
        # Check configuration files contain expected values
        readme_content = (project_dir / "README.md").read_text()
        assert minimal_context["project_name"] in readme_content
        assert minimal_context["project_description"] in readme_content
        
        pyproject_content = (project_dir / "pyproject.toml").read_text()
        assert minimal_context["project_slug"] in pyproject_content
        assert minimal_context["author_name"] in pyproject_content

    def test_generated_project_no_template_artifacts(self, temp_output_dir, minimal_context):
        """Test that generated project has no template artifacts."""
        generator = ProjectGenerator()
        result_path = generator.generate_project(
            output_dir=str(temp_output_dir),
            context=minimal_context
        )
        
        project_dir = Path(result_path)
        
        # Check that no files contain unreplaced Jinja2 syntax
        for file_path in project_dir.rglob("*.py"):
            if file_path.is_file():
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                assert "{{" not in content, f"Unreplaced Jinja2 syntax in {file_path}"
                assert "{%" not in content, f"Unreplaced Jinja2 syntax in {file_path}"
        
        # Check configuration files too
        for file_path in project_dir.rglob("*.yml"):
            if file_path.is_file():
                content = file_path.read_text(encoding='utf-8', errors='ignore')
                assert "{{" not in content, f"Unreplaced Jinja2 syntax in {file_path}"
                assert "{%" not in content, f"Unreplaced Jinja2 syntax in {file_path}"

    def test_template_with_different_database_types(self, temp_output_dir):
        """Test template with different database configurations."""
        generator = ProjectGenerator()
        
        # Test with PostgreSQL
        context_postgres = {
            "project_name": "Test Postgres Project",
            "project_slug": "test-postgres-project",
            "project_description": "Test project",
            "author_name": "Test Author",
            "author_email": "test@example.com",
            "database_type": "postgresql",
            "database_name": "test_db",
            "database_user": "test_user",
            "include_redis": "y",
            "include_monitoring": "y",
            "include_terraform": "y",
            "aws_region": "us-east-1",
            "environment": "development"
        }
        
        result_postgres = generator.generate_project(
            output_dir=str(temp_output_dir / "postgres"),
            context=context_postgres
        )
        
        # Test with MySQL
        context_mysql = context_postgres.copy()
        context_mysql.update({
            "project_slug": "test-mysql-project",
            "database_type": "mysql"
        })
        
        result_mysql = generator.generate_project(
            output_dir=str(temp_output_dir / "mysql"),
            context=context_mysql
        )
        
        # Both should generate successfully
        assert Path(result_postgres).exists()
        assert Path(result_mysql).exists()

    def test_template_validation_comprehensive(self):
        """Test comprehensive template validation."""
        generator = ProjectGenerator()
        
        # Test various validation scenarios
        valid_contexts = [
            {
                "project_name": "Valid Project",
                "project_slug": "valid-project",
                "author_email": "valid@example.com",
                "aws_region": "us-east-1"
            },
            {
                "project_name": "Another Valid Project",
                "project_slug": "another-valid-project", 
                "author_email": "another@example.com",
                "aws_region": "eu-west-1"
            }
        ]
        
        for context in valid_contexts:
            # Should not raise any exceptions
            generator.validate_context(context)

    def test_error_handling_in_generation(self, temp_output_dir, minimal_context):
        """Test error handling during project generation."""
        generator = ProjectGenerator()
        
        # Test with invalid output directory
        with pytest.raises(Exception):
            generator.generate_project(
                output_dir="/invalid/nonexistent/path",
                context=minimal_context
            )

    def test_template_completeness(self, temp_output_dir, minimal_context):
        """Test that generated template includes all expected features."""
        generator = ProjectGenerator()
        result_path = generator.generate_project(
            output_dir=str(temp_output_dir),
            context=minimal_context
        )
        
        project_dir = Path(result_path)
        
        # Check for security features
        assert (project_dir / ".github" / "workflows" / "security.yml").exists()
        
        # Check for Unit of Work implementation
        assert (project_dir / "app" / "core" / "unit_of_work.py").exists()
        
        # Check for comprehensive testing
        assert (project_dir / "tests" / "unit" / "test_unit_of_work.py").exists()
        
        # Check for AI-specific tests
        assert (project_dir / "tests" / "unit" / "test_ai_providers.py").exists()
        
        # Check for Docker and infrastructure
        assert (project_dir / "terraform" / "modules").exists()
        assert (project_dir / "docker" / "Dockerfile.prod").exists()