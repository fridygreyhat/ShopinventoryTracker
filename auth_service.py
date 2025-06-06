import os
import logging
from datetime import datetime
from functools import wraps
from flask import request, redirect, url_for, session, jsonify
from models import User, db
from werkzeug.security import check_password_hash

# Configure logging
logger = logging.getLogger(__name__)

def authenticate_user(email, password):
    """
    Authenticate user with email and password against PostgreSQL database

    Args:
        email (str): User email
        password (str): User password

    Returns:
        User: User object if authentication successful, None otherwise
    """
    try:
        logger.info(f"Attempting to authenticate user: {email}")

        # Find user by email
        user = User.query.filter_by(email=email).first()

        if not user:
            logger.warning(f"User not found: {email}")
            return None

        # Check if user is active
        if not getattr(user, 'active', True):
            logger.warning(f"User account is inactive: {email}")
            return None

        # Verify password
        if not user.check_password(password):
            logger.warning(f"Invalid password for user: {email}")
            return None

        logger.info(f"Authentication successful for user: {email}")
        return user

    except Exception as e:
        logger.error(f"Error authenticating user {email}: {str(e)}")
        return None

def create_or_update_user(user_data, extra_data=None):
    """
    Create or update user in the database

    Args:
        user_data (dict): User data including email, password
        extra_data (dict, optional): Additional user data from registration form

    Returns:
        User: User model instance
    """
    try:
        # Get email from user data
        email = user_data.get("email")
        password = user_data.get("password")

        if not email or not password:
            logger.error("Missing email or password in user data")
            return None

        # Check if user exists
        user = User.query.filter_by(email=email).first()

        if user:
            logger.info(f"User already exists: {email}")
            return user

        # Create username from email (default behavior)
        username = email.split("@")[0] if email else "user"

        # Ensure username is unique
        counter = 1
        original_username = username
        while User.query.filter_by(username=username).first():
            username = f"{original_username}{counter}"
            counter += 1

        # Create new user
        new_user = User(
            email=email,
            username=username,
            email_verified=True  # Set to True for PostgreSQL auth
        )

        # Set password
        new_user.set_password(password)

        # Add additional fields if provided
        if extra_data:
            new_user.first_name = extra_data.get('firstName')
            new_user.last_name = extra_data.get('lastName')
            new_user.phone = extra_data.get('phone')
            new_user.shop_name = extra_data.get('shopName')
            new_user.product_categories = extra_data.get('productCategories')

        db.session.add(new_user)
        db.session.commit()

        logger.info(f"Created new user: {email}")
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

def role_required(allowed_roles):
    """
    Decorator for routes that require specific roles
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login", next=request.url))

            user = User.query.get(session["user_id"])
            if not user:
                return jsonify({"error": "User not found"}), 404

            if user.role not in [role.value for role in allowed_roles]:
                return jsonify({"error": "Unauthorized access"}), 403

            return f(*args, **kwargs)
        return decorated_function
    return decorator

def admin_required(f):
    """
    Decorator for routes that require admin privileges
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("login", next=request.url))

        user = User.query.get(session["user_id"])
        if not user:
            return redirect(url_for("login"))

        if not user.is_admin:
            return jsonify({"error": "Admin access required"}), 403

        return f(*args, **kwargs)
    return decorated_function

def inventory_manager_required(f):
    """
    Decorator for routes that require inventory management privileges
    """
    from models import UserRole
    return role_required([UserRole.ADMIN, UserRole.INVENTORY_MANAGER])(f)

def sales_required(f):
    """
    Decorator for routes that require sales privileges
    """
    from models import UserRole
    return role_required([UserRole.ADMIN, UserRole.SALESPERSON])(f)