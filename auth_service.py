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
        if not user.is_active:
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

def validate_email_format(email):
    """
    Validate email format with enhanced regex
    
    Args:
        email (str): Email address to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not email or not isinstance(email, str):
        return False, "Email is required"
    
    email = email.strip()
    
    if len(email) == 0:
        return False, "Email cannot be empty"
    
    if len(email) > 320:  # RFC 5321 limit
        return False, "Email address is too long"
    
    # Enhanced email regex with better validation
    import re
    email_regex = r'^[a-zA-Z0-9.!#$%&\'*+/=?^_`{|}~-]+@[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?(?:\.[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?)*$'
    
    if not re.match(email_regex, email):
        return False, "Please enter a valid email address"
    
    # Check for common invalid patterns
    if email.startswith('.') or email.endswith('.'):
        return False, "Email cannot start or end with a period"
    
    if '..' in email:
        return False, "Email cannot contain consecutive periods"
    
    local_part, domain = email.rsplit('@', 1)
    
    if len(local_part) > 64:  # RFC 5321 limit for local part
        return False, "Email local part is too long"
    
    if len(domain) > 255:  # RFC 5321 limit for domain
        return False, "Email domain is too long"
    
    return True, ""

def validate_password_strength(password):
    """
    Validate password strength requirements
    
    Args:
        password (str): Password to validate
        
    Returns:
        tuple: (is_valid, error_message)
    """
    if not password or not isinstance(password, str):
        return False, "Password is required"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters long"
    
    if len(password) > 128:
        return False, "Password is too long (maximum 128 characters)"
    
    # Check for at least one letter and one number (optional but recommended)
    import re
    if not re.search(r'[a-zA-Z]', password):
        return False, "Password should contain at least one letter"
    
    # Check for common weak passwords
    weak_passwords = ['password', '123456', 'qwerty', 'abc123', 'password123']
    if password.lower() in weak_passwords:
        return False, "Password is too weak. Please choose a stronger password"
    
    return True, ""

def clean_and_validate_username(email):
    """
    Generate and validate username from email
    
    Args:
        email (str): Email address
        
    Returns:
        str: Clean username
    """
    import re
    
    # Create username from email local part
    username = email.split("@")[0] if email else "user"
    
    # Clean username (keep only alphanumeric and underscore)
    username = re.sub(r'[^a-zA-Z0-9_]', '', username)
    
    # Ensure username is not empty and has minimum length
    if not username or len(username) < 3:
        username = "user"
    
    # Limit username length
    if len(username) > 20:
        username = username[:20]
    
    return username

def create_or_update_user(user_data, extra_data=None):
    """
    Create or update user in the database with enhanced validation

    Args:
        user_data (dict): User data including email, password
        extra_data (dict, optional): Additional user data from registration form

    Returns:
        tuple: (User object or None, error_message)
    """
    try:
        # Get and validate email
        email = user_data.get("email", "").strip().lower()
        password = user_data.get("password", "")

        # Validate email format
        email_valid, email_error = validate_email_format(email)
        if not email_valid:
            logger.error(f"Email validation failed: {email_error}")
            return None, email_error

        # Validate password strength
        password_valid, password_error = validate_password_strength(password)
        if not password_valid:
            logger.error(f"Password validation failed: {password_error}")
            return None, password_error

        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            logger.info(f"User already exists: {email}")
            return None, "An account with this email already exists"

        # Generate and validate username
        username = clean_and_validate_username(email)
        
        # Ensure username is unique
        counter = 1
        original_username = username
        while User.query.filter_by(username=username).first():
            username = f"{original_username}{counter}"
            counter += 1
            # Prevent infinite loop
            if counter > 1000:
                username = f"user{int(datetime.utcnow().timestamp())}"
                break

        # Validate and clean extra data
        validated_extra_data = {}
        if extra_data:
            # Clean and validate first name
            if extra_data.get('firstName'):
                first_name = str(extra_data.get('firstName')).strip()
                if len(first_name) <= 64:
                    validated_extra_data['first_name'] = first_name
            
            # Clean and validate last name  
            if extra_data.get('lastName'):
                last_name = str(extra_data.get('lastName')).strip()
                if len(last_name) <= 64:
                    validated_extra_data['last_name'] = last_name
            
            # Clean and validate phone
            if extra_data.get('phone'):
                phone = str(extra_data.get('phone')).strip()
                if len(phone) <= 20:
                    validated_extra_data['phone'] = phone
            
            # Clean and validate shop name
            if extra_data.get('shopName'):
                shop_name = str(extra_data.get('shopName')).strip()
                if len(shop_name) <= 128:
                    validated_extra_data['shop_name'] = shop_name
            
            # Clean and validate product categories
            if extra_data.get('productCategories'):
                product_categories = str(extra_data.get('productCategories')).strip()
                if len(product_categories) <= 512:
                    validated_extra_data['product_categories'] = product_categories

        # Create new user within transaction
        try:
            new_user = User(
                email=email,
                username=username,
                email_verified=True,
                active=True,
                is_active=True,
                is_admin=False,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
                **validated_extra_data
            )

            # Set password hash
            new_user.set_password(password)

            # Add to session and flush to get ID
            db.session.add(new_user)
            db.session.flush()
            
            logger.info(f"Created new user with ID {new_user.id}: {email}")
            
            # Commit transaction
            db.session.commit()
            return new_user, None

        except Exception as db_error:
            db.session.rollback()
            logger.error(f"Database error creating user: {str(db_error)}")
            return None, "Failed to create account due to database error"

    except Exception as e:
        # Ensure rollback on any unexpected error
        try:
            db.session.rollback()
        except:
            pass
        logger.error(f"Unexpected error creating user: {str(e)}")
        return None, "An unexpected error occurred during registration"

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