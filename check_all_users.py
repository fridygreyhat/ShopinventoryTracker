
#!/usr/bin/env python3
"""
Script to check and display all registered users in PostgreSQL database
"""

import os
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
import sys

# Load environment variables
load_dotenv()

def check_all_users():
    """Check all registered users in the PostgreSQL database"""
    try:
        # Get database URL from environment variables
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            print("ERROR: DATABASE_URL not found in environment variables")
            print("Make sure you have set up the PostgreSQL database in Replit")
            return False
        
        print(f"Connecting to database...")
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            # Check if user table exists
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_name = 'user' AND table_schema = 'public'
            """))
            
            if not result.fetchone():
                print("❌ User table does not exist in the database.")
                print("Run the Flask app first to create tables: python main.py")
                return False
            
            print("✅ User table found. Checking for registered users...\n")
            
            # Get all users with detailed information
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
                    last_login,
                    password_hash
                FROM "user" 
                ORDER BY created_at DESC
            """))
            
            users = result.fetchall()
            
            if not users:
                print("❌ No users found in the database.")
                print("Try registering a new user through the web interface.")
                return False
            
            print(f"✅ Found {len(users)} registered user(s):")
            print("=" * 120)
            print(f"{'ID':<4} {'Username':<15} {'Email':<30} {'Name':<25} {'Shop':<20} {'Active':<8} {'Admin':<7} {'Verified':<10} {'Created':<20}")
            print("=" * 120)
            
            for user in users:
                id_val, username, email, first_name, last_name, shop_name, phone, is_active, is_admin, email_verified, created_at, last_login, password_hash = user
                
                full_name = f"{first_name or ''} {last_name or ''}".strip() or "N/A"
                shop_display = shop_name[:17] + "..." if shop_name and len(shop_name) > 20 else (shop_name or "N/A")
                created_display = created_at.strftime('%Y-%m-%d %H:%M') if created_at else "N/A"
                
                print(f"{id_val:<4} {username:<15} {email:<30} {full_name:<25} {shop_display:<20} {'Yes' if is_active else 'No':<8} {'Yes' if is_admin else 'No':<7} {'Yes' if email_verified else 'No':<10} {created_display:<20}")
            
            print("=" * 120)
            
            # Additional statistics
            active_users = sum(1 for user in users if user[7])  # is_active
            admin_users = sum(1 for user in users if user[8])   # is_admin
            verified_users = sum(1 for user in users if user[9])  # email_verified
            
            print(f"\n📊 User Statistics:")
            print(f"   Total users: {len(users)}")
            print(f"   Active users: {active_users}")
            print(f"   Admin users: {admin_users}")
            print(f"   Verified emails: {verified_users}")
            
            # Check for users with password issues
            users_without_password = sum(1 for user in users if not user[12])  # password_hash
            if users_without_password > 0:
                print(f"   ⚠️  Users without password hash: {users_without_password}")
            
            return True
            
    except Exception as e:
        print(f"❌ Error checking users: {str(e)}")
        print(f"   Database URL: {db_url[:50]}...")
        return False

def check_database_connection():
    """Test basic database connection"""
    try:
        db_url = os.environ.get("DATABASE_URL")
        if not db_url:
            print("❌ DATABASE_URL environment variable not found")
            return False
        
        print("🔗 Testing database connection...")
        engine = create_engine(db_url)
        
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            print(f"✅ Database connection successful!")
            print(f"   PostgreSQL version: {version.split(',')[0]}")
            
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def main():
    """Main function"""
    print("🔍 PostgreSQL User Registry Checker")
    print("=" * 50)
    
    # Test database connection first
    if not check_database_connection():
        print("\n💡 Troubleshooting tips:")
        print("   1. Make sure you have created a PostgreSQL database in Replit")
        print("   2. Check that DATABASE_URL is set in your environment variables")
        print("   3. Ensure your Flask app has run at least once to create tables")
        return
    
    print()
    
    # Check all users
    if check_all_users():
        print(f"\n✅ User check completed successfully!")
    else:
        print(f"\n❌ User check failed. Please check the errors above.")
        print("\n💡 If you're having login issues:")
        print("   1. Check that users have valid password hashes")
        print("   2. Ensure user accounts are active (is_active = true)")
        print("   3. Try registering a new user to test the registration flow")

if __name__ == "__main__":
    main()
