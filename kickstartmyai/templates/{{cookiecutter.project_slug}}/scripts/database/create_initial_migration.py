"""Create initial database migration for all models."""

import subprocess
import sys
from pathlib import Path

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


def run_command(cmd: str, description: str) -> bool:
    """Run a command and return success status."""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(
            cmd, 
            shell=True, 
            capture_output=True, 
            text=True,
            cwd=Path(__file__).parent.parent.parent
        )
        
        if result.returncode == 0:
            print(f"✅ {description} completed successfully")
            if result.stdout.strip():
                print(f"Output: {result.stdout.strip()}")
            return True
        else:
            print(f"❌ {description} failed")
            print(f"Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"❌ {description} failed with exception: {e}")
        return False


def validate_models_imported():
    """Validate all models are properly imported."""
    print("🔍 Validating model imports...")
    
    try:
        # Import all models to check for issues
        from app.models import (
            User, Conversation, Message, MessageRole,
            Agent, AgentType, AgentStatus, 
            Execution, ExecutionStatus, ExecutionType
        )
        print("✅ All models imported successfully")
        
        # Check that models have proper Base inheritance
        from app.db.base import Base
        
        model_classes = [User, Conversation, Message, Agent, Execution]
        for model_class in model_classes:
            if not issubclass(model_class, Base):
                print(f"❌ {model_class.__name__} does not inherit from Base")
                return False
        
        print("✅ All models inherit from Base correctly")
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Validation error: {e}")
        return False


def check_alembic_setup():
    """Check if Alembic is properly set up."""
    alembic_dir = Path("alembic")
    env_file = alembic_dir / "env.py"
    versions_dir = alembic_dir / "versions"
    
    if not alembic_dir.exists():
        print("❌ Alembic directory not found. Run: alembic init alembic")
        return False
    
    if not env_file.exists():
        print("❌ Alembic env.py not found")
        return False
    
    if not versions_dir.exists():
        print("❌ Alembic versions directory not found")
        return False
    
    print("✅ Alembic setup validated")
    return True


def create_initial_migration():
    """Create the initial migration."""
    print("\n🚀 Creating Initial Database Migration")
    print("=" * 40)
    
    # Step 1: Validate models
    if not validate_models_imported():
        print("❌ Model validation failed. Please fix model imports first.")
        return False
    
    # Step 2: Check Alembic setup
    if not check_alembic_setup():
        print("❌ Alembic setup incomplete. Please initialize Alembic first.")
        return False
    
    # Step 3: Check current migration status
    print("\n📋 Checking current migration status...")
    if not run_command("alembic current", "Check current migration"):
        print("⚠️ No current migration found (expected for initial setup)")
    
    # Step 4: Generate initial migration
    print("\n🔨 Generating initial migration...")
    migration_message = "Initial migration - Create all tables"
    
    if not run_command(
        f'alembic revision --autogenerate -m "{migration_message}"',
        "Generate initial migration"
    ):
        return False
    
    # Step 5: Show generated migration
    versions_dir = Path("alembic/versions")
    migration_files = list(versions_dir.glob("*.py"))
    
    if migration_files:
        latest_migration = max(migration_files, key=lambda x: x.stat().st_mtime)
        print(f"\n📄 Generated migration file: {latest_migration.name}")
        
        # Show first few lines of the migration
        try:
            with open(latest_migration, 'r') as f:
                lines = f.readlines()[:20]
            print("\n📝 Migration preview (first 20 lines):")
            print("-" * 40)
            for i, line in enumerate(lines, 1):
                print(f"{i:2d}: {line.rstrip()}")
            print("-" * 40)
        except Exception as e:
            print(f"⚠️ Could not preview migration: {e}")
    
    print("\n✅ Initial migration created successfully!")
    print("\n📋 Next steps:")
    print("1. Review the generated migration file")
    print("2. Run: alembic upgrade head")
    print("3. Or run: make db-upgrade")
    
    return True


if __name__ == "__main__":
    success = create_initial_migration()
    sys.exit(0 if success else 1)
