
#!/usr/bin/env python3
"""
Script to check and manage users in PostgreSQL database
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import psycopg2

# Load environment variables
load_dotenv()

def get_database_connection():
    """Get database connection using environment variables"""
    db_url = os.environ.get("DATABASE_URL")
    if not db_url:
        print("ERROR: DATABASE_URL not found in environment variables")
        return None
    
    try:
        engine = create_engine(db_url)
        return engine
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None

def check_users():
    """Check all registered users in the database"""
    engine = get_database_connection()
    if not engine:
        return
    
    try:
        with engine.connect() as conn:
            # Check if user table exists
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'user' AND table_schema = 'public'
            """))
            
            if not result.fetchone():
                print("User table does not exist. Creating tables...")
                # Import and create tables
                from app import app, db
                with app.app_context():
                    db.create_all()
                    print("Tables created successfully!")
                return
            
            # Get all users
            result = conn.execute(text("""
                SELECT id, username, email, first_name, last_name, shop_name, 
                       is_active, is_admin, email_verified, created_at, last_login
                FROM "user" 
                ORDER BY created_at DESC
            """))
            
            users = result.fetchall()
            
            if not users:
                print("No users found in the database.")
                return
            
            print(f"\nFound {len(users)} user(s) in the database:")
            print("-" * 80)
            print(f"{'ID':<5} {'Username':<15} {'Email':<25} {'Name':<20} {'Admin':<7} {'Active':<8} {'Verified':<10}")
            print("-" * 80)
            
            for user in users:
                id_val, username, email, first_name, last_name, shop_name, is_active, is_admin, email_verified, created_at, last_login = user
                full_name = f"{first_name or ''} {last_name or ''}".strip() or "N/A"
                print(f"{id_val:<5} {username:<15} {email:<25} {full_name:<20} {'Yes' if is_admin else 'No':<7} {'Yes' if is_active else 'No':<8} {'Yes' if email_verified else 'No':<10}")
            
            print("-" * 80)
            
    except Exception as e:
        print(f"Error checking users: {e}")

def delete_all_users():
    """Delete all users from the database"""
    engine = get_database_connection()
    if not engine:
        return
    
    try:
        with engine.connect() as conn:
            # First check if there are any users
            result = conn.execute(text('SELECT COUNT(*) FROM "user"'))
            user_count = result.scalar()
            
            if user_count == 0:
                print("No users to delete.")
                return
            
            print(f"Found {user_count} user(s) in the database.")
            confirm = input("Are you sure you want to delete ALL users? (type 'DELETE ALL' to confirm): ")
            
            if confirm == "DELETE ALL":
                # Delete all users
                conn.execute(text('DELETE FROM "user"'))
                conn.commit()
                print(f"Successfully deleted all {user_count} users from the database.")
            else:
                print("Operation cancelled.")
                
    except Exception as e:
        print(f"Error deleting users: {e}")

def delete_specific_user():
    """Delete a specific user by ID or email"""
    engine = get_database_connection()
    if not engine:
        return
    
    try:
        with engine.connect() as conn:
            identifier = input("Enter user ID or email to delete: ").strip()
            
            if not identifier:
                print("No identifier provided.")
                return
            
            # Check if identifier is numeric (ID) or email
            if identifier.isdigit():
                # Delete by ID
                result = conn.execute(text('SELECT username, email FROM "user" WHERE id = :id'), {'id': int(identifier)})
            else:
                # Delete by email
                result = conn.execute(text('SELECT username, email FROM "user" WHERE email = :email'), {'email': identifier})
            
            user = result.fetchone()
            
            if not user:
                print("User not found.")
                return
            
            username, email = user
            confirm = input(f"Are you sure you want to delete user '{username}' ({email})? (y/N): ")
            
            if confirm.lower() == 'y':
                if identifier.isdigit():
                    conn.execute(text('DELETE FROM "user" WHERE id = :id'), {'id': int(identifier)})
                else:
                    conn.execute(text('DELETE FROM "user" WHERE email = :email'), {'email': identifier})
                
                conn.commit()
                print(f"Successfully deleted user '{username}' ({email}).")
            else:
                print("Operation cancelled.")
                
    except Exception as e:
        print(f"Error deleting user: {e}")

def main():
    """Main function"""
    print("PostgreSQL User Management Tool")
    print("=" * 40)
    
    while True:
        print("\nOptions:")
        print("1. Check all users")
        print("2. Delete all users")
        print("3. Delete specific user")
        print("4. Exit")
        
        choice = input("\nEnter your choice (1-4): ").strip()
        
        if choice == "1":
            check_users()
        elif choice == "2":
            delete_all_users()
        elif choice == "3":
            delete_specific_user()
        elif choice == "4":
            print("Goodbye!")
            break
        else:
            print("Invalid choice. Please try again.")

if __name__ == "__main__":
    main()
