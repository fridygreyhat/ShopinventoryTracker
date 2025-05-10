import os
import logging
import json
from datetime import datetime
from functools import wraps
from flask import request, redirect, url_for, session, jsonify
from models import User, db

# Import Firebase Admin SDK
import firebase_admin
from firebase_admin import credentials, auth

# Configure logging
logger = logging.getLogger(__name__)

# Initialize Firebase Admin SDK if not already initialized
try:
    # Check if the app is already initialized
    firebase_admin.get_app()
    logger.info("Firebase Admin SDK already initialized")
except ValueError:
    # We don't need to fully initialize the Admin SDK
    # since we'll be using the REST API for token verification
    try:
        # Initialize with minimal configuration
        firebase_admin.initialize_app()
        logger.info("Firebase Admin SDK initialized with minimal configuration")
    except Exception as e:
        logger.warning(f"Could not initialize Firebase Admin: {str(e)}")
        
    # Log API configuration status
    has_api_key = bool(os.environ.get("FIREBASE_API_KEY"))
    has_project_id = bool(os.environ.get("FIREBASE_PROJECT_ID"))
    has_app_id = bool(os.environ.get("FIREBASE_APP_ID"))
    
    logger.info(f"Firebase configuration status - API Key: {'✓' if has_api_key else '✗'}, " + 
                f"Project ID: {'✓' if has_project_id else '✗'}, " + 
                f"App ID: {'✓' if has_app_id else '✗'}")
    
    # Check if we have all required keys
    if not (has_api_key and has_project_id and has_app_id):
        logger.warning("Missing one or more Firebase configuration values")

def verify_firebase_token(id_token):
    """
    Verify Firebase ID token and return user info
    
    Args:
        id_token (str): Firebase ID token
        
    Returns:
        dict: User information if token is valid, None otherwise
    """
    import requests
    
    try:
        # Try to use Firebase Admin SDK if available
        try:
            # Verify the Firebase token using Admin SDK
            decoded_token = auth.verify_id_token(id_token)
            
            # Extract user data
            user_data = {
                "localId": decoded_token.get("uid"),
                "email": decoded_token.get("email"),
                "emailVerified": decoded_token.get("email_verified", False),
                "displayName": decoded_token.get("name", ""),
            }
            
            logger.info("Token verified with Firebase Admin SDK")
            return user_data
            
        except Exception as admin_error:
            logger.warning(f"Failed to verify token with Admin SDK: {str(admin_error)}")
            
            # Fall back to REST API
            firebase_api_key = os.environ.get("FIREBASE_API_KEY")
            if not firebase_api_key:
                raise ValueError("Firebase API key not available")
                
            # Verify token with REST API
            url = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={firebase_api_key}"
            response = requests.post(url, json={"idToken": id_token})
            
            if response.status_code != 200:
                logger.error(f"Failed to verify token with REST API: {response.text}")
                return None
                
            # Extract user data
            response_data = response.json()
            if "users" not in response_data or not response_data["users"]:
                logger.error("No user found in Firebase response")
                return None
                
            logger.info("Token verified with Firebase REST API")
            return response_data["users"][0]
            
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {str(e)}")
        return None

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
        user = User.query.get(user_id)
        
        if not user:
            logger.error(f"User with ID {user_id} not found")
            return None
            
        # Update fields if provided
        if 'username' in profile_data:
            # Check for username uniqueness
            existing_user = User.query.filter_by(username=profile_data['username']).first()
            if existing_user and existing_user.id != user.id:
                logger.error(f"Username {profile_data['username']} already taken")
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
            
        # Update timestamps
        user.updated_at = datetime.utcnow()
        
        db.session.commit()
        return user
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user profile: {str(e)}")
        return None

def create_or_update_user(user_data, extra_data=None):
    """
    Create or update user in the database based on Firebase user data
    
    Args:
        user_data (dict): Firebase user data
        extra_data (dict, optional): Additional user data from registration form
        
    Returns:
        User: User model instance
    """
    try:
        # Get email from Firebase user data
        email = user_data.get("email")
        firebase_uid = user_data.get("localId")
        
        if not email or not firebase_uid:
            logger.error("Missing email or Firebase UID in user data")
            return None
            
        # Check if user exists
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Update existing user
            user.firebase_uid = firebase_uid
            user.email_verified = user_data.get("emailVerified", False)
            
            # Update additional fields if provided
            if extra_data:
                if 'firstName' in extra_data:
                    user.first_name = extra_data.get('firstName')
                if 'lastName' in extra_data:
                    user.last_name = extra_data.get('lastName')
                if 'shopName' in extra_data:
                    user.shop_name = extra_data.get('shopName')
                if 'productCategories' in extra_data:
                    user.product_categories = extra_data.get('productCategories')
            
            db.session.commit()
            return user
            
        # Create new user with username from email (default behavior)
        username = email.split("@")[0] if email else "user"
        
        # Create new user
        new_user = User(
            email=email,
            username=username,
            firebase_uid=firebase_uid,
            email_verified=user_data.get("emailVerified", False)
        )
        
        # Add additional fields if provided
        if extra_data:
            new_user.first_name = extra_data.get('firstName')
            new_user.last_name = extra_data.get('lastName')
            new_user.shop_name = extra_data.get('shopName')
            new_user.product_categories = extra_data.get('productCategories')
        
        db.session.add(new_user)
        db.session.commit()
        return new_user
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating/updating user: {str(e)}")
        return None

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

def login_required(f):
    """
    Decorator for routes that require login
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if "user_id" not in session:
            return redirect(url_for("login", next=request.url))
        return f(*args, **kwargs)
    return decorated_function

def admin_required(f):
    """
    Decorator for routes that require admin privileges
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check if user is logged in
        if "user_id" not in session:
            return redirect(url_for("login", next=request.url))
            
        # Check if user is an admin
        user = User.query.get(session["user_id"])
        if not user or not user.is_admin:
            return jsonify({"error": "Unauthorized access"}), 403
            
        return f(*args, **kwargs)
    return decorated_function