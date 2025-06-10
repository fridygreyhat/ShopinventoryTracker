
#!/usr/bin/env python3
"""
Migration script to remove Firebase dependencies and ensure PostgreSQL authentication
Run this script to clean up Firebase-related data and ensure all users have proper passwords
"""

import os
from datetime import datetime
from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def migrate_firebase_users():
    """Migrate users from Firebase to PostgreSQL authentication"""
    print("🔄 Migrating users from Firebase to PostgreSQL authentication...")
    
    with app.app_context():
        try:
            # Get all users
            users = User.query.all()
            updated_count = 0
            
            for user in users:
                needs_update = False
                
                # Check if user has a password hash
                if not user.password_hash or user.password_hash == 'firebase-auth-user':
                    # Generate a temporary password for Firebase users
                    temp_password = f"temp_{user.id}_{datetime.now().strftime('%Y%m%d')}"
                    user.password_hash = generate_password_hash(temp_password)
                    needs_update = True
                    print(f"📝 Generated temporary password for user {user.email}: {temp_password}")
                
                # Ensure email is verified for all existing users
                if not user.email_verified:
                    user.email_verified = True
                    needs_update = True
                
                # Remove firebase_uid if it exists (handled by model change)
                
                if needs_update:
                    user.updated_at = datetime.utcnow()
                    updated_count += 1
            
            db.session.commit()
            print(f"✅ Updated {updated_count} users for PostgreSQL authentication")
            
            # Display users with temporary passwords
            temp_password_users = User.query.filter(
                User.password_hash.like('%temp_%')
            ).all()
            
            if temp_password_users:
                print("\n⚠️  Users with temporary passwords (they should change these):")
                for user in temp_password_users:
                    print(f"   - {user.email}")
                print("\n💡 These users should log in and change their passwords immediately.")
            
        except Exception as e:
            db.session.rollback()
            print(f"❌ Migration failed: {e}")
            return False
    
    return True

def cleanup_firebase_settings():
    """Remove Firebase-related settings"""
    print("🧹 Cleaning up Firebase-related settings...")
    
    with app.app_context():
        try:
            from models import Setting
            
            # Remove Firebase-related settings
            firebase_settings = Setting.query.filter(
                Setting.key.like('%firebase%')
            ).all()
            
            for setting in firebase_settings:
                db.session.delete(setting)
            
            db.session.commit()
            print(f"✅ Removed {len(firebase_settings)} Firebase-related settings")
            
        except Exception as e:
            db.session.rollback()
            print(f"⚠️  Could not cleanup Firebase settings: {e}")

def verify_postgresql_setup():
    """Verify PostgreSQL authentication is working"""
    print("🔍 Verifying PostgreSQL authentication setup...")
    
    with app.app_context():
        try:
            # Test database connection
            users_count = User.query.count()
            print(f"✅ Database connection working - {users_count} users found")
            
            # Check for users without proper authentication
            users_without_password = User.query.filter(
                db.or_(
                    User.password_hash.is_(None),
                    User.password_hash == ''
                )
            ).count()
            
            if users_without_password > 0:
                print(f"⚠️  Found {users_without_password} users without passwords")
                return False
            
            print("✅ All users have proper password authentication")
            return True
            
        except Exception as e:
            print(f"❌ Verification failed: {e}")
            return False

def main():
    """Main migration function"""
    print("🚀 Starting Firebase to PostgreSQL authentication migration...")
    
    # Check if PostgreSQL is configured
    database_url = os.environ.get("DATABASE_URL")
    if not database_url or not database_url.startswith(("postgres://", "postgresql://")):
        print("❌ PostgreSQL DATABASE_URL not found. Please set up PostgreSQL first.")
        return
    
    print(f"✅ PostgreSQL database configured")
    
    # Run migration steps
    success = True
    success &= migrate_firebase_users()
    cleanup_firebase_settings()
    success &= verify_postgresql_setup()
    
    if success:
        print("\n🎉 Migration completed successfully!")
        print("\n📋 Next steps:")
        print("1. Remove Firebase SDK scripts from your templates")
        print("2. Test login/registration with the new PostgreSQL system")
        print("3. Users with temporary passwords should change them immediately")
        print("4. Consider implementing password reset functionality")
    else:
        print("\n❌ Migration completed with warnings. Please review the issues above.")

if __name__ == "__main__":
    main()
