#!/usr/bin/env python3
"""
Database creation script for Test AI Project
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine
from app.core.config import settings


def create_database():
    """Create the database and user if they don't exist."""
    
    # Connection parameters for the default postgres database
    conn_params = {
        'host': settings.POSTGRES_SERVER,
        'port': settings.POSTGRES_PORT,
        'user': 'postgres',  # Default admin user
        'password': os.getenv('POSTGRES_ADMIN_PASSWORD', 'postgres'),
        'database': 'postgres'
    }
    
    try:
        # Connect to PostgreSQL server
        print(f"Connecting to PostgreSQL server at {settings.POSTGRES_SERVER}:{settings.POSTGRES_PORT}")
        conn = psycopg2.connect(**conn_params)
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()
        
        # Create user if not exists
        print(f"Creating user '{settings.POSTGRES_USER}' if not exists...")
        cursor.execute(f"""
            DO $$
            BEGIN
                IF NOT EXISTS (SELECT FROM pg_catalog.pg_user WHERE usename = '{settings.POSTGRES_USER}') THEN
                    CREATE USER {settings.POSTGRES_USER} WITH PASSWORD '{settings.POSTGRES_PASSWORD}';
                END IF;
            END
            $$;
        """)
        
        # Create database if not exists
        print(f"Creating database '{settings.POSTGRES_DB}' if not exists...")
        cursor.execute(f"""
            SELECT 1 FROM pg_catalog.pg_database WHERE datname = '{settings.POSTGRES_DB}'
        """)
        exists = cursor.fetchone()
        
        if not exists:
            cursor.execute(f"CREATE DATABASE {settings.POSTGRES_DB} OWNER {settings.POSTGRES_USER}")
            print(f"Database '{settings.POSTGRES_DB}' created successfully!")
        else:
            print(f"Database '{settings.POSTGRES_DB}' already exists.")
        
        # Grant privileges
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {settings.POSTGRES_DB} TO {settings.POSTGRES_USER}")
        
        cursor.close()
        conn.close()
        
        print("Database setup completed successfully!")
        
    except psycopg2.Error as e:
        print(f"Error creating database: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)


def test_connection():
    """Test the database connection with the application settings."""
    try:
        print("Testing database connection...")
        engine = create_engine(settings.DATABASE_URL)
        with engine.connect() as conn:
            result = conn.execute("SELECT version()")
            version = result.fetchone()[0]
            print(f"Successfully connected to: {version}")
        
    except Exception as e:
        print(f"Connection test failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    create_database()
    test_connection()
    print("\n✅ Database is ready for use!")
    print(f"Connection string: {settings.DATABASE_URL}")
