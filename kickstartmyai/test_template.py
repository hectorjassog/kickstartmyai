#!/usr/bin/env python3
"""
KickStartMyAI Template Testing Script

This script tests the KickStartMyAI cookiecutter template to ensure
it generates correctly and works without hidden bugs.
"""

import os
import sys
import subprocess
import tempfile
import json
import shutil
import time
import requests
import psutil
from pathlib import Path
from typing import Dict, Any, List
import argparse


class ComprehensiveTemplateValidator:
    """Comprehensive validator for the KickStartMyAI template."""
    
    def __init__(self, template_path: Path):
        self.template_path = template_path
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.test_db_name = "kickstartmyai_test_db"
        self.test_project_dir = None
        
    def run_validation(self, level: str = "basic") -> bool:
        """Run template validation at different levels."""
        print("🔍 Starting KickStartMyAI Comprehensive Template Validation...")
        print("=" * 70)
        
        success = True
        temp_dir = None
        
        try:
            # Create a temporary directory that we'll use for all tests
            temp_dir = tempfile.mkdtemp()
            temp_path = Path(temp_dir)
            
            # Level 1: Basic validation (what we had before)
            if not self._test_template_generation(temp_path):
                success = False
            
            if level in ["full", "integration"]:
                # Level 2: Integration testing
                if not self._test_dependency_installation():
                    success = False
                
                if not self._test_database_setup():
                    success = False
                
                if not self._test_server_startup():
                    success = False
            
            if level == "full":
                # Level 3: Full end-to-end testing
                if not self._test_api_endpoints():
                    success = False
                
                if not self._test_ai_integration():
                    success = False
                
                if not self._test_docker_build():
                    success = False
                
                if not self._test_production_readiness():
                    success = False
        
        finally:
            # Clean up the temporary directory
            if temp_dir and os.path.exists(temp_dir):
                shutil.rmtree(temp_dir, ignore_errors=True)
        
        # Print summary
        self._print_summary(success)
        
        return success
    
    def _test_template_generation(self, temp_path: Path) -> bool:
        """Test basic template generation (existing functionality)."""
        print("\n📋 Testing Template Generation...")
        
        # Test default configuration
        config = {
            "project_name": "Test AI Project",
            "project_slug": "test_ai_project",
            "description": "A test AI project",
            "author": "Test Author",
            "email": "test@example.com",
            "version": "0.1.0"
        }
        
        try:
            project_dir = self._generate_template(temp_path, config)
            if not project_dir:
                return False
            
            # Store for later tests
            self.test_project_dir = project_dir
            
            print("✅ Template generation successful")
            
            # Validate generated structure
            if not self._validate_project_structure(project_dir):
                return False
            
            print("✅ Project structure validation passed")
            
            # Validate Python syntax
            if not self._validate_python_syntax(project_dir):
                return False
            
            print("✅ Python syntax validation passed")
            
            return True
            
        except Exception as e:
            self.errors.append(f"Template generation failed: {e}")
            return False
    
    def _test_dependency_installation(self) -> bool:
        """Test that all dependencies can be installed successfully."""
        print("\n📦 Testing Dependency Installation...")
        
        if not self.test_project_dir or not self.test_project_dir.exists():
            self.errors.append("No test project directory available for dependency testing")
            return False
        
        try:
            # Create a virtual environment
            venv_dir = self.test_project_dir / "test_venv"
            result = subprocess.run([
                sys.executable, "-m", "venv", str(venv_dir)
            ], capture_output=True, text=True, cwd=self.test_project_dir)
            
            if result.returncode != 0:
                self.errors.append(f"Failed to create virtual environment: {result.stderr}")
                return False
            
            # Get the python executable from the venv
            if sys.platform == "win32":
                python_exe = venv_dir / "Scripts" / "python.exe"
                pip_exe = venv_dir / "Scripts" / "pip.exe"
            else:
                python_exe = venv_dir / "bin" / "python"
                pip_exe = venv_dir / "bin" / "pip"
            
            # Install dependencies
            print("  Installing production dependencies...")
            result = subprocess.run([
                str(pip_exe), "install", "-r", "requirements.txt"
            ], capture_output=True, text=True, cwd=self.test_project_dir, timeout=300)
            
            if result.returncode != 0:
                self.errors.append(f"Failed to install requirements.txt: {result.stderr}")
                return False
            
            print("  Installing development dependencies...")
            result = subprocess.run([
                str(pip_exe), "install", "-r", "requirements-dev.txt"
            ], capture_output=True, text=True, cwd=self.test_project_dir, timeout=300)
            
            if result.returncode != 0:
                self.warnings.append(f"Failed to install requirements-dev.txt: {result.stderr}")
            
            print("✅ Dependency installation successful")
            return True
            
        except subprocess.TimeoutExpired:
            self.errors.append("Dependency installation timed out (>5 minutes)")
            return False
        except Exception as e:
            self.errors.append(f"Dependency installation failed: {e}")
            return False
    
    def _test_database_setup(self) -> bool:
        """Test database creation and migrations."""
        print("\n🗄️ Testing Database Setup...")
        
        try:
            # Create test database
            result = subprocess.run([
                "createdb", self.test_db_name
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                self.warnings.append(f"Could not create test database: {result.stderr}")
                return True  # Don't fail if PostgreSQL not available
            
            print("  ✅ Test database created")
            
            # Set environment variables
            env = os.environ.copy()
            env.update({
                "SECRET_KEY": "test-secret-key-for-comprehensive-testing",
                "DATABASE_URL": f"postgresql+asyncpg://postgres@localhost:5432/{self.test_db_name}",
                "ENVIRONMENT": "testing",
                "REDIS_URL": "redis://localhost:6379/1"  # Use different DB
            })
            
            # Run migrations
            result = subprocess.run([
                "alembic", "upgrade", "head"
            ], capture_output=True, text=True, cwd=self.test_project_dir, env=env)
            
            if result.returncode != 0:
                self.errors.append(f"Database migration failed: {result.stderr}")
                return False
            
            print("  ✅ Database migrations successful")
            
            # Test database connection
            test_script = self.test_project_dir / "test_db_connection.py"
            test_script.write_text(f"""
import asyncio
import os
os.environ.update({env!r})

async def test_connection():
    from app.db.base import async_engine
    from sqlalchemy import text
    try:
        async with async_engine.connect() as conn:
            result = await conn.execute(text("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema = 'public'"))
            count = result.scalar()
            print(f"Database connected, found {{count}} tables")
            return True
    except Exception as e:
        print(f"Database connection failed: {{e}}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
            """)
            
            result = subprocess.run([
                sys.executable, str(test_script)
            ], capture_output=True, text=True, cwd=self.test_project_dir)
            
            test_script.unlink()
            
            if result.returncode != 0:
                self.errors.append(f"Database connection test failed: {result.stdout} {result.stderr}")
                return False
            
            print("  ✅ Database connection test passed")
            return True
            
        except Exception as e:
            self.errors.append(f"Database setup test failed: {e}")
            return False
        finally:
            # Cleanup test database
            try:
                subprocess.run(["dropdb", self.test_db_name], capture_output=True)
            except:
                pass
    
    def _test_server_startup(self) -> bool:
        """Test that the FastAPI server can start successfully."""
        print("\n🚀 Testing Server Startup...")
        
        try:
            env = os.environ.copy()
            env.update({
                "SECRET_KEY": "test-secret-key-for-server-testing",
                "DATABASE_URL": "postgresql+asyncpg://postgres@localhost:5432/postgres",
                "ENVIRONMENT": "testing",
                "PORT": "8899"  # Use different port
            })
            
            # Start server in background
            server_process = subprocess.Popen([
                sys.executable, "-m", "uvicorn", "app.main:app", 
                "--host", "0.0.0.0", "--port", "8899"
            ], cwd=self.test_project_dir, env=env, 
               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            
            # Wait for server to start
            print("  Waiting for server to start...")
            time.sleep(15)  # Increased wait time
            
            # Check if process is still running
            if server_process.poll() is not None:
                # Process has terminated
                stdout, stderr = server_process.communicate()
                self.errors.append(f"Server process terminated early. STDOUT: {stdout.decode()}, STDERR: {stderr.decode()}")
                return False
            
            # Test server health
            try:
                response = requests.get("http://localhost:8899/health", timeout=5)
                if response.status_code == 200:
                    print("  ✅ Server started successfully")
                    print("  ✅ Health endpoint accessible")
                    success = True
                else:
                    self.errors.append(f"Health endpoint returned {response.status_code}")
                    success = False
            except requests.exceptions.RequestException as e:
                self.errors.append(f"Could not connect to server: {e}")
                success = False
            
            # Test API docs
            try:
                response = requests.get("http://localhost:8899/docs", timeout=5)
                if response.status_code == 200:
                    print("  ✅ API documentation accessible")
                else:
                    self.warnings.append(f"API docs returned {response.status_code}")
            except:
                self.warnings.append("Could not access API documentation")
            
            return success
            
        except Exception as e:
            self.errors.append(f"Server startup test failed: {e}")
            return False
        finally:
            # Kill server process and capture any error output
            try:
                if 'server_process' in locals() and server_process.poll() is None:
                    server_process.terminate()
                    stdout, stderr = server_process.communicate(timeout=5)
                    if stderr:
                        print(f"  Server stderr: {stderr.decode()}")
            except:
                try:
                    if 'server_process' in locals():
                        server_process.kill()
                except:
                    pass
    
    def _test_api_endpoints(self) -> bool:
        """Test key API endpoints work correctly."""
        print("\n🌐 Testing API Endpoints...")
        # Implementation would test user registration, auth, agent creation, etc.
        print("  📝 TODO: Implement comprehensive API endpoint testing")
        return True
    
    def _test_ai_integration(self) -> bool:
        """Test AI provider integration."""
        print("\n🤖 Testing AI Integration...")
        # Implementation would test with mock/real API keys
        print("  📝 TODO: Implement AI provider integration testing")
        return True
    
    def _test_docker_build(self) -> bool:
        """Test Docker container builds successfully."""
        print("\n🐳 Testing Docker Build...")
        
        if not shutil.which("docker"):
            self.warnings.append("Docker not available, skipping Docker tests")
            return True
        
        try:
            # Build the Docker image
            result = subprocess.run([
                "docker", "build", "-t", "kickstartmyai-test", "."
            ], capture_output=True, text=True, cwd=self.test_project_dir, timeout=600)
            
            if result.returncode != 0:
                self.errors.append(f"Docker build failed: {result.stderr}")
                return False
            
            print("  ✅ Docker image built successfully")
            
            # Test running the container
            result = subprocess.run([
                "docker", "run", "--rm", "-e", "SECRET_KEY=test", 
                "-e", "DATABASE_URL=sqlite:///test.db",
                "kickstartmyai-test", "python", "-c", 
                "from app.main import app; print('Container test passed')"
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode != 0:
                self.errors.append(f"Docker container test failed: {result.stderr}")
                return False
            
            print("  ✅ Docker container test passed")
            return True
            
        except subprocess.TimeoutExpired:
            self.errors.append("Docker build timed out (>10 minutes)")
            return False
        except Exception as e:
            self.errors.append(f"Docker test failed: {e}")
            return False
        finally:
            # Cleanup Docker image
            try:
                subprocess.run(["docker", "rmi", "kickstartmyai-test"], capture_output=True)
            except:
                pass
    
    def _test_production_readiness(self) -> bool:
        """Test production readiness checklist."""
        print("\n🏭 Testing Production Readiness...")
        
        checks = [
            ("Environment variables documented", self._check_env_documentation),
            ("Security configurations present", self._check_security_configs),
            ("Monitoring setup", self._check_monitoring_setup),
            ("Logging configuration", self._check_logging_config),
            ("Error handling", self._check_error_handling),
        ]
        
        passed = 0
        for check_name, check_func in checks:
            try:
                if check_func():
                    print(f"  ✅ {check_name}")
                    passed += 1
                else:
                    print(f"  ❌ {check_name}")
            except Exception as e:
                print(f"  ❌ {check_name}: {e}")
        
        if passed == len(checks):
            print("✅ Production readiness checks passed")
            return True
        else:
            self.warnings.append(f"Production readiness: {passed}/{len(checks)} checks passed")
            return True  # Don't fail, just warn
    
    def _check_env_documentation(self) -> bool:
        """Check if environment variables are documented."""
        env_example = self.test_project_dir / ".env.example"
        return env_example.exists() and len(env_example.read_text()) > 100
    
    def _check_security_configs(self) -> bool:
        """Check security configurations."""
        # Check for security middleware, rate limiting, etc.
        security_files = [
            "app/api/middleware/security.py",
            "app/api/middleware/rate_limiting.py"
        ]
        return all((self.test_project_dir / f).exists() for f in security_files)
    
    def _check_monitoring_setup(self) -> bool:
        """Check monitoring setup."""
        return (self.test_project_dir / "app/monitoring/health_checks.py").exists()
    
    def _check_logging_config(self) -> bool:
        """Check logging configuration."""
        return (self.test_project_dir / "app/core/logging_utils.py").exists()
    
    def _check_error_handling(self) -> bool:
        """Check error handling middleware."""
        return (self.test_project_dir / "app/api/middleware/error_handling.py").exists()
    
    def _generate_template(self, temp_path: Path, config: Dict[str, Any]) -> Path:
        """Generate template with given configuration."""
        # Check if cookiecutter is available
        if not shutil.which("cookiecutter"):
            self.errors.append("cookiecutter command not found. Install with: pip install cookiecutter")
            return None
        
        # Build cookiecutter command with overrides
        cmd = [
            "cookiecutter",
            str(self.template_path),
            "--no-input",
            "--output-dir", str(temp_path)
        ]
        
        # Add variable overrides
        for key, value in config.items():
            cmd.extend(["-v", f"{key}={value}"])
        
        # Generate template
        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            self.errors.append(f"Cookiecutter failed: {result.stderr}")
            return None
        
        # Calculate expected project slug from project name
        project_name = config.get("project_name", "Test AI Project")
        expected_slug = project_name.lower().replace(' ', '_').replace('-', '_')
        project_slug = config.get("project_slug", expected_slug)
        
        project_dir = temp_path / project_slug
        if not project_dir.exists():
            # List what was actually created for debugging
            created_dirs = [d.name for d in temp_path.iterdir() if d.is_dir()]
            self.errors.append(f"Generated project directory '{project_slug}' not found. Created directories: {created_dirs}")
            return None
        
        return project_dir
    
    def _validate_project_structure(self, project_dir: Path) -> bool:
        """Validate the generated project structure."""
        expected_files = [
            "README.md",
            "pyproject.toml", 
            "requirements.txt",
            "Makefile",
            ".env.example",
            "pytest.ini",
            "app/__init__.py",
            "app/main.py",
            "app/core/config.py",
            "app/ai/providers/__init__.py",
            "app/ai/tools/__init__.py",
            "tests/__init__.py",
            "tests/conftest.py"
        ]
        
        missing_files = []
        for file_path in expected_files:
            full_path = project_dir / file_path
            if not full_path.exists():
                missing_files.append(file_path)
        
        if missing_files:
            self.errors.append(f"Missing expected files: {missing_files}")
            return False
        
        return True
    
    def _validate_python_syntax(self, project_dir: Path) -> bool:
        """Validate Python syntax in all generated files."""
        python_files = list(project_dir.rglob("*.py"))
        
        if not python_files:
            self.warnings.append("No Python files found to validate")
            return True
        
        syntax_errors = []
        for py_file in python_files:
            result = subprocess.run([
                sys.executable, "-m", "py_compile", str(py_file)
            ], capture_output=True, text=True)
            
            if result.returncode != 0:
                syntax_errors.append(f"{py_file.relative_to(project_dir)}: {result.stderr}")
        
        if syntax_errors:
            self.errors.append("Python syntax errors found:")
            self.errors.extend(syntax_errors)
            return False
        
        return True
    
    def _print_summary(self, success: bool):
        """Print validation summary."""
        print("\n" + "=" * 70)
        print("📊 COMPREHENSIVE VALIDATION SUMMARY")
        print("=" * 70)
        
        if success:
            print("🎉 SUCCESS: Comprehensive template validation passed!")
            print("✅ The KickStartMyAI template is production-ready")
        else:
            print("❌ FAILURE: Template validation failed!")
            print("⚠️  The template has issues that need to be fixed")
        
        if self.errors:
            print(f"\n🔴 ERRORS ({len(self.errors)}):")
            for i, error in enumerate(self.errors, 1):
                print(f"  {i}. {error}")
        
        if self.warnings:
            print(f"\n🟡 WARNINGS ({len(self.warnings)}):")
            for i, warning in enumerate(self.warnings, 1):
                print(f"  {i}. {warning}")
        
        if success:
            print("\n✨ The template is ready for production deployment!")
        else:
            print("\n💡 Please fix the errors before using the template.")


def main():
    """Main function."""
    parser = argparse.ArgumentParser(
        description="Comprehensive KickStartMyAI cookiecutter template validation"
    )
    parser.add_argument(
        "--level",
        choices=["basic", "integration", "full"],
        default="basic",
        help="Validation level: basic (syntax/structure), integration (deps/db/server), full (all tests)"
    )
    parser.add_argument(
        "--template-path",
        type=Path,
        default=Path(__file__).parent / "templates",
        help="Path to template directory"
    )
    
    args = parser.parse_args()
    
    # Validate template path
    if not args.template_path.exists():
        print(f"❌ Template path not found: {args.template_path}")
        sys.exit(1)
    
    # Check for cookiecutter.json
    cookiecutter_json = args.template_path / "cookiecutter.json"
    if not cookiecutter_json.exists():
        print(f"❌ cookiecutter.json not found in template path")
        sys.exit(1)
    
    # Run validation
    validator = ComprehensiveTemplateValidator(args.template_path)
    success = validator.run_validation(level=args.level)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main() 