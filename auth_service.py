import os
import logging
import json
import secrets
import time
from datetime import datetime, timedelta
from functools import wraps
from flask import request, redirect, url_for, session, jsonify
from flask_login import current_user, login_required
from models import User, db
from werkzeug.security import generate_password_hash, check_password_hash

# Configure logging
logger = logging.getLogger(__name__)

def generate_verification_token(user):
    """
    Generate a verification token for email verification
    
    Args:
        user (User): User model instance
        
    Returns:
        str: Verification token
    """
    # Generate random token
    token = secrets.token_urlsafe(32)
    
    # Set token expiration (24 hours)
    expiration = datetime.utcnow() + timedelta(hours=24)
    
    # Update user model
    user.verification_token = token
    user.verification_token_expires = expiration
    db.session.commit()
    
    return token

def verify_token(token):
    """
    Verify a token and mark the user's email as verified
    
    Args:
        token (str): Verification token
        
    Returns:
        User: User model instance if token is valid, None otherwise
    """
    # Find the user by token
    user = User.query.filter_by(verification_token=token).first()
    
    if not user:
        return None
        
    # Check if token has expired
    if user.verification_token_expires and user.verification_token_expires < datetime.utcnow():
        return None
        
    # Mark email as verified
    user.email_verified = True
    user.verification_token = None
    user.verification_token_expires = None
    db.session.commit()
    
    return user

def update_user_profile(user_id, profile_data):
    """
    Update user profile data
    
    Args:
        user_id (int): User ID
        profile_data (dict): Profile data to update
        
    Returns:
        User: Updated user model instance
    """
    try:
        # Get user from database
        user = User.query.get(user_id)
        
        if not user:
            logger.error(f"User not found: {user_id}")
            return None
            
        # Update user profile data
        if 'username' in profile_data:
            # Check if username is already taken
            existing_user = User.query.filter_by(username=profile_data['username']).first()
            if existing_user and existing_user.id != user_id:
                return None
            user.username = profile_data['username']
            
        if 'firstName' in profile_data:
            user.first_name = profile_data['firstName']
            
        if 'lastName' in profile_data:
            user.last_name = profile_data['lastName']
            
        if 'shopName' in profile_data:
            user.shop_name = profile_data['shopName']
            
        if 'productCategories' in profile_data:
            user.product_categories = profile_data['productCategories']
        
        # Save changes
        db.session.commit()
        return user
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user profile: {str(e)}")
        return None

def admin_required(f):
    """
    Decorator for routes that require admin privileges
    """
    @wraps(f)
    @login_required
    def decorated_function(*args, **kwargs):
        # Check if user is an admin
        if not current_user.is_admin:
            return jsonify({"error": "Unauthorized access"}), 403
            
        return f(*args, **kwargs)
    return decorated_function

def change_user_password(user_id, current_password, new_password):
    """
    Change user password
    
    Args:
        user_id (int): User ID
        current_password (str): Current password
        new_password (str): New password
        
    Returns:
        bool: True if password was changed, False otherwise
    """
    try:
        # Get user from database
        user = User.query.get(user_id)
        
        if not user:
            logger.error(f"User not found: {user_id}")
            return False
            
        # Check current password
        if not user.check_password(current_password):
            logger.error(f"Invalid current password for user: {user_id}")
            return False
            
        # Update password
        user.set_password(new_password)
        db.session.commit()
        return True
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error changing password: {str(e)}")
        return False