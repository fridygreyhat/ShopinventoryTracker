#!/usr/bin/env python3
"""
Script to check all registered users in the PostgreSQL database
"""

import os
import logging
from sqlalchemy import create_engine, text
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
                    last_login
                FROM "user" 
                ORDER BY created_at DESC
            """))

            users = result.fetchall()

            if not users:
                print("📭 No users found in the database.")
                print("Users can register at: /register")
                return True

            print(f"👥 Found {len(users)} registered user(s):")
            print("=" * 100)

            for i, user in enumerate(users, 1):
                print(f"\n🧑‍💼 User #{i}")
                print(f"   ID: {user.id}")
                print(f"   Username: {user.username}")
                print(f"   Email: {user.email}")
                print(f"   Name: {user.first_name or 'N/A'} {user.last_name or 'N/A'}")
                print(f"   Shop: {user.shop_name or 'N/A'}")
                print(f"   Phone: {user.phone or 'N/A'}")
                print(f"   Status: {'🟢 Active' if user.is_active else '🔴 Inactive'}")
                print(f"   Admin: {'👑 Yes' if user.is_admin else '👤 No'}")
                print(f"   Email Verified: {'✅ Yes' if user.email_verified else '❌ No'}")
                print(f"   Registered: {user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'N/A'}")
                print(f"   Last Login: {user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'}")
                print("-" * 50)

            # Summary statistics
            active_users = sum(1 for user in users if user.is_active)
            admin_users = sum(1 for user in users if user.is_admin)
            verified_users = sum(1 for user in users if user.email_verified)

            print(f"\n📊 Summary:")
            print(f"   Total Users: {len(users)}")
            print(f"   Active Users: {active_users}")
            print(f"   Admin Users: {admin_users}")
            print(f"   Verified Users: {verified_users}")

            return True

    except Exception as e:
        print(f"❌ Error checking users: {str(e)}")
        return False

def main():
    """Main function"""
    print("🔍 Checking registered users in PostgreSQL database...\n")

    if not check_database_connection():
        return

    if not check_all_users():
        print("\n❌ Failed to check users")
        return

    print("\n✅ User check completed successfully!")

if __name__ == "__main__":
    main()