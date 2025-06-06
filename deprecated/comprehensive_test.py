#!/usr/bin/env python3
"""
Comprehensive testing script for KickStartMyAI cookiecutter template.
Tests multiple scenarios and configurations to ensure robustness.
"""

import sys
import json
import subprocess
import os
import tempfile
import shutil
from pathlib import Path
import time

# Define comprehensive test matrix based on actual cookiecutter.json
TEST_SCENARIOS = [
    # Core database type combinations
    {
        'project_name': 'PostgreSQL Project',
        'database_type': 'postgresql',
        'include_redis': 'y',
        'include_monitoring': 'y',
        'include_load_testing': 'y',
        'environment': 'development'
    },
    {
        'project_name': 'MySQL Project',
        'database_type': 'mysql', 
        'include_redis': 'n',
        'include_monitoring': 'y',
        'include_load_testing': 'n',
        'environment': 'production'
    },
    {
        'project_name': 'SQLite Project',
        'database_type': 'sqlite',
        'include_redis': 'n',
        'include_monitoring': 'n',
        'include_load_testing': 'n',
        'environment': 'development'
    },
    # AWS region variations
    {
        'project_name': 'US East Project',
        'database_type': 'postgresql',
        'aws_region': 'us-east-1',
        'include_redis': 'y',
        'include_monitoring': 'y',
        'include_load_testing': 'y',
        'environment': 'production'
    },
    {
        'project_name': 'EU West Project',
        'database_type': 'postgresql',
        'aws_region': 'eu-west-1',
        'include_redis': 'y',
        'include_monitoring': 'y',
        'include_load_testing': 'n',
        'environment': 'staging'
    },
    # AI provider variations
    {
        'project_name': 'OpenAI Only Project',
        'include_openai': 'y',
        'include_anthropic': 'n',
        'include_gemini': 'n',
        'database_type': 'postgresql',
        'include_redis': 'y',
        'environment': 'development'
    },
    {
        'project_name': 'Anthropic Only Project', 
        'include_openai': 'n',
        'include_anthropic': 'y',
        'include_gemini': 'n',
        'database_type': 'postgresql',
        'include_redis': 'y',
        'environment': 'development'
    },
    # Security and HTTPS variations
    {
        'project_name': 'HTTPS Project',
        'database_type': 'postgresql',
        'use_https': 'y',
        'domain_name': 'myapi.example.com',
        'include_monitoring': 'y',
        'environment': 'production'
    },
    # Minimal configuration
    {
        'project_name': 'Minimal Project',
        'database_type': 'sqlite',
        'include_redis': 'n',
        'include_monitoring': 'n',
        'include_load_testing': 'n',
        'include_openai': 'n',
        'include_anthropic': 'n',
        'include_gemini': 'n',
        'use_https': 'n',
        'environment': 'development'
    },
    # Maximum features configuration
    {
        'project_name': 'Full Featured Project',
        'database_type': 'postgresql',
        'include_redis': 'y',
        'include_monitoring': 'y',
        'include_load_testing': 'y',
        'include_openai': 'y',
        'include_anthropic': 'y',
        'include_gemini': 'y',
        'use_https': 'y',
        'domain_name': 'api.mycompany.com',
        'aws_region': 'us-west-2',
        'environment': 'production',
        'log_level': 'INFO'
    }
]

CRITICAL_FILES = [
    'pyproject.toml',
    'app/main.py',
    'app/core/config.py',
    'app/db/session.py',
    'app/api/v1/api.py',
    'tests/conftest.py',
    'docker-compose.yml',
    'Dockerfile',
    '.github/workflows/test.yml',
    'alembic.ini',
    'alembic/env.py',
    'README.md',
    'Makefile'
]

def validate_python_syntax(project_path):
    """Validate Python syntax in all .py files."""
    python_files = list(project_path.rglob('*.py'))
    errors = []
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            compile(content, str(py_file), 'exec')
        except SyntaxError as e:
            errors.append(f"{py_file}: {e}")
        except Exception as e:
            errors.append(f"{py_file}: {e}")
    
    return errors

def validate_configuration_coherence(project_path, scenario):
    """Validate that the generated configuration matches the scenario."""
    issues = []
    
    # Check requirements.txt for database dependencies
    requirements_path = project_path / 'requirements.txt'
    if requirements_path.exists():
        with open(requirements_path, 'r') as f:
            content = f.read()
            
        # Check database dependencies
        db_type = scenario.get('database_type', 'postgresql')
        if db_type == 'postgresql':
            if 'asyncpg' not in content:
                issues.append("PostgreSQL selected but asyncpg dependency missing")
            if 'psycopg2-binary' not in content:
                issues.append("PostgreSQL selected but psycopg2-binary dependency missing")
        elif db_type == 'mysql':
            if 'aiomysql' not in content:
                issues.append("MySQL selected but aiomysql dependency missing")
            if 'PyMySQL' not in content:
                issues.append("MySQL selected but PyMySQL dependency missing")
        elif db_type == 'sqlite':
            if 'aiosqlite' not in content:
                issues.append("SQLite selected but aiosqlite dependency missing")
        
        # Check Redis dependencies
        include_redis = scenario.get('include_redis', 'y')
        if include_redis == 'y' and 'redis==' not in content:
            issues.append("Redis enabled but redis dependency missing")
        elif include_redis == 'n' and 'redis==' in content:
            issues.append("Redis disabled but redis dependency present")
            
        # Check AI provider dependencies
        include_openai = scenario.get('include_openai', 'y')
        if include_openai == 'y' and 'openai==' not in content:
            issues.append("OpenAI enabled but openai dependency missing")
        elif include_openai == 'n' and 'openai==' in content:
            issues.append("OpenAI disabled but openai dependency present")
            
        include_anthropic = scenario.get('include_anthropic', 'y')
        if include_anthropic == 'y' and 'anthropic==' not in content:
            issues.append("Anthropic enabled but anthropic dependency missing")
        elif include_anthropic == 'n' and 'anthropic==' in content:
            issues.append("Anthropic disabled but anthropic dependency present")
            
        include_gemini = scenario.get('include_gemini', 'n')
        if include_gemini == 'y' and 'google-generativeai==' not in content:
            issues.append("Gemini enabled but google-generativeai dependency missing")
        elif include_gemini == 'n' and 'google-generativeai==' in content:
            issues.append("Gemini disabled but google-generativeai dependency present")
    
    # Check docker-compose.yml for services
    docker_compose_path = project_path / 'docker-compose.yml'
    if docker_compose_path.exists():
        with open(docker_compose_path, 'r') as f:
            content = f.read()
            
        include_redis = scenario.get('include_redis', 'y')
        if include_redis == 'y' and 'redis:' not in content:
            issues.append("Redis enabled but not in docker-compose.yml")
        elif include_redis == 'n' and 'redis:' in content:
            issues.append("Redis disabled but present in docker-compose.yml")
            
        # Check database service
        db_type = scenario.get('database_type', 'postgresql')
        if db_type == 'postgresql' and 'postgres:' not in content:
            issues.append("PostgreSQL selected but not in docker-compose.yml")
        elif db_type == 'mysql' and 'mysql:' not in content:
            issues.append("MySQL selected but not in docker-compose.yml")
    
    return issues

def validate_project_structure(project_path):
    """Validate expected directory structure."""
    expected_dirs = [
        'app', 'tests', 'alembic', '.github', 'docs', 
        'scripts', 'app/api', 'app/core', 'app/db'
    ]
    missing_dirs = []
    
    for expected_dir in expected_dirs:
        if not (project_path / expected_dir).exists():
            missing_dirs.append(expected_dir)
    
    return missing_dirs

def run_comprehensive_tests():
    """Run comprehensive tests on all scenarios."""
    print("🚀 Starting Comprehensive KickStartMyAI Template Testing")
    print("=" * 70)
    
    total_scenarios = len(TEST_SCENARIOS)
    passed = 0
    failed = 0
    warnings = 0
    
    for i, scenario in enumerate(TEST_SCENARIOS, 1):
        project_name = scenario.get('project_name', f'Test Project {i}')
        print(f"\n📋 Scenario {i}/{total_scenarios}: {project_name}")
        print("-" * 50)
        
        # Create temp directory for this test
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Clean up any existing project first
                existing_project = Path(f"{scenario['project_name'].lower().replace(' ', '_').replace('-', '_')}")
                if existing_project.exists():
                    shutil.rmtree(existing_project)
                
                # Build cookiecutter command
                cmd = ['cookiecutter', '.', '--no-input', '-o', temp_dir]
                for key, value in scenario.items():
                    cmd.extend(['-v', f'{key}={value}'])
                
                print(f"🔧 Generating with config: {dict(list(scenario.items())[:3])}...")
                
                # Run cookiecutter
                start_time = time.time()
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
                generation_time = time.time() - start_time
                
                if result.returncode != 0:
                    print(f"❌ Generation failed in {generation_time:.2f}s")
                    print(f"   Error: {result.stderr.strip()}")
                    failed += 1
                    continue
                
                # Find generated project
                project_dirs = [d for d in os.listdir(temp_dir) 
                              if os.path.isdir(os.path.join(temp_dir, d))]
                
                if not project_dirs:
                    print("❌ No project directory created")
                    failed += 1
                    continue
                
                project_path = Path(temp_dir) / project_dirs[0]
                print(f"✅ Generated in {generation_time:.2f}s: {project_path.name}")
                
                # Validation checks
                validation_passed = True
                warning_count = 0
                
                # 1. Check critical files
                missing_files = []
                for file in CRITICAL_FILES:
                    if not (project_path / file).exists():
                        missing_files.append(file)
                
                if missing_files:
                    print(f"❌ Missing critical files: {missing_files[:3]}{'...' if len(missing_files) > 3 else ''}")
                    validation_passed = False
                
                # 2. Validate Python syntax
                syntax_errors = validate_python_syntax(project_path)
                if syntax_errors:
                    print(f"❌ Python syntax errors: {len(syntax_errors)} files")
                    validation_passed = False
                
                # 3. Validate project structure
                missing_dirs = validate_project_structure(project_path)
                if missing_dirs:
                    print(f"⚠️  Missing directories: {missing_dirs}")
                    warning_count += 1
                
                # 4. Validate configuration coherence
                config_issues = validate_configuration_coherence(project_path, scenario)
                if config_issues:
                    print(f"⚠️  Configuration issues: {config_issues[:2]}{'...' if len(config_issues) > 2 else ''}")
                    warning_count += 1
                
                # 5. Check specific features
                features_check = []
                
                # Database configuration
                db_type = scenario.get('database_type', 'postgresql')
                requirements_path = project_path / 'requirements.txt'
                if requirements_path.exists():
                    with open(requirements_path, 'r') as f:
                        req_content = f.read()
                        if db_type == 'postgresql' and 'asyncpg' in req_content:
                            features_check.append("✓ PostgreSQL async driver")
                        elif db_type == 'mysql' and 'aiomysql' in req_content:
                            features_check.append("✓ MySQL async driver")
                        elif db_type == 'sqlite':
                            features_check.append("✓ SQLite configuration")
                
                # AI providers check
                if scenario.get('include_openai', 'y') == 'y' and 'openai' in req_content:
                    features_check.append("✓ OpenAI integration")
                if scenario.get('include_anthropic', 'y') == 'y' and 'anthropic' in req_content:
                    features_check.append("✓ Anthropic integration")
                if scenario.get('include_gemini', 'n') == 'y' and 'google-generativeai' in req_content:
                    features_check.append("✓ Gemini integration")
                
                # Final result
                if validation_passed:
                    if warning_count == 0:
                        print("🎉 All validations passed!")
                        passed += 1
                    else:
                        print(f"⚠️  Passed with {warning_count} warnings")
                        warnings += 1
                        passed += 1
                    
                    for check in features_check[:3]:  # Show first 3 features
                        print(f"   {check}")
                else:
                    print("❌ Critical validation failures")
                    failed += 1
                    
            except subprocess.TimeoutExpired:
                print("❌ Generation timed out (>60s)")
                failed += 1
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                failed += 1
    
    # Final summary
    print("\n" + "=" * 70)
    print("📊 COMPREHENSIVE TEST RESULTS")
    print("=" * 70)
    print(f"Total scenarios tested: {total_scenarios}")
    print(f"✅ Passed: {passed}")
    print(f"⚠️  Warnings: {warnings}")  
    print(f"❌ Failed: {failed}")
    print(f"📈 Success rate: {(passed/total_scenarios)*100:.1f}%")
    
    if passed == total_scenarios:
        print("\n🎉 ALL TESTS PASSED! Template is production-ready!")
        return True
    elif passed + warnings == total_scenarios:
        print(f"\n⚠️  All tests passed but with {warnings} warnings to review")
        return True
    else:
        print(f"\n💥 {failed} scenarios failed - needs attention")
        return False

if __name__ == "__main__":
    success = run_comprehensive_tests()
    sys.exit(0 if success else 1) 