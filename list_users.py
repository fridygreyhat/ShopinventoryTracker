
#!/usr/bin/env python3
"""
Script to list all users in the database
"""

from app import app, db
from models import User

def list_all_users():
    """List all users in the database"""
    with app.app_context():
        try:
            users = User.query.all()
            
            print(f"\n=== Database Users ({len(users)} total) ===")
            print("-" * 80)
            
            for user in users:
                print(f"ID: {user.id}")
                print(f"Username: {user.username}")
                print(f"Email: {user.email}")
                print(f"Name: {user.first_name or ''} {user.last_name or ''}".strip() or "N/A")
                print(f"Shop: {user.shop_name or 'N/A'}")
                print(f"Admin: {'Yes' if user.is_admin else 'No'}")
                print(f"Active: {'Yes' if getattr(user, 'active', True) else 'No'}")
                print(f"Email Verified: {'Yes' if user.email_verified else 'No'}")
                print(f"Created: {user.created_at.strftime('%Y-%m-%d %H:%M:%S') if user.created_at else 'N/A'}")
                print(f"Last Login: {user.last_login.strftime('%Y-%m-%d %H:%M:%S') if user.last_login else 'Never'}")
                print("-" * 80)
                
        except Exception as e:
            print(f"Error listing users: {str(e)}")

if __name__ == "__main__":
    list_all_users()
