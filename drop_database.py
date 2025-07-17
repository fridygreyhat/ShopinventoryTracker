
#!/usr/bin/env python3
"""
Complete database removal and recreation script
This will PERMANENTLY DELETE all data in the database
"""

import os
import sys
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def drop_and_recreate_database():
    """Completely drop and recreate the database"""
    # Get database connection details
    db_host = os.environ.get("DB_HOST", "localhost")
    db_user = os.environ.get("DB_USER", "postgres")
    db_password = os.environ.get("DB_PASSWORD", "postgres")
    db_port = os.environ.get("DB_PORT", "5432")
    db_name = os.environ.get("DB_NAME", "inventory_db")

    try:
        # Connect to PostgreSQL server (not to the specific database)
        conn = psycopg2.connect(
            host=db_host,
            user=db_user,
            password=db_password,
            port=db_port,
            database="postgres"  # Connect to default postgres database
        )
        conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
        cursor = conn.cursor()

        print(f"🗑️  Dropping database '{db_name}'...")
        
        # Terminate all connections to the target database
        cursor.execute(f"""
            SELECT pg_terminate_backend(pid)
            FROM pg_stat_activity
            WHERE datname = '{db_name}' AND pid <> pg_backend_pid();
        """)
        
        # Drop the database
        try:
            cursor.execute(f"DROP DATABASE IF EXISTS {db_name};")
            print(f"✅ Database '{db_name}' dropped successfully")
        except Exception as e:
            print(f"⚠️  Error dropping database: {e}")

        # Recreate the database
        try:
            cursor.execute(f"CREATE DATABASE {db_name};")
            print(f"✅ Database '{db_name}' created successfully")
        except Exception as e:
            print(f"❌ Error creating database: {e}")
            return False

        # Grant privileges to user if exists
        try:
            cursor.execute(f"GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};")
            print(f"✅ Privileges granted to user '{db_user}'")
        except Exception as e:
            print(f"⚠️  Warning granting privileges: {e}")

        cursor.close()
        conn.close()

        print("\n🎉 Database completely removed and recreated!")
        print("All data has been permanently deleted.")
        print("\nNext steps:")
        print("1. Run: python repair_database.py")
        print("2. Or run your Flask app to reinitialize tables")
        
        return True

    except Exception as e:
        print(f"❌ Error during database removal: {e}")
        return False

def drop_all_tables_only():
    """Alternative: Drop all tables but keep the database"""
    try:
        from app import app, db
        
        with app.app_context():
            print("🗑️  Dropping all tables...")
            
            # Get all table names
            result = db.session.execute(db.text("""
                SELECT tablename FROM pg_tables 
                WHERE schemaname = 'public'
            """))
            
            tables = [row[0] for row in result.fetchall()]
            
            if tables:
                # Drop all tables
                for table in tables:
                    try:
                        db.session.execute(db.text(f'DROP TABLE IF EXISTS "{table}" CASCADE'))
                        print(f"  ✅ Dropped table: {table}")
                    except Exception as e:
                        print(f"  ⚠️  Error dropping table {table}: {e}")
                
                db.session.commit()
                print("✅ All tables dropped successfully")
            else:
                print("ℹ️  No tables found to drop")
                
            return True
            
    except Exception as e:
        print(f"❌ Error dropping tables: {e}")
        return False

if __name__ == '__main__':
    print("⚠️  WARNING: This will PERMANENTLY DELETE all data!")
    print("Choose an option:")
    print("1. Drop and recreate entire database (recommended)")
    print("2. Drop all tables only (keep database)")
    print("3. Cancel")
    
    choice = input("\nEnter your choice (1/2/3): ").strip()
    
    if choice == "1":
        confirm = input("\nType 'DELETE' to confirm complete database removal: ")
        if confirm == "DELETE":
            drop_and_recreate_database()
        else:
            print("❌ Operation cancelled")
    elif choice == "2":
        confirm = input("\nType 'DROP' to confirm dropping all tables: ")
        if confirm == "DROP":
            drop_all_tables_only()
        else:
            print("❌ Operation cancelled")
    else:
        print("❌ Operation cancelled")
