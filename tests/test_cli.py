"""Tests for CLI functionality."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path
from typer.testing import CliRunner

from kickstartmyai.cli.main import app, main


class TestCLI:
    """Test CLI commands."""

    def setUp(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_help(self):
        """Test CLI help command."""
        runner = CliRunner()
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "KickStartMyAI" in result.stdout

    @patch('kickstartmyai.cli.main.ProjectGenerator')
    def test_create_command_success(self, mock_generator_class):
        """Test successful project creation."""
        runner = CliRunner()
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_project.return_value = "/tmp/test-project"
        
        result = runner.invoke(app, [
            "create", 
            "--project-name", "Test Project",
            "--project-slug", "test-project",
            "--author-name", "Test Author",
            "--author-email", "test@example.com",
            "--output-dir", "/tmp"
        ])
        
        assert result.exit_code == 0
        mock_generator.generate_project.assert_called_once()

    @patch('kickstartmyai.cli.main.ProjectGenerator')
    def test_create_command_validation_error(self, mock_generator_class):
        """Test project creation with validation error."""
        runner = CliRunner()
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        
        from kickstartmyai.core.validators import ProjectValidationError
        mock_generator.validate_context.side_effect = ProjectValidationError(
            "project_name", "Invalid project name"
        )
        
        result = runner.invoke(app, [
            "create",
            "--project-name", "",  # Invalid empty name
            "--project-slug", "test-project",
            "--author-name", "Test Author", 
            "--author-email", "test@example.com"
        ])
        
        assert result.exit_code != 0

    @patch('kickstartmyai.cli.main.ProjectGenerator')
    def test_create_command_generation_error(self, mock_generator_class):
        """Test project creation with generation error."""
        runner = CliRunner()
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_project.side_effect = Exception("Generation failed")
        
        result = runner.invoke(app, [
            "create",
            "--project-name", "Test Project",
            "--project-slug", "test-project", 
            "--author-name", "Test Author",
            "--author-email", "test@example.com"
        ])
        
        assert result.exit_code != 0

    def test_version_command(self):
        """Test version command."""
        runner = CliRunner()
        result = runner.invoke(app, ["version"])
        assert result.exit_code == 0
        # Should contain version information
        assert "KickStartMyAI" in result.stdout

    @patch('kickstartmyai.cli.main.ProjectGenerator')
    def test_interactive_mode(self, mock_generator_class):
        """Test interactive project creation mode."""
        runner = CliRunner()
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.generate_project.return_value = "/tmp/test-project"
        
        # Simulate interactive input (match CLI prompts)
        inputs = [
            "Test Project",      # project name
            "Test Author",       # author name  
            "test@example.com",  # author email
            "Test Description",  # description
            "us-east-1",         # aws region
            "y",                 # include redis
            "y"                  # include monitoring
        ]
        
        result = runner.invoke(app, ["create", "--interactive"], input="\n".join(inputs))
        
        # Should not fail (exact exit code depends on mocked behavior)
        mock_generator.generate_project.assert_called_once()

    def test_list_templates_command(self):
        """Test list templates command."""
        runner = CliRunner()
        result = runner.invoke(app, ["list-templates"])
        assert result.exit_code == 0
        # Should list available templates
        assert "FastAPI AI Template" in result.stdout

    @patch('kickstartmyai.cli.main.ProjectGenerator')
    def test_validate_command_success(self, mock_generator_class):
        """Test validate command with valid template."""
        runner = CliRunner()
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.validate_template.return_value = True
        
        result = runner.invoke(app, ["validate"])
        assert result.exit_code == 0
        assert "valid" in result.stdout.lower()

    @patch('kickstartmyai.cli.main.ProjectGenerator')
    def test_validate_command_failure(self, mock_generator_class):
        """Test validate command with invalid template."""
        runner = CliRunner()
        mock_generator = Mock()
        mock_generator_class.return_value = mock_generator
        mock_generator.validate_template.side_effect = Exception("Validation failed")
        
        result = runner.invoke(app, ["validate"])
        assert result.exit_code != 0

    def test_main_function(self):
        """Test main function entry point."""
        with patch('kickstartmyai.cli.main.app') as mock_app:
            main()
            mock_app.assert_called_once()


class TestCLIUtilities:
    """Test CLI utility functions."""

    @patch('kickstartmyai.cli.main.console.print')
    def test_success_message(self, mock_print):
        """Test success message formatting."""
        from kickstartmyai.cli.main import success_message
        success_message("Test message")
        mock_print.assert_called_once()
        args = mock_print.call_args[0]
        assert "✅" in args[0] or "success" in args[0].lower()

    @patch('kickstartmyai.cli.main.console.print')
    def test_error_message(self, mock_print):
        """Test error message formatting."""
        from kickstartmyai.cli.main import error_message
        error_message("Test error")
        mock_print.assert_called_once()
        args = mock_print.call_args[0]
        assert "❌" in args[0] or "error" in args[0].lower()

    @patch('kickstartmyai.cli.main.console.print')
    def test_info_message(self, mock_print):
        """Test info message formatting.""" 
        from kickstartmyai.cli.main import info_message
        info_message("Test info")
        mock_print.assert_called_once()
        args = mock_print.call_args[0]
        assert "ℹ️" in args[0] or "info" in args[0].lower()


class TestCLIArguments:
    """Test CLI argument parsing and validation."""

    def test_create_with_all_options(self):
        """Test create command with all options specified."""
        runner = CliRunner()
        
        with patch('kickstartmyai.cli.main.ProjectGenerator') as mock_gen:
            mock_generator = Mock()
            mock_gen.return_value = mock_generator
            mock_generator.generate_project.return_value = "/tmp/test-project"
            
            result = runner.invoke(app, [
                "create",
                "--project-name", "My AI Project",
                "--project-slug", "my-ai-project", 
                "--description", "Test description",
                "--author-name", "John Doe",
                "--author-email", "john@example.com",
                "--database-type", "postgresql",
                "--aws-region", "us-west-2",
                "--output-dir", "/tmp",
                "--no-interactive"
            ])
            
            assert result.exit_code == 0
            mock_generator.generate_project.assert_called_once()

    def test_create_with_minimal_options(self):
        """Test create command with minimal required options."""
        runner = CliRunner()
        
        with patch('kickstartmyai.cli.main.ProjectGenerator') as mock_gen:
            mock_generator = Mock()
            mock_gen.return_value = mock_generator
            mock_generator.generate_project.return_value = "/tmp/test-project"
            
            result = runner.invoke(app, [
                "create",
                "--project-name", "Test Project",
                "--no-interactive"
            ])
            
            # Should use defaults for missing options
            mock_generator.generate_project.assert_called_once()

    def test_invalid_arguments(self):
        """Test CLI with invalid arguments."""
        runner = CliRunner()
        
        # Test invalid command
        result = runner.invoke(app, ["invalid-command"])
        assert result.exit_code != 0
        
        # Test missing required argument
        result = runner.invoke(app, ["create", "--no-interactive"])
        assert result.exit_code != 0