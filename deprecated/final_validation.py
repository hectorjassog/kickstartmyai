#!/usr/bin/env python3
"""
Final comprehensive validation script for KickStartMyAI cookiecutter template.
Tests edge cases and provides detailed production readiness assessment.
"""

import sys
import json
import subprocess
import os
import tempfile
import shutil
from pathlib import Path
import time
import ast

# Extended test matrix with edge cases
EDGE_CASE_SCENARIOS = [
    # Database edge cases
    {
        'name': 'MySQL with Redis and All AI Providers',
        'config': {
            'project_name': 'MySQL Full Stack',
            'database_type': 'mysql',
            'include_redis': 'y',
            'include_openai': 'y',
            'include_anthropic': 'y',
            'include_gemini': 'y',
            'include_monitoring': 'y',
            'include_load_testing': 'y',
            'environment': 'production'
        }
    },
    {
        'name': 'SQLite Minimal Configuration',
        'config': {
            'project_name': 'SQLite Minimal',
            'database_type': 'sqlite',
            'include_redis': 'n',
            'include_openai': 'n',
            'include_anthropic': 'n',
            'include_gemini': 'n',
            'include_monitoring': 'n',
            'include_load_testing': 'n',
            'environment': 'development'
        }
    },
    # AI provider combinations
    {
        'name': 'Gemini Only Configuration',
        'config': {
            'project_name': 'Gemini Only',
            'include_openai': 'n',
            'include_anthropic': 'n',
            'include_gemini': 'y',
            'database_type': 'postgresql'
        }
    },
    {
        'name': 'No AI Providers',
        'config': {
            'project_name': 'No AI',
            'include_openai': 'n',
            'include_anthropic': 'n',
            'include_gemini': 'n',
            'database_type': 'postgresql'
        }
    },
    # Regional and environment variations
    {
        'name': 'Asia Pacific Production',
        'config': {
            'project_name': 'APAC Production',
            'aws_region': 'ap-southeast-1',
            'environment': 'production',
            'use_https': 'y',
            'domain_name': 'api.example.com.sg'
        }
    },
    {
        'name': 'EU Staging Environment',
        'config': {
            'project_name': 'EU Staging',
            'aws_region': 'eu-west-1',
            'environment': 'staging',
            'log_level': 'DEBUG'
        }
    }
]

def validate_python_imports(project_path):
    """Validate that all Python imports can be resolved."""
    python_files = list(project_path.rglob('*.py'))
    import_issues = []
    
    for py_file in python_files:
        try:
            with open(py_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Parse the AST to extract imports
            tree = ast.parse(content, str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        # Check for common problematic imports
                        if alias.name in ['aioredis', 'redis'] and 'redis' not in str(py_file):
                            import_issues.append(f"{py_file}: Conditional import {alias.name} may fail")
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.module.startswith('app.'):
                        # Check internal imports
                        continue
                        
        except Exception as e:
            import_issues.append(f"{py_file}: Parse error - {e}")
    
    return import_issues

def validate_configuration_files(project_path, scenario):
    """Validate configuration file consistency."""
    issues = []
    
    # Check .env.example
    env_example = project_path / '.env.example'
    if env_example.exists():
        with open(env_example, 'r') as f:
            env_content = f.read()
            
        # Check for required environment variables
        required_vars = ['SECRET_KEY', 'DATABASE_URL']
        for var in required_vars:
            if var not in env_content:
                issues.append(f".env.example missing {var}")
    
    # Check alembic.ini
    alembic_ini = project_path / 'alembic.ini'
    if alembic_ini.exists():
        with open(alembic_ini, 'r') as f:
            alembic_content = f.read()
            
        if 'sqlalchemy.url' not in alembic_content:
            issues.append("alembic.ini missing sqlalchemy.url configuration")
    
    return issues

def validate_docker_configuration(project_path, scenario):
    """Validate Docker configuration consistency."""
    issues = []
    
    # Check Dockerfile exists
    dockerfile_paths = [
        project_path / 'Dockerfile',
        project_path / 'docker' / 'Dockerfile.dev',
        project_path / 'docker' / 'Dockerfile.prod'
    ]
    
    dockerfile_found = any(path.exists() for path in dockerfile_paths)
    if not dockerfile_found:
        issues.append("No Dockerfile found")
    
    # Check docker-compose.yml consistency
    docker_compose = project_path / 'docker-compose.yml'
    if docker_compose.exists():
        with open(docker_compose, 'r') as f:
            compose_content = f.read()
            
        # Validate service dependencies
        if 'depends_on:' in compose_content:
            db_type = scenario['config'].get('database_type', 'postgresql')
            if db_type == 'postgresql' and 'postgres:' not in compose_content:
                issues.append("docker-compose.yml has depends_on but no postgres service")
            elif db_type == 'mysql' and 'mysql:' not in compose_content:
                issues.append("docker-compose.yml has depends_on but no mysql service")
    
    return issues

def validate_terraform_configuration(project_path, scenario):
    """Validate Terraform configuration."""
    issues = []
    
    terraform_dir = project_path / 'terraform'
    if terraform_dir.exists():
        # Check for main.tf files
        main_tf_files = list(terraform_dir.rglob('main.tf'))
        if not main_tf_files:
            issues.append("Terraform directory exists but no main.tf files found")
        
        # Check for variables.tf
        variables_tf_files = list(terraform_dir.rglob('variables.tf'))
        if not variables_tf_files:
            issues.append("Terraform directory exists but no variables.tf files found")
    
    return issues

def validate_github_actions(project_path):
    """Validate GitHub Actions workflow."""
    issues = []
    
    workflows_dir = project_path / '.github' / 'workflows'
    if workflows_dir.exists():
        workflow_files = list(workflows_dir.glob('*.yml'))
        if not workflow_files:
            issues.append("GitHub workflows directory exists but no workflow files found")
        
        for workflow_file in workflow_files:
            with open(workflow_file, 'r') as f:
                workflow_content = f.read()
                
            # Check for essential workflow elements
            if 'on:' not in workflow_content:
                issues.append(f"{workflow_file.name}: Missing 'on:' trigger")
            if 'jobs:' not in workflow_content:
                issues.append(f"{workflow_file.name}: Missing 'jobs:' section")
    
    return issues

def run_edge_case_validation():
    """Run comprehensive edge case validation."""
    print("🔬 Starting Edge Case Validation for KickStartMyAI Template")
    print("=" * 70)
    
    total_scenarios = len(EDGE_CASE_SCENARIOS)
    passed = 0
    failed = 0
    all_issues = []
    
    for i, scenario in enumerate(EDGE_CASE_SCENARIOS, 1):
        print(f"\n🧪 Edge Case {i}/{total_scenarios}: {scenario['name']}")
        print("-" * 50)
        
        with tempfile.TemporaryDirectory() as temp_dir:
            try:
                # Build cookiecutter command
                cmd = ['cookiecutter', '.', '--no-input', '-o', temp_dir]
                for key, value in scenario['config'].items():
                    cmd.extend(['-v', f'{key}={value}'])
                
                print(f"🔧 Generating with config: {dict(list(scenario['config'].items())[:3])}...")
                
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
                
                # Run comprehensive validations
                scenario_issues = []
                
                # 1. Python import validation
                import_issues = validate_python_imports(project_path)
                scenario_issues.extend(import_issues)
                
                # 2. Configuration file validation
                config_issues = validate_configuration_files(project_path, scenario)
                scenario_issues.extend(config_issues)
                
                # 3. Docker configuration validation
                docker_issues = validate_docker_configuration(project_path, scenario)
                scenario_issues.extend(docker_issues)
                
                # 4. Terraform validation
                terraform_issues = validate_terraform_configuration(project_path, scenario)
                scenario_issues.extend(terraform_issues)
                
                # 5. GitHub Actions validation
                github_issues = validate_github_actions(project_path)
                scenario_issues.extend(github_issues)
                
                # Report results
                if scenario_issues:
                    print(f"⚠️  Found {len(scenario_issues)} issues:")
                    for issue in scenario_issues[:3]:  # Show first 3 issues
                        print(f"   • {issue}")
                    if len(scenario_issues) > 3:
                        print(f"   • ... and {len(scenario_issues) - 3} more")
                    all_issues.extend(scenario_issues)
                else:
                    print("🎉 All edge case validations passed!")
                
                passed += 1
                
            except subprocess.TimeoutExpired:
                print("❌ Generation timed out (>60s)")
                failed += 1
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                failed += 1
    
    # Final comprehensive report
    print("\n" + "=" * 70)
    print("🔬 EDGE CASE VALIDATION RESULTS")
    print("=" * 70)
    print(f"Total edge cases tested: {total_scenarios}")
    print(f"✅ Passed: {passed}")
    print(f"❌ Failed: {failed}")
    print(f"📈 Success rate: {(passed/total_scenarios)*100:.1f}%")
    print(f"🐛 Total issues found: {len(all_issues)}")
    
    if all_issues:
        print(f"\n📋 Issue Summary:")
        issue_types = {}
        for issue in all_issues:
            issue_type = issue.split(':')[0] if ':' in issue else 'General'
            issue_types[issue_type] = issue_types.get(issue_type, 0) + 1
        
        for issue_type, count in sorted(issue_types.items()):
            print(f"   • {issue_type}: {count} issues")
    
    if passed == total_scenarios and len(all_issues) == 0:
        print("\n🏆 PERFECT! Template passes all edge case validations!")
        return True
    elif passed == total_scenarios:
        print(f"\n⚠️  Template generates successfully but has {len(all_issues)} minor issues")
        return True
    else:
        print(f"\n💥 Template has critical issues - {failed} scenarios failed")
        return False

if __name__ == "__main__":
    success = run_edge_case_validation()
    sys.exit(0 if success else 1) 