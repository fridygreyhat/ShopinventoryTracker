
#!/usr/bin/env python3
"""
Script to add a specific user as admin
"""

from app import app, db
from models import User
from datetime import datetime

def create_admin_user():
    """Create or update the specific user as admin"""
    with app.app_context():
        try:
            email = "byer2311@gmail.com"
            password = "Newnyarubanda12!"
            
            # Check if user already exists
            existing_user = User.query.filter_by(email=email).first()
            
            if existing_user:
                # Update existing user to admin
                existing_user.is_admin = True
                existing_user.active = True
                existing_user.is_active = True
                existing_user.updated_at = datetime.utcnow()
                db.session.commit()
                print(f"✅ Updated existing user {email} to admin")
                print(f"   User ID: {existing_user.id}")
                print(f"   Username: {existing_user.username}")
            else:
                # Create new admin user
                username = email.split("@")[0]  # Use email prefix as username
                
                new_user = User(
                    username=username,
                    email=email,
                    email_verified=True,
                    active=True,
                    is_active=True,
                    is_admin=True,
                    created_at=datetime.utcnow(),
                    updated_at=datetime.utcnow()
                )
                
                # Set password
                new_user.set_password(password)
                
                # Add to database
                db.session.add(new_user)
                db.session.commit()
                
                print(f"✅ Created new admin user {email}")
                print(f"   User ID: {new_user.id}")
                print(f"   Username: {new_user.username}")
            
            print(f"   Admin Status: Yes")
            print(f"   Active Status: Yes")
            print("\n🔐 Login credentials:")
            print(f"   Email: {email}")
            print(f"   Password: {password}")
            
        except Exception as e:
            print(f"❌ Error creating admin user: {str(e)}")
            db.session.rollback()

if __name__ == "__main__":
    create_admin_user()
