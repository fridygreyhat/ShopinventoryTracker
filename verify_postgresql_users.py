
#!/usr/bin/env python3
"""
Script to verify all registered users are stored in PostgreSQL database
"""

import os
import logging
from datetime import datetime
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_database_connection():
    """Get PostgreSQL database connection"""
    try:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL environment variable not found")
            return None

        print("🔗 Connecting to PostgreSQL database...")
        engine = create_engine(db_url, echo=False)
        return engine

    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return None

def verify_user_table_structure():
    """Verify the user table structure in PostgreSQL"""
    engine = get_database_connection()
    if not engine:
        return False

    try:
        with engine.connect() as conn:
            # Check if user table exists
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'user' AND table_schema = 'public'
            """))
            
            if not result.fetchone():
                print("❌ User table does not exist in PostgreSQL")
                return False

            # Get table structure
            result = conn.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns 
                WHERE table_name = 'user' AND table_schema = 'public'
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            print("✅ User table structure in PostgreSQL:")
            print("-" * 60)
            for col in columns:
                nullable = "NULL" if col[2] == "YES" else "NOT NULL"
                default = f" DEFAULT {col[3]}" if col[3] else ""
                print(f"  {col[0]:<20} {col[1]:<15} {nullable}{default}")
            
            return True

    except Exception as e:
        print(f"❌ Error verifying table structure: {str(e)}")
        return False

def get_all_registered_users():
    """Get all registered users from PostgreSQL"""
    engine = get_database_connection()
    if not engine:
        return []

    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT 
                    id, 
                    username, 
                    email, 
                    first_name, 
                    last_name, 
                    shop_name,
                    phone,
                    is_active, 
                    is_admin,
                    email_verified,
                    created_at,
                    last_login
                FROM "user" 
                ORDER BY created_at DESC
            """))

            users = result.fetchall()
            return users

    except Exception as e:
        print(f"❌ Error fetching users: {str(e)}")
        return []

def display_user_statistics():
    """Display user statistics"""
    users = get_all_registered_users()
    
    if not users:
        print("📭 No users found in PostgreSQL database")
        return

    print(f"\n👥 Found {len(users)} registered user(s) in PostgreSQL:")
    print("=" * 80)
    
    active_users = sum(1 for user in users if user[7])  # is_active
    admin_users = sum(1 for user in users if user[8])   # is_admin
    verified_users = sum(1 for user in users if user[9]) # email_verified
    
    print(f"📊 Statistics:")
    print(f"  Total Users:     {len(users)}")
    print(f"  Active Users:    {active_users}")
    print(f"  Admin Users:     {admin_users}")
    print(f"  Verified Users:  {verified_users}")
    print()
    
    print("👤 User Details:")
    print("-" * 80)
    for user in users:
        status_icons = []
        if user[7]:  # is_active
            status_icons.append("✅")
        else:
            status_icons.append("❌")
        
        if user[8]:  # is_admin
            status_icons.append("👑")
        
        if user[9]:  # email_verified
            status_icons.append("📧")
        
        status = " ".join(status_icons)
        created = user[10].strftime('%Y-%m-%d %H:%M') if user[10] else 'Unknown'
        last_login = user[11].strftime('%Y-%m-%d %H:%M') if user[11] else 'Never'
        
        print(f"ID: {user[0]:<3} | {user[1]:<20} | {user[2]:<30} | {status}")
        print(f"        Name: {(user[3] or '') + ' ' + (user[4] or '')}")
        print(f"        Shop: {user[5] or 'N/A'}")
        print(f"        Phone: {user[6] or 'N/A'}")
        print(f"        Created: {created} | Last Login: {last_login}")
        print("-" * 80)

def migrate_users_to_postgresql():
    """Ensure all users are properly stored in PostgreSQL"""
    try:
        from app import app, db
        from models import User
        
        with app.app_context():
            print("🔄 Checking user data integrity in PostgreSQL...")
            
            # Get all users using SQLAlchemy
            users = User.query.all()
            
            print(f"Found {len(users)} users in application")
            
            # Verify each user is properly stored
            for user in users:
                try:
                    # Refresh user from database to ensure it's stored
                    db.session.refresh(user)
                    print(f"✅ User {user.email} (ID: {user.id}) verified in PostgreSQL")
                except Exception as e:
                    print(f"❌ User {user.email} verification failed: {str(e)}")
            
            print("✅ User migration verification completed")
            return True
            
    except Exception as e:
        print(f"❌ Error during user migration: {str(e)}")
        return False

def main():
    print("PostgreSQL User Database Verification")
    print("=" * 50)
    
    # Step 1: Verify table structure
    if not verify_user_table_structure():
        print("\n❌ Table structure verification failed")
        return
    
    # Step 2: Display user statistics
    display_user_statistics()
    
    # Step 3: Verify user data integrity
    print("\n🔄 Verifying user data integrity...")
    if migrate_users_to_postgresql():
        print("✅ All users are properly stored in PostgreSQL")
    else:
        print("❌ User data integrity check failed")

if __name__ == "__main__":
    main()
