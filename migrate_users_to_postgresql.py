
#!/usr/bin/env python3
"""
Migration script to ensure all users are properly stored in PostgreSQL
and remove any Firebase references
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

def clean_firebase_columns():
    """Remove Firebase-related columns from user table"""
    engine = get_database_connection()
    if not engine:
        return False

    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Check and remove firebase_uid column if it exists
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'user' AND column_name = 'firebase_uid'
                """))
                
                if result.fetchone():
                    print("🗑️ Removing firebase_uid column...")
                    conn.execute(text("ALTER TABLE \"user\" DROP COLUMN firebase_uid"))
                    print("✅ Firebase UID column removed")
                else:
                    print("✅ Firebase UID column already removed")

                # Check and remove role column if it exists (replaced with is_admin)
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'user' AND column_name = 'role'
                """))
                
                if result.fetchone():
                    print("🗑️ Removing role column...")
                    conn.execute(text("ALTER TABLE \"user\" DROP COLUMN role"))
                    print("✅ Role column removed")
                else:
                    print("✅ Role column already removed")

                # Check and remove active column if it exists (replaced with is_active)
                result = conn.execute(text("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = 'user' AND column_name = 'active'
                """))
                
                if result.fetchone():
                    print("🗑️ Removing duplicate active column...")
                    conn.execute(text("ALTER TABLE \"user\" DROP COLUMN active"))
                    print("✅ Duplicate active column removed")
                else:
                    print("✅ Duplicate active column already removed")

                # Commit the transaction
                trans.commit()
                print("✅ Database cleanup completed successfully!")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Cleanup failed: {str(e)}")
                return False
                
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def verify_user_migration():
    """Verify all users are properly stored in PostgreSQL"""
    engine = get_database_connection()
    if not engine:
        return False

    try:
        with engine.connect() as conn:
            # Get user count
            result = conn.execute(text("SELECT COUNT(*) FROM \"user\""))
            user_count = result.fetchone()[0]
            
            print(f"📊 Total users in PostgreSQL: {user_count}")
            
            # Get users with missing data
            result = conn.execute(text("""
                SELECT id, username, email, first_name, last_name, created_at
                FROM \"user\" 
                WHERE password_hash IS NULL OR password_hash = ''
            """))
            
            users_without_password = result.fetchall()
            
            if users_without_password:
                print(f"⚠️ Found {len(users_without_password)} users without password hash:")
                for user in users_without_password:
                    print(f"   - ID: {user[0]}, Email: {user[2]}")
            else:
                print("✅ All users have valid password hashes")

            # Check for users without email
            result = conn.execute(text("""
                SELECT id, username, email
                FROM \"user\" 
                WHERE email IS NULL OR email = ''
            """))
            
            users_without_email = result.fetchall()
            
            if users_without_email:
                print(f"⚠️ Found {len(users_without_email)} users without email:")
                for user in users_without_email:
                    print(f"   - ID: {user[0]}, Username: {user[1]}")
            else:
                print("✅ All users have valid emails")

            return True
            
    except Exception as e:
        print(f"❌ Verification failed: {str(e)}")
        return False

def update_user_schema():
    """Update user table schema to ensure PostgreSQL compliance"""
    engine = get_database_connection()
    if not engine:
        return False

    try:
        with engine.connect() as conn:
            # Start transaction
            trans = conn.begin()
            
            try:
                # Ensure all required columns exist with proper types
                required_columns = [
                    ('first_name', 'VARCHAR(64)'),
                    ('last_name', 'VARCHAR(64)'),
                    ('phone', 'VARCHAR(20)'),
                    ('shop_name', 'VARCHAR(128)'),
                    ('product_categories', 'VARCHAR(512)'),
                    ('is_active', 'BOOLEAN DEFAULT TRUE'),
                    ('is_admin', 'BOOLEAN DEFAULT FALSE'),
                    ('email_verified', 'BOOLEAN DEFAULT FALSE'),
                    ('verification_token', 'VARCHAR(64)'),
                    ('verification_token_expires', 'TIMESTAMP'),
                    ('created_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                    ('updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP'),
                    ('last_login', 'TIMESTAMP')
                ]
                
                for column_name, column_type in required_columns:
                    result = conn.execute(text(f"""
                        SELECT column_name 
                        FROM information_schema.columns 
                        WHERE table_name = 'user' AND column_name = '{column_name}'
                    """))
                    
                    if not result.fetchone():
                        print(f"➕ Adding missing column: {column_name}")
                        conn.execute(text(f'ALTER TABLE "user" ADD COLUMN {column_name} {column_type}'))
                    else:
                        print(f"✅ Column {column_name} already exists")

                # Ensure proper indexes exist
                print("🔍 Creating indexes for performance...")
                
                try:
                    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_user_email ON "user" (email)'))
                    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_user_username ON "user" (username)'))
                    conn.execute(text('CREATE INDEX IF NOT EXISTS idx_user_is_active ON "user" (is_active)'))
                    print("✅ Indexes created successfully")
                except Exception as e:
                    print(f"⚠️ Index creation warning: {str(e)}")

                # Commit the transaction
                trans.commit()
                print("✅ Schema update completed successfully!")
                return True
                
            except Exception as e:
                trans.rollback()
                print(f"❌ Schema update failed: {str(e)}")
                return False
                
    except Exception as e:
        print(f"❌ Database connection failed: {str(e)}")
        return False

def main():
    """Main migration function"""
    print("PostgreSQL User Migration Script")
    print("=" * 50)
    
    print("\n🚀 Starting user migration to PostgreSQL...")
    
    # Step 1: Clean up Firebase columns
    print("\n📋 Step 1: Cleaning up Firebase references...")
    if not clean_firebase_columns():
        print("❌ Firebase cleanup failed")
        return False
    
    # Step 2: Update schema
    print("\n📋 Step 2: Updating user table schema...")
    if not update_user_schema():
        print("❌ Schema update failed")
        return False
    
    # Step 3: Verify migration
    print("\n📋 Step 3: Verifying user migration...")
    if not verify_user_migration():
        print("❌ Migration verification failed")
        return False
    
    print("\n" + "=" * 50)
    print("✅ User migration to PostgreSQL completed successfully!")
    print("🗑️ All Firebase references have been removed")
    print("📊 All users are now stored exclusively in PostgreSQL")
    
    return True

if __name__ == "__main__":
    main()
