#!/usr/bin/env python3
"""
Script to create the admin user with specified credentials
"""

from app import app, db
from models import User
from werkzeug.security import generate_password_hash

def create_admin_user():
    with app.app_context():
        # Check if admin user already exists
        admin_user = User.query.filter_by(email='byer2311@gmail.com').first()
        
        if admin_user:
            # Update existing user to be admin
            admin_user.username = 'admin'
            admin_user.is_admin = True
            admin_user.set_password('Newnyarubanda12!')
            print(f"Updated existing user {admin_user.email} to admin status")
        else:
            # Create new admin user
            admin_user = User(
                username='admin',
                email='byer2311@gmail.com',
                first_name='Admin',
                last_name='User',
                is_admin=True
            )
            admin_user.set_password('Newnyarubanda12!')
            db.session.add(admin_user)
            print(f"Created new admin user: {admin_user.email}")
        
        db.session.commit()
        print("Admin user created/updated successfully!")
        print(f"Email: byer2311@gmail.com")
        print(f"Password: Newnyarubanda12!")
        print(f"Access admin portal at: /admin")

if __name__ == '__main__':
    create_admin_user()