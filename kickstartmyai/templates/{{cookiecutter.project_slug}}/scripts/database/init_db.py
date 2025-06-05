#!/usr/bin/env python3
"""
Database initialization script.

This script initializes the database and creates the initial migration.
Run this after setting up your .env file with proper database credentials.
"""

import asyncio
import os
import sys
import subprocess
from pathlib import Path

# Add the app directory to the Python path
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

from app.core.config import settings
from app.db.base import init_db, check_db_connection


async def check_database_connection():
    """Check if we can connect to the database."""
    print("🔍 Checking database connection...")
    
    try:
        connection_ok = await check_db_connection()
        if connection_ok:
            print("✅ Database connection successful!")
            return True
        else:
            print("❌ Database connection failed!")
            return False
    except Exception as e:
        print(f"❌ Database connection error: {e}")
        return False


def run_alembic_command(command_args):
    """Run an alembic command."""
    try:
        cmd = ["alembic"] + command_args
        print(f"🚀 Running: {' '.join(cmd)}")
        
        result = subprocess.run(
            cmd,
            cwd=project_root,
            capture_output=True,
            text=True,
            check=True
        )
        
        if result.stdout:
            print(result.stdout)
        
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Alembic command failed: {e}")
        if e.stdout:
            print("STDOUT:", e.stdout)
        if e.stderr:
            print("STDERR:", e.stderr)
        return False
    except FileNotFoundError:
        print("❌ Alembic not found. Please install it with: pip install alembic")
        return False


def create_initial_migration():
    """Create the initial database migration."""
    print("📝 Creating initial database migration...")
    
    # Check if there are already migrations
    versions_dir = project_root / "alembic" / "versions"
    if versions_dir.exists() and any(versions_dir.glob("*.py")):
        print("⚠️  Migrations already exist. Skipping initial migration creation.")
        return True
    
    # Create initial migration
    return run_alembic_command([
        "revision", 
        "--autogenerate", 
        "-m", 
        "Initial migration"
    ])


def upgrade_database():
    """Upgrade the database to the latest migration."""
    print("⬆️  Upgrading database to latest migration...")
    return run_alembic_command(["upgrade", "head"])


async def initialize_database():
    """Initialize the database with tables."""
    print("🏗️  Initializing database tables...")
    
    try:
        await init_db()
        print("✅ Database tables initialized successfully!")
        return True
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        return False


def check_environment():
    """Check if environment is properly configured."""
    print("🔧 Checking environment configuration...")
    
    required_vars = [
        "SECRET_KEY",
        "POSTGRES_PASSWORD"
    ]
    
    missing_vars = []
    for var in required_vars:
        if not getattr(settings, var, None):
            missing_vars.append(var)
    
    if missing_vars:
        print(f"❌ Missing required environment variables: {', '.join(missing_vars)}")
        print("💡 Please set these in your .env file")
        return False
    
    print("✅ Environment configuration looks good!")
    return True


async def main():
    """Main initialization function."""
    print("🚀 KickStartMyAI Database Initialization")
    print("=" * 50)
    
    # Check environment configuration
    if not check_environment():
        print("\n❌ Please fix your environment configuration and try again.")
        sys.exit(1)
    
    # Check database connection
    if not await check_database_connection():
        print("\n❌ Please check your database configuration and ensure the database server is running.")
        sys.exit(1)
    
    # Create initial migration
    if not create_initial_migration():
        print("\n❌ Failed to create initial migration.")
        sys.exit(1)
    
    # Run database migrations
    if not upgrade_database():
        print("\n❌ Failed to upgrade database.")
        sys.exit(1)
    
    print("\n🎉 Database initialization completed successfully!")
    print("🔥 Your KickStartMyAI application is ready to use!")
    
    print("\n📋 Next steps:")
    print("1. Start the application: uvicorn app.main:app --reload")
    print("2. Visit the API docs: http://localhost:8000/docs")
    print("3. Create your first user and start building!")


if __name__ == "__main__":
    asyncio.run(main()) 