
#!/usr/bin/env python3
"""
PostgreSQL Database Initialization Script
This script helps set up the PostgreSQL database for the inventory management system.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import OperationalError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_database():
    """Create the inventory_management database if it doesn't exist"""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    
    if not database_url:
        print("Error: DATABASE_URL not found in environment variables")
        print("Please set up your .env file with the correct DATABASE_URL")
        return False
    
    print(f"Using database URL: {database_url}")
    
    try:
        # Create engine
        engine = create_engine(database_url)
        
        # Test connection
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version();"))
            version = result.fetchone()
            print(f"Successfully connected to PostgreSQL: {version[0]}")
            
        print("Database connection successful!")
        return True
        
    except OperationalError as e:
        print(f"Error connecting to database: {e}")
        print("\nTroubleshooting steps:")
        print("1. Make sure PostgreSQL is running")
        print("2. Check that the database credentials in DATABASE_URL are correct")
        print("3. Ensure the database 'inventory_management' exists")
        print("4. Verify that the user has proper permissions")
        return False
    
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

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
    print("\nStep 1: Testing database connection...")
    if not create_database():
        print("Database connection failed. Please fix the connection issues and try again.")
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
