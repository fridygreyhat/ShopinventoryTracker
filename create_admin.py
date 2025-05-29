
#!/usr/bin/env python3
"""
Script to manually make a user admin
Run this after registering your account
"""

from app import app, db
from models import User

def make_admin(email):
    """Make a user admin by email"""
    with app.app_context():
        user = User.query.filter_by(email=email).first()
        if user:
            user.is_admin = True
            db.session.commit()
            print(f"✅ Admin privileges granted to {user.email}")
            print(f"   User ID: {user.id}")
            print(f"   Username: {user.username}")
        else:
            print(f"❌ User with email {email} not found")
            print("Available users:")
            users = User.query.all()
            for u in users:
                print(f"   - {u.email} (ID: {u.id})")

if __name__ == "__main__":
    email = input("Enter email address to make admin: ").strip()
    make_admin(email)
