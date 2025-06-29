#!/usr/bin/env python3
"""
PostgreSQL Database Initialization Script
This script helps set up the PostgreSQL database for the inventory management system.
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_database():
    """Create PostgreSQL database if it doesn't exist"""
    # Get database URL from environment variables
    db_host = os.environ.get("DB_HOST", "localhost")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "postgres")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "inventory_db")

    try:
        # Connect to PostgreSQL server (not to a specific database)
        conn = psycopg2.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            port=db_port
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        # Create database if it doesn't exist
        try:
            cursor.execute(f"CREATE DATABASE {db_name};")
            print(f"Database '{db_name}' created successfully")
        except psycopg2.errors.DuplicateDatabase:
            print(f"Database '{db_name}' already exists")

        # Create user if it doesn't exist
        try:
            cursor.execute("CREATE USER inventory WITH PASSWORD 'password';")
            print("User 'inventory' created successfully")
        except psycopg2.errors.DuplicateObject:
            print("User 'inventory' already exists")

        # Grant privileges
        cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO inventory;")
        print("Privileges granted to user 'inventory'")

        cursor.close()
        conn.close()

    except Exception as e:
        print(f"Error creating database: {e}")
        return False
    return True

def setup_database_schema():
    """Initialize database tables using Flask app context"""
    try:
        # Import app to get database context
        from app import app, db

        with app.app_context():
            print("Creating database tables...")

            # Create all tables
            db.create_all()

            print("Database tables created successfully!")

            # Check if tables were created
            from sqlalchemy import text
            result = db.session.execute(text("""
                SELECT table_name
                FROM information_schema.tables
                WHERE table_schema = 'public'
                ORDER BY table_name;
            """))

            tables = [row[0] for row in result.fetchall()]
            print(f"Created tables: {', '.join(tables)}")

            return True

    except Exception as e:
        print(f"Error setting up database schema: {e}")
        return False

def main():
    print("PostgreSQL Database Setup for Inventory Management System")
    print("=" * 60)

    # Step 1: Test database connection
    print("\nStep 1: Creating and testing database connection...")
    if not create_database():
        print("Database creation/connection failed. Please fix the connection issues and try again.")
        sys.exit(1)

    # Step 2: Setup database schema
    print("\nStep 2: Setting up database schema...")
    if not setup_database_schema():
        print("Schema setup failed. Please check the errors above.")
        sys.exit(1)

    print("\n" + "=" * 60)
    print("Database setup completed successfully!")
    print("You can now run your Flask application with PostgreSQL.")
    print("Run: python main.py")

if __name__ == "__main__":
    main()