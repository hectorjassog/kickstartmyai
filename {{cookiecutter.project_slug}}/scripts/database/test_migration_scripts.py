#!/usr/bin/env python3
"""Quick test of migration scripts functionality."""

import subprocess
import sys
from pathlib import Path

def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"🔄 Testing: {description}")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=Path(__file__).parent.parent
        )
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            return True
        else:
            print(f"❌ {description} - FAILED")
            print(f"Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ {description} - EXCEPTION: {e}")
        return False

def main():
    """Test migration scripts."""
    print("🧪 Testing Migration Scripts")
    print("=" * 40)
    
    tests = [
        ("./scripts/database/migrate.sh help", "Migration script help"),
        ("python scripts/database/validate_models.py --help", "Model validator help"),
        ("python scripts/database/migration_utils.py --help", "Migration utils help"),
        ("python scripts/database/create_initial_migration.py --help", "Initial migration help"),
    ]
    
    passed = 0
    failed = 0
    
    for cmd, description in tests:
        if run_command(cmd, description):
            passed += 1
        else:
            failed += 1
    
    print(f"\n📊 Test Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All migration scripts are properly configured!")
        return 0
    else:
        print("⚠️ Some migration scripts have issues.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
