import logging
from functools import wraps
from flask import session, request, jsonify, redirect, url_for
from datetime import datetime

logger = logging.getLogger(__name__)

def login_required(f):
    """Decorator to require login for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function



def create_or_update_user(user_data, extra_data=None):
    """Create or update user in database"""
    try:
        from models import User, db

        email = user_data.get('email')
        if not email:
            return None

        # Find existing user or create new one
        user = User.query.filter_by(email=email).first()

        if not user:
            # Create new user
            user = User(
                email=email,
                username=email.split('@')[0],  # Use email prefix as username
                is_active=True,
                email_verified=user_data.get('emailVerified', False)
            )

            # Set a default password (should be updated by user)
            user.set_password('temp_password_change_me')

            db.session.add(user)

        # Update user data
        if user_data.get('displayName'):
            name_parts = user_data.get('displayName', '').split(' ', 1)
            user.first_name = name_parts[0] if len(name_parts) > 0 else ''
            user.last_name = name_parts[1] if len(name_parts) > 1 else ''

        # Apply extra data if provided
        if extra_data:
            for key, value in extra_data.items():
                if hasattr(user, key):
                    setattr(user, key, value)

        user.updated_at = datetime.utcnow()
        db.session.commit()

        return user

    except Exception as e:
        logger.error(f"Error creating/updating user: {str(e)}")
        return None

def role_required(allowed_roles):
    """
    Decorator for routes that require specific roles
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login", next=request.url))

            from models import User
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

        from models import User
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