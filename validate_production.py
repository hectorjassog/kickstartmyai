#!/usr/bin/env python3
"""
KickStartMyAI Production Validation Script

This script performs comprehensive validation to ensure:
1. The cookiecutter package installs correctly
2. Templates generate successfully  
3. Generated projects are fully functional
4. All components work together seamlessly
"""

import os
import sys
import subprocess
import tempfile
import json
import shutil
import time
import requests
import signal
from pathlib import Path
from typing import Dict, Any, List, Optional
import argparse
from contextlib import contextmanager


class ValidationError(Exception):
    """Custom exception for validation failures."""
    pass


class KickStartMyAIValidator:
    """Comprehensive validator for KickStartMyAI template."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.temp_dirs: List[Path] = []
        
    def __del__(self):
        """Cleanup temporary directories."""
        for temp_dir in self.temp_dirs:
            if temp_dir.exists():
                shutil.rmtree(temp_dir, ignore_errors=True)
    
    def log(self, message: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = time.strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "WARNING": "⚠️",
            "ERROR": "❌",
            "DEBUG": "🔍"
        }.get(level, "📝")
        
        print(f"[{timestamp}] {prefix} {message}")
        
        if level == "ERROR":
            self.errors.append(message)
        elif level == "WARNING":
            self.warnings.append(message)
    
    def run_command(self, cmd: List[str], cwd: Optional[Path] = None, timeout: int = 300) -> subprocess.CompletedProcess:
        """Run shell command with timeout and error handling."""
        try:
            if self.verbose:
                self.log(f"Running: {' '.join(cmd)}", "DEBUG")
            
            result = subprocess.run(
                cmd,
                cwd=cwd,
                capture_output=True,
                text=True,
                timeout=timeout,
                check=False
            )
            
            if result.returncode != 0:
                self.log(f"Command failed: {' '.join(cmd)}", "ERROR")
                self.log(f"STDOUT: {result.stdout}", "DEBUG")
                self.log(f"STDERR: {result.stderr}", "DEBUG")
                raise ValidationError(f"Command failed with code {result.returncode}")
            
            return result
            
        except subprocess.TimeoutExpired:
            self.log(f"Command timed out: {' '.join(cmd)}", "ERROR")
            raise ValidationError("Command timeout")
        except Exception as e:
            self.log(f"Command error: {e}", "ERROR")
            raise ValidationError(f"Command execution failed: {e}")
    
    @contextmanager
    def temp_directory(self):
        """Create and manage temporary directory."""
        temp_dir = Path(tempfile.mkdtemp())
        self.temp_dirs.append(temp_dir)
        try:
            yield temp_dir
        finally:
            # Cleanup handled in __del__
            pass
    
    def validate_package_installation(self) -> bool:
        """Test package installation and CLI functionality."""
        self.log("Testing package installation...", "INFO")
        
        try:
            # Test CLI availability - try the proper CLI entry point first
            try:
                result = self.run_command([sys.executable, "-m", "kickstartmyai.cli.main", "--help"])
            except ValidationError:
                # Fallback to the __main__.py entry point
                result = self.run_command([sys.executable, "-m", "kickstartmyai", "--help"])
            
            # Check for key indicators in the help output
            help_output = result.stdout.lower()
            required_indicators = [
                "fastapi",  # Should mention FastAPI
                "generate",  # Should mention generation functionality
                "commands",  # Should show commands section
                "new"  # Should have the 'new' command
            ]
            
            missing_indicators = [indicator for indicator in required_indicators 
                                if indicator not in help_output]
            
            if missing_indicators:
                raise ValidationError(f"CLI help output missing key indicators: {missing_indicators}")
            
            self.log("Package installation validated", "SUCCESS")
            return True
            
        except Exception as e:
            self.log(f"Package installation failed: {e}", "ERROR")
            return False
    
    def validate_template_generation(self) -> bool:
        """Test template generation with various configurations."""
        self.log("Testing template generation...", "INFO")
        
        test_configs = [
            {
                "name": "minimal",
                "config": {
                    "project_name": "Minimal Test Project",
                    "project_slug": "minimal_test",
                    "project_description": "A minimal test project",
                    "author_name": "Test Author",
                    "author_email": "test@example.com",
                    "version": "0.1.0",
                    "include_docker": "n",
                    "include_redis": "n",
                    "database_type": "sqlite"
                }
            },
            {
                "name": "full",
                "config": {
                    "project_name": "Full Test Project", 
                    "project_slug": "full_test",
                    "project_description": "A full-featured test project",
                    "author_name": "Test Author",
                    "author_email": "test@example.com",
                    "version": "0.1.0",
                    "include_docker": "y",
                    "include_redis": "y",
                    "database_type": "postgresql"
                }
            }
        ]
        
        success = True
        for test_case in test_configs:
            try:
                with self.temp_directory() as temp_dir:
                    project_dir = self._generate_project(temp_dir, test_case["config"])
                    self._validate_project_structure(project_dir)
                    self._validate_python_syntax(project_dir)
                    
                    self.log(f"Template generation '{test_case['name']}' passed", "SUCCESS")
                    
            except Exception as e:
                self.log(f"Template generation '{test_case['name']}' failed: {e}", "ERROR")
                success = False
        
        return success
    
    def validate_project_functionality(self) -> bool:
        """Test that generated projects are fully functional."""
        self.log("Testing project functionality...", "INFO")
        
        config = {
            "project_name": "Functional Test Project",
            "project_slug": "functional_test",
            "project_description": "Testing project functionality",
            "author_name": "Test Author", 
            "author_email": "test@example.com",
            "version": "0.1.0",
            "include_docker": "y",
            "include_redis": "n",
            "database_type": "sqlite"
        }
        
        try:
            with self.temp_directory() as temp_dir:
                project_dir = self._generate_project(temp_dir, config)
                
                # Test dependency installation
                self._test_dependency_installation(project_dir)
                
                # Test database setup
                self._test_database_setup(project_dir)
                
                # Test application startup
                self._test_application_startup(project_dir)
                
                # Test API endpoints
                self._test_api_endpoints(project_dir)
                
                # Test Docker build (if included)
                if config.get("include_docker") == "y":
                    self._test_docker_build(project_dir)
                
                self.log("Project functionality validation passed", "SUCCESS")
                return True
                
        except Exception as e:
            self.log(f"Project functionality validation failed: {e}", "ERROR")
            return False
    
    def _generate_project(self, output_dir: Path, config: Dict[str, Any]) -> Path:
        """Generate project using cookiecutter."""
        # Create config file
        config_file = output_dir / "cookiecutter_config.json"
        with open(config_file, 'w') as f:
            json.dump(config, f, indent=2)
        
        # Get template path
        template_path = Path(__file__).parent / "kickstartmyai" / "templates"
        
        # Generate project
        cmd = [
            "cookiecutter",
            str(template_path),
            "--config-file", str(config_file),
            "--output-dir", str(output_dir),
            "--no-input"
        ]
        
        self.run_command(cmd)
        
        project_dir = output_dir / config["project_slug"]
        if not project_dir.exists():
            raise ValidationError(f"Project directory not created: {project_dir}")
        
        return project_dir
    
    def _validate_project_structure(self, project_dir: Path):
        """Validate generated project structure."""
        required_files = [
            "README.md",
            "requirements.txt", 
            "requirements-dev.txt",
            "pyproject.toml",
            "Makefile",
            "app/main.py",
            "app/__init__.py",
            "app/core/config.py",
            "app/api/v1/api.py",
            "app/db/base.py",
            "app/models/__init__.py",
            "tests/conftest.py",
            "alembic.ini",
            "alembic/env.py"
        ]
        
        for file_path in required_files:
            full_path = project_dir / file_path
            if not full_path.exists():
                raise ValidationError(f"Required file missing: {file_path}")
    
    def _validate_python_syntax(self, project_dir: Path):
        """Validate Python syntax in all .py files."""
        python_files = list(project_dir.rglob("*.py"))
        
        for py_file in python_files:
            try:
                with open(py_file, 'r') as f:
                    compile(f.read(), str(py_file), 'exec')
            except SyntaxError as e:
                raise ValidationError(f"Syntax error in {py_file}: {e}")
    
    def _test_dependency_installation(self, project_dir: Path):
        """Test that all dependencies install correctly."""
        self.log("Testing dependency installation...", "INFO")
        
        # Create virtual environment
        venv_dir = project_dir / ".venv"
        self.run_command([sys.executable, "-m", "venv", str(venv_dir)], cwd=project_dir)
        
        # Get python executable in venv
        if sys.platform == "win32":
            python_exe = venv_dir / "Scripts" / "python.exe"
            pip_exe = venv_dir / "Scripts" / "pip.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
            pip_exe = venv_dir / "bin" / "pip"
        
        # Install dependencies
        self.run_command([str(pip_exe), "install", "-r", "requirements.txt"], cwd=project_dir)
        self.run_command([str(pip_exe), "install", "-r", "requirements-dev.txt"], cwd=project_dir)
        
        # Test imports
        test_imports = [
            "import fastapi",
            "import sqlalchemy", 
            "import pydantic",
            "import uvicorn",
            "import pytest",
            "from app.main import app"
        ]
        
        for import_stmt in test_imports:
            self.run_command([str(python_exe), "-c", import_stmt], cwd=project_dir)
    
    def _test_database_setup(self, project_dir: Path):
        """Test database setup and migrations."""
        self.log("Testing database setup...", "INFO")
        
        venv_dir = project_dir / ".venv"
        if sys.platform == "win32":
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
        
        # Test Alembic commands
        self.run_command([str(python_exe), "-m", "alembic", "check"], cwd=project_dir)
        self.run_command([str(python_exe), "-m", "alembic", "upgrade", "head"], cwd=project_dir)
    
    def _test_application_startup(self, project_dir: Path):
        """Test that the application starts successfully."""
        self.log("Testing application startup...", "INFO")
        
        venv_dir = project_dir / ".venv"
        if sys.platform == "win32":
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
        
        # Start server in background
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_dir)
        
        process = subprocess.Popen(
            [str(python_exe), "-m", "uvicorn", "app.main:app", "--port", "8001"],
            cwd=project_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for startup
            time.sleep(5)
            
            # Check if process is running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                raise ValidationError(f"Application failed to start: {stderr.decode()}")
            
        finally:
            # Cleanup
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    
    def _test_api_endpoints(self, project_dir: Path):
        """Test API endpoints are accessible."""
        self.log("Testing API endpoints...", "INFO")
        
        venv_dir = project_dir / ".venv"
        if sys.platform == "win32":
            python_exe = venv_dir / "Scripts" / "python.exe"
        else:
            python_exe = venv_dir / "bin" / "python"
        
        # Start server
        env = os.environ.copy()
        env["PYTHONPATH"] = str(project_dir)
        
        process = subprocess.Popen(
            [str(python_exe), "-m", "uvicorn", "app.main:app", "--port", "8002"],
            cwd=project_dir,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        
        try:
            # Wait for startup
            time.sleep(5)
            
            # Test endpoints
            base_url = "http://localhost:8002"
            endpoints = [
                "/health",
                "/docs",
                "/api/v1/health"
            ]
            
            for endpoint in endpoints:
                try:
                    response = requests.get(f"{base_url}{endpoint}", timeout=10)
                    if response.status_code >= 400:
                        raise ValidationError(f"Endpoint {endpoint} returned {response.status_code}")
                except requests.RequestException as e:
                    raise ValidationError(f"Failed to access endpoint {endpoint}: {e}")
            
        finally:
            # Cleanup
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
    
    def _test_docker_build(self, project_dir: Path):
        """Test Docker build process."""
        self.log("Testing Docker build...", "INFO")
        
        # Check if Dockerfile exists
        dockerfile = project_dir / "Dockerfile"
        if not dockerfile.exists():
            dockerfile = project_dir / "docker" / "Dockerfile.prod"
        
        if not dockerfile.exists():
            raise ValidationError("No Dockerfile found")
        
        # Build Docker image
        image_name = f"kickstartmyai-test-{int(time.time())}"
        self.run_command([
            "docker", "build",
            "-t", image_name,
            "-f", str(dockerfile),
            "."
        ], cwd=project_dir, timeout=600)
        
        # Cleanup image
        try:
            self.run_command(["docker", "rmi", image_name])
        except:
            pass  # Ignore cleanup errors
    
    def run_full_validation(self) -> bool:
        """Run complete validation suite."""
        self.log("🚀 Starting KickStartMyAI Full Validation", "INFO")
        self.log("=" * 60, "INFO")
        
        success = True
        
        # Test package installation
        if not self.validate_package_installation():
            success = False
        
        # Test template generation
        if not self.validate_template_generation():
            success = False
        
        # Test project functionality  
        if not self.validate_project_functionality():
            success = False
        
        # Print summary
        self._print_summary(success)
        
        return success
    
    def _print_summary(self, success: bool):
        """Print validation summary."""
        self.log("=" * 60, "INFO")
        
        if success:
            self.log("🎉 ALL VALIDATIONS PASSED!", "SUCCESS")
            self.log("The KickStartMyAI template is ready for production use!", "SUCCESS")
        else:
            self.log("💥 VALIDATION FAILED!", "ERROR")
            self.log(f"Found {len(self.errors)} errors and {len(self.warnings)} warnings", "ERROR")
        
        if self.warnings:
            self.log(f"\n⚠️  Warnings ({len(self.warnings)}):", "WARNING")
            for warning in self.warnings:
                self.log(f"  • {warning}", "WARNING")
        
        if self.errors:
            self.log(f"\n❌ Errors ({len(self.errors)}):", "ERROR")
            for error in self.errors:
                self.log(f"  • {error}", "ERROR")


def main():
    """Main validation function."""
    parser = argparse.ArgumentParser(
        description="Validate KickStartMyAI template for production readiness"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    parser.add_argument(
        "--quick",
        action="store_true", 
        help="Run quick validation (skip functionality tests)"
    )
    
    args = parser.parse_args()
    
    validator = KickStartMyAIValidator(verbose=args.verbose)
    
    if args.quick:
        success = (
            validator.validate_package_installation() and
            validator.validate_template_generation()
        )
    else:
        success = validator.run_full_validation()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
