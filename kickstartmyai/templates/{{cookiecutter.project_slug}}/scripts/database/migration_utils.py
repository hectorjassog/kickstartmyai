"""Python utilities for database migrations."""

import asyncio
import sys
from pathlib import Path
from typing import List, Optional

# Add app to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings


class MigrationUtils:
    """Utility class for database migration operations."""
    
    def __init__(self):
        self.engine = create_async_engine(
            str(settings.DATABASE_URL),
            echo=False,
        )
    
    async def get_current_revision(self) -> Optional[str]:
        """Get the current database revision."""
        try:
            async with self.engine.connect() as conn:
                result = await conn.execute(
                    text("SELECT version_num FROM alembic_version LIMIT 1")
                )
                row = result.fetchone()
                return row[0] if row else None
        except Exception:
            return None
    
    async def check_migration_status(self) -> dict:
        """Check if migrations need to be applied."""
        current_rev = await self.get_current_revision()
        
        # Simple check - in a real app you'd compare with alembic heads
        status = {
            "current_revision": current_rev,
            "needs_migration": current_rev is None,
            "is_initialized": current_rev is not None
        }
        
        return status
    
    async def list_tables(self) -> List[str]:
        """List all tables in the database."""
        async with self.engine.connect() as conn:
            if "postgresql" in str(settings.DATABASE_URL):
                result = await conn.execute(
                    text("""
                        SELECT tablename 
                        FROM pg_tables 
                        WHERE schemaname = 'public'
                        ORDER BY tablename
                    """)
                )
            else:
                # SQLite
                result = await conn.execute(
                    text("""
                        SELECT name 
                        FROM sqlite_master 
                        WHERE type='table' 
                        ORDER BY name
                    """)
                )
            
            return [row[0] for row in result.fetchall()]
    
    async def table_exists(self, table_name: str) -> bool:
        """Check if a table exists."""
        tables = await self.list_tables()
        return table_name in tables
    
    async def count_records(self, table_name: str) -> int:
        """Count records in a table."""
        async with self.engine.connect() as conn:
            result = await conn.execute(
                text(f"SELECT COUNT(*) FROM {table_name}")
            )
            return result.scalar()
    
    async def database_info(self) -> dict:
        """Get comprehensive database information."""
        tables = await self.list_tables()
        current_rev = await self.get_current_revision()
        
        table_info = {}
        for table in tables:
            if table != 'alembic_version':
                table_info[table] = await self.count_records(table)
        
        return {
            "current_revision": current_rev,
            "total_tables": len(tables),
            "tables": table_info,
            "database_url": str(settings.DATABASE_URL).split('@')[1] if '@' in str(settings.DATABASE_URL) else "local"
        }
    
    async def close(self):
        """Close the database connection."""
        await self.engine.dispose()


async def main():
    """Command line interface for migration utilities."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Migration utilities")
    parser.add_argument(
        "command",
        choices=["status", "info", "tables", "check-table"],
        help="Command to run"
    )
    parser.add_argument("--table", help="Table name for check-table command")
    
    args = parser.parse_args()
    
    utils = MigrationUtils()
    
    try:
        if args.command == "status":
            status = await utils.check_migration_status()
            print(f"Current revision: {status['current_revision']}")
            print(f"Needs migration: {status['needs_migration']}")
            print(f"Database initialized: {status['is_initialized']}")
        
        elif args.command == "info":
            info = await utils.database_info()
            print(f"Database: {info['database_url']}")
            print(f"Current revision: {info['current_revision']}")
            print(f"Total tables: {info['total_tables']}")
            print("\nTable record counts:")
            for table, count in info['tables'].items():
                print(f"  {table}: {count} records")
        
        elif args.command == "tables":
            tables = await utils.list_tables()
            print("Database tables:")
            for table in tables:
                print(f"  - {table}")
        
        elif args.command == "check-table":
            if not args.table:
                print("Error: --table argument required")
                return
            
            exists = await utils.table_exists(args.table)
            if exists:
                count = await utils.count_records(args.table)
                print(f"Table '{args.table}' exists with {count} records")
            else:
                print(f"Table '{args.table}' does not exist")
    
    finally:
        await utils.close()


if __name__ == "__main__":
    asyncio.run(main())
