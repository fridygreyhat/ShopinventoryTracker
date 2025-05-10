import os
import logging
import json
import requests
from functools import wraps
from flask import request, redirect, url_for, session, jsonify
from models import User, db

# Configure logging
logger = logging.getLogger(__name__)

# Firebase API endpoints
FIREBASE_API_KEY = os.environ.get("FIREBASE_API_KEY")
FIREBASE_AUTH_SIGN_IN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
FIREBASE_AUTH_SIGN_UP_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signUp?key={FIREBASE_API_KEY}"
FIREBASE_AUTH_USER_INFO_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:lookup?key={FIREBASE_API_KEY}"

def verify_firebase_token(id_token):
    """
    Verify Firebase ID token and return user info
    
    Args:
        id_token (str): Firebase ID token
        
    Returns:
        dict: User information if token is valid, None otherwise
    """
    try:
        # Verify token with Firebase
        response = requests.post(
            FIREBASE_AUTH_USER_INFO_URL,
            json={"idToken": id_token}
        )
        
        if response.status_code != 200:
            logger.error(f"Failed to verify token: {response.text}")
            return None
            
        # Get user info from response
        user_data = response.json()
        
        if "users" not in user_data or not user_data["users"]:
            logger.error("No user found in Firebase response")
            return None
            
        # Return first user (there should only be one)
        return user_data["users"][0]
        
    except Exception as e:
        logger.error(f"Error verifying Firebase token: {str(e)}")
        return None

def create_or_update_user(user_data):
    """
    Create or update user in the database based on Firebase user data
    
    Args:
        user_data (dict): Firebase user data
        
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
            db.session.commit()
            return user
            
        # Create new user
        new_user = User(
            email=email,
            username=email.split("@")[0],  # Default username is the part before @ in email
            firebase_uid=firebase_uid,
            email_verified=user_data.get("emailVerified", False)
        )
        
        db.session.add(new_user)
        db.session.commit()
        return new_user
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating/updating user: {str(e)}")
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