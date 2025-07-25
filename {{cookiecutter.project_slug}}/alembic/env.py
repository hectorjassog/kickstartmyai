"""Alembic environment configuration for async database migrations."""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

# Import the Base class and all models to ensure they are registered
from app.db.base import Base, metadata
from app.models import (  # noqa: F401
    User,
    Agent,
    Conversation, 
    Message,
    Execution
)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def get_database_url():
    """Get database URL from environment variables."""
    # First try to get the full DATABASE_URL
    database_url = os.getenv("DATABASE_URL")
    
    if database_url:
        return database_url
    
    # If not available, build from individual components
    postgres_server = os.getenv("POSTGRES_SERVER", "localhost")
    postgres_user = os.getenv("POSTGRES_USER", "{{cookiecutter.database_user}}")
    postgres_password = os.getenv("POSTGRES_PASSWORD", "password")
    postgres_db = os.getenv("POSTGRES_DB", "{{cookiecutter.database_name}}")
    postgres_port = os.getenv("POSTGRES_PORT", "5432")
    
    return f"postgresql://{postgres_user}:{postgres_password}@{postgres_server}:{postgres_port}/{postgres_db}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the given connection."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    # Get database URL from environment
    database_url = get_database_url()
    
    # Set the database URL in the configuration
    config.set_main_option("sqlalchemy.url", database_url)
    
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)

    await connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online() 