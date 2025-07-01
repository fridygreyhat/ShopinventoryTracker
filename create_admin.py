
#!/usr/bin/env python3
"""
Quick script to create an admin user
"""
from app import app, db
from models import User

# Admin user details - CHANGE THESE!
ADMIN_USERNAME = "admin"
ADMIN_EMAIL = "admin@yourdomain.com"
ADMIN_PASSWORD = "your_secure_password"
ADMIN_FIRST_NAME = "System"
ADMIN_LAST_NAME = "Administrator"

def create_admin():
    with app.app_context():
        # Check if admin already exists
        existing_admin = User.query.filter(
            (User.email == ADMIN_EMAIL) | (User.username == ADMIN_USERNAME)
        ).first()
        
        if existing_admin:
            print(f"Admin user already exists: {existing_admin.username} ({existing_admin.email})")
            return
        
        # Create admin user
        admin_user = User(
            username=ADMIN_USERNAME,
            email=ADMIN_EMAIL,
            first_name=ADMIN_FIRST_NAME,
            last_name=ADMIN_LAST_NAME,
            is_admin=True,
            is_active=True,
            email_verified=True
        )
        admin_user.set_password(ADMIN_PASSWORD)
        
        try:
            db.session.add(admin_user)
            db.session.commit()
            print(f"Admin user created successfully!")
            print(f"Username: {ADMIN_USERNAME}")
            print(f"Email: {ADMIN_EMAIL}")
            print(f"Login at: /login")
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {e}")

if __name__ == "__main__":
    create_admin()
