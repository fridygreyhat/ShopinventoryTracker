
#!/usr/bin/env python3
"""
Script to check and manage admin users
"""
import os
from app import app, db
from models import User

def list_admin_users():
    """List all admin users"""
    with app.app_context():
        admin_users = User.query.filter_by(is_admin=True).all()
        
        print("=== ADMIN USERS ===")
        if not admin_users:
            print("No admin users found!")
        else:
            for user in admin_users:
                print(f"ID: {user.id}")
                print(f"Username: {user.username}")
                print(f"Email: {user.email}")
                print(f"Active: {user.is_active}")
                print(f"Created: {user.created_at}")
                print("-" * 30)

def create_admin_user(username, email, password, first_name="Admin", last_name="User"):
    """Create a new admin user"""
    with app.app_context():
        # Check if user already exists
        existing_user = User.query.filter(
            (User.email == email) | (User.username == username)
        ).first()
        
        if existing_user:
            print(f"User with email {email} or username {username} already exists!")
            return False
        
        # Create new admin user
        new_admin = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            is_admin=True,
            is_active=True,
            email_verified=True
        )
        new_admin.set_password(password)
        
        try:
            db.session.add(new_admin)
            db.session.commit()
            print(f"Admin user '{username}' created successfully!")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error creating admin user: {e}")
            return False

def change_user_password(username_or_email, new_password):
    """Change password for a user"""
    with app.app_context():
        user = User.query.filter(
            (User.email == username_or_email) | (User.username == username_or_email)
        ).first()
        
        if not user:
            print(f"User '{username_or_email}' not found!")
            return False
        
        try:
            user.set_password(new_password)
            db.session.commit()
            print(f"Password changed successfully for user '{user.username}'!")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error changing password: {e}")
            return False

def make_user_admin(username_or_email):
    """Make an existing user an admin"""
    with app.app_context():
        user = User.query.filter(
            (User.email == username_or_email) | (User.username == username_or_email)
        ).first()
        
        if not user:
            print(f"User '{username_or_email}' not found!")
            return False
        
        try:
            user.is_admin = True
            db.session.commit()
            print(f"User '{user.username}' is now an admin!")
            return True
        except Exception as e:
            db.session.rollback()
            print(f"Error making user admin: {e}")
            return False

if __name__ == "__main__":
    print("Admin User Management")
    print("====================")
    
    while True:
        print("\nOptions:")
        print("1. List all admin users")
        print("2. Create new admin user")
        print("3. Change user password")
        print("4. Make existing user admin")
        print("5. Exit")
        
        choice = input("\nEnter your choice (1-5): ").strip()
        
        if choice == "1":
            list_admin_users()
        
        elif choice == "2":
            print("\nCreate New Admin User:")
            username = input("Username: ").strip()
            email = input("Email: ").strip()
            password = input("Password: ").strip()
            first_name = input("First Name (optional): ").strip() or "Admin"
            last_name = input("Last Name (optional): ").strip() or "User"
            
            if username and email and password:
                create_admin_user(username, email, password, first_name, last_name)
            else:
                print("Username, email, and password are required!")
        
        elif choice == "3":
            print("\nChange User Password:")
            username_or_email = input("Username or Email: ").strip()
            new_password = input("New Password: ").strip()
            
            if username_or_email and new_password:
                change_user_password(username_or_email, new_password)
            else:
                print("Username/email and new password are required!")
        
        elif choice == "4":
            print("\nMake User Admin:")
            username_or_email = input("Username or Email: ").strip()
            
            if username_or_email:
                make_user_admin(username_or_email)
            else:
                print("Username or email is required!")
        
        elif choice == "5":
            print("Goodbye!")
            break
        
        else:
            print("Invalid choice! Please try again.")
