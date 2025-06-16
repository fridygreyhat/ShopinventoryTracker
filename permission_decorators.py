"""
Permission decorators for role-based access control
"""
from functools import wraps
from flask import abort, flash, redirect, url_for
from flask_login import current_user

def permission_required(permission):
    """
    Decorator to require specific permission for a route
    
    Args:
        permission (str): The permission required to access the route
    
    Returns:
        function: Decorated function that checks permissions
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not current_user.has_permission(permission):
                flash(f'You do not have permission to access this feature. Required permission: {permission.replace("_", " ").title()}', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def inventory_permission_required(f):
    """Decorator for routes that require inventory management permission"""
    return permission_required('manage_inventory')(f)

def sales_permission_required(f):
    """Decorator for routes that require sales management permission"""
    return permission_required('manage_sales')(f)

def customers_permission_required(f):
    """Decorator for routes that require customer management permission"""
    return permission_required('manage_customers')(f)

def finances_permission_required(f):
    """Decorator for routes that require finance management permission"""
    return permission_required('manage_finances')(f)

def reports_permission_required(f):
    """Decorator for routes that require reports viewing permission"""
    return permission_required('view_reports')(f)

def locations_permission_required(f):
    """Decorator for routes that require location management permission"""
    return permission_required('manage_locations')(f)

def categories_permission_required(f):
    """Decorator for routes that require category management permission"""
    return permission_required('manage_categories')(f)

def admin_or_permission_required(permission):
    """
    Decorator that allows access if user is admin OR has specific permission
    
    Args:
        permission (str): The permission required for non-admin users
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('auth.login'))
            
            if not (current_user.is_admin or current_user.has_permission(permission)):
                flash(f'You do not have permission to access this feature. Required permission: {permission.replace("_", " ").title()}', 'error')
                return redirect(url_for('index'))
            
            return f(*args, **kwargs)
        return decorated_function
    return decorator