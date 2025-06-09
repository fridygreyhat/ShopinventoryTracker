import os
from datetime import datetime, timedelta
from functools import wraps
from flask import Blueprint, render_template, request, redirect, url_for, flash, session, jsonify
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from app import app, db
from models import User
from email_service import EmailService
import re

# Create auth blueprint
auth_bp = Blueprint('postgresql_auth', __name__, url_prefix='/auth')

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_password(password):
    """Validate password strength"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Za-z]', password):
        return False, "Password must contain at least one letter"
    if not re.search(r'[0-9]', password):
        return False, "Password must contain at least one number"
    return True, ""

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = bool(request.form.get('remember'))
        
        if not email or not password:
            flash('Please fill in all fields', 'error')
            return render_template('auth/login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.active:
                flash('Your account has been deactivated. Please contact support.', 'error')
                return render_template('auth/login.html')
            
            if not user.email_verified:
                flash('Please verify your email address before logging in. Check your email for the verification link.', 'warning')
                return redirect(url_for('postgresql_auth.verification_sent', email=user.email))
            
            login_user(user, remember=remember)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid email or password', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        # Get form data
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        shop_name = request.form.get('shop_name', '').strip()
        phone = request.form.get('phone', '').strip()
        
        # Validation
        errors = []
        
        if not email:
            errors.append('Email is required')
        elif not validate_email(email):
            errors.append('Please enter a valid email address')
        elif User.query.filter_by(email=email).first():
            errors.append('Email already registered')
        
        if not password:
            errors.append('Password is required')
        else:
            is_valid, message = validate_password(password)
            if not is_valid:
                errors.append(message)
        
        if password != confirm_password:
            errors.append('Passwords do not match')
        
        if not first_name:
            errors.append('First name is required')
        
        if not last_name:
            errors.append('Last name is required')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        # Create username from email
        username = email.split('@')[0]
        counter = 1
        base_username = username
        while User.query.filter_by(username=username).first():
            username = f"{base_username}{counter}"
            counter += 1
        
        # Create new user
        try:
            user = User(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                shop_name=shop_name,
                phone=phone,
                active=True,
                is_admin=False,
                role='user'
            )
            user.set_password(password)
            user.email_verified = False  # Email not verified yet
            
            # Generate email verification token
            verification_token = user.generate_email_verification_token()
            
            db.session.add(user)
            db.session.commit()
            
            # Send email verification email
            EmailService.send_verification_email(user, verification_token)
            
            flash('Registration successful! Please check your email to verify your account before logging in.', 'success')
            return redirect(url_for('postgresql_auth.verification_sent', email=email))
            
        except Exception as e:
            db.session.rollback()
            import logging
            logging.error(f"Registration error: {str(e)}")
            flash(f'Registration failed: {str(e)}', 'error')
            return render_template('auth/register.html')
    
    return render_template('auth/register.html')

@auth_bp.route('/logout', methods=['GET', 'POST'])
def logout():
    from datetime import datetime
    logout_time = datetime.now().strftime('%B %d, %Y at %I:%M %p')
    
    # Clear session completely
    session.clear()
    
    # Logout user if authenticated
    if current_user.is_authenticated:
        logout_user()
    
    # Force session to be saved
    session.permanent = False
    
    # Handle AJAX requests
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return jsonify({
            'success': True,
            'message': 'Logged out successfully',
            'redirect': url_for('index')
        })
    
    return render_template('auth/logout_success.html', logout_time=logout_time)

@auth_bp.route('/logout-redirect')
def logout_redirect():
    """Handles logout redirects from various parts of the app"""
    if current_user.is_authenticated:
        logout_user()
    session.clear()
    return redirect(url_for('index'))

@auth_bp.route('/profile')
@login_required
def profile():
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        # Get form data
        first_name = request.form.get('first_name', '').strip()
        last_name = request.form.get('last_name', '').strip()
        shop_name = request.form.get('shop_name', '').strip()
        phone = request.form.get('phone', '').strip()
        product_categories = request.form.get('product_categories', '').strip()
        
        # Validation
        errors = []
        
        if not first_name:
            errors.append('First name is required')
        
        if not last_name:
            errors.append('Last name is required')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/edit_profile.html', user=current_user)
        
        # Update user
        try:
            current_user.first_name = first_name
            current_user.last_name = last_name
            current_user.shop_name = shop_name
            current_user.phone = phone
            current_user.product_categories = product_categories
            current_user.updated_at = datetime.utcnow()
            
            db.session.commit()
            flash('Profile updated successfully!', 'success')
            return redirect(url_for('postgresql_auth.settings') + '#account')
            
        except Exception as e:
            db.session.rollback()
            flash('Profile update failed. Please try again.', 'error')
    
    return render_template('auth/edit_profile.html', user=current_user)

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        # Validation
        errors = []
        
        if not current_password:
            errors.append('Current password is required')
        elif not current_user.check_password(current_password):
            errors.append('Current password is incorrect')
        
        if not new_password:
            errors.append('New password is required')
        else:
            is_valid, message = validate_password(new_password)
            if not is_valid:
                errors.append(message)
        
        if new_password != confirm_password:
            errors.append('New passwords do not match')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/change_password.html')
        
        # Update password
        try:
            current_user.set_password(new_password)
            current_user.updated_at = datetime.utcnow()
            db.session.commit()
            
            flash('Password changed successfully!', 'success')
            return redirect(url_for('postgresql_auth.settings') + '#security')
            
        except Exception as e:
            db.session.rollback()
            flash('Password change failed. Please try again.', 'error')
    
    return render_template('auth/change_password.html')

@auth_bp.route('/settings')
@login_required
def settings():
    return render_template('auth/settings.html', user=current_user)

@auth_bp.route('/settings/preferences', methods=['POST'])
@login_required
def update_preferences():
    try:
        # Get form data
        language = request.form.get('language', 'en')
        currency_format = request.form.get('currency_format', 'TSh')
        date_format = request.form.get('date_format', 'DD/MM/YYYY')
        timezone = request.form.get('timezone', 'Africa/Dar_es_Salaam')
        
        # Update user preferences
        current_user.language = language
        current_user.currency_format = currency_format
        current_user.date_format = date_format
        current_user.timezone = timezone
        current_user.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Preferences updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Preferences update error: {str(e)}")
        flash('Failed to update preferences. Please try again.', 'error')
    
    return redirect(url_for('postgresql_auth.settings') + '#preferences')

@auth_bp.route('/settings/notifications', methods=['POST'])
@login_required
def update_notifications():
    try:
        # Get notification preferences
        email_notifications = 'email_notifications' in request.form
        sms_notifications = 'sms_notifications' in request.form
        low_stock_alerts = 'low_stock_alerts' in request.form
        sales_reports = 'sales_reports' in request.form
        
        # Update user notification preferences
        current_user.email_notifications = email_notifications
        current_user.sms_notifications = sms_notifications
        current_user.low_stock_alerts = low_stock_alerts
        current_user.sales_reports = sales_reports
        current_user.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Notification preferences updated successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Notifications update error: {str(e)}")
        flash('Failed to update notification preferences. Please try again.', 'error')
    
    return redirect(url_for('postgresql_auth.settings') + '#notifications')

@auth_bp.route('/settings/business', methods=['POST'])
@login_required
def update_business_settings():
    try:
        # Get business settings
        business_type = request.form.get('business_type', 'retail')
        default_tax_rate = float(request.form.get('default_tax_rate', 0))
        low_stock_threshold = int(request.form.get('low_stock_threshold', 10))
        
        # Validate inputs
        if default_tax_rate < 0 or default_tax_rate > 100:
            flash('Tax rate must be between 0 and 100 percent.', 'error')
            return redirect(url_for('postgresql_auth.settings') + '#business')
        
        if low_stock_threshold < 1:
            flash('Low stock threshold must be at least 1.', 'error')
            return redirect(url_for('postgresql_auth.settings') + '#business')
        
        # Update user business settings
        current_user.business_type = business_type
        current_user.default_tax_rate = default_tax_rate
        current_user.low_stock_threshold = low_stock_threshold
        current_user.updated_at = datetime.utcnow()
        
        db.session.commit()
        flash('Business settings updated successfully!', 'success')
        
    except ValueError:
        flash('Invalid number format. Please check your inputs.', 'error')
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Business settings update error: {str(e)}")
        flash('Failed to update business settings. Please try again.', 'error')
    
    return redirect(url_for('postgresql_auth.settings') + '#business')

# Custom decorators
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@auth_bp.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    """Handle password reset request"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        
        if not email:
            flash('Please enter your email address', 'error')
            return render_template('auth/forgot_password.html')
        
        if not validate_email(email):
            flash('Please enter a valid email address', 'error')
            return render_template('auth/forgot_password.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user:
            # Send password reset email
            if EmailService.send_password_reset_email(user):
                flash('Password reset instructions have been sent to your email address', 'success')
            else:
                flash('Unable to send reset email. Please try again later.', 'error')
        else:
            # Don't reveal if email exists for security
            flash('If an account with this email exists, password reset instructions have been sent', 'info')
        
        return redirect(url_for('postgresql_auth.login'))
    
    return render_template('auth/forgot_password.html')

@auth_bp.route('/reset-password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    """Handle password reset with token"""
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    
    # Find user with valid reset token
    user = User.query.filter_by(reset_token=token).first()
    
    if not user or not user.reset_token_expires or user.reset_token_expires < datetime.utcnow():
        flash('Invalid or expired reset token. Please request a new password reset.', 'error')
        return redirect(url_for('postgresql_auth.forgot_password'))
    
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not password or not confirm_password:
            flash('Please fill in all fields', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        if password != confirm_password:
            flash('Passwords do not match', 'error')
            return render_template('auth/reset_password.html', token=token)
        
        # Validate password strength
        is_valid, error_message = validate_password(password)
        if not is_valid:
            flash(error_message, 'error')
            return render_template('auth/reset_password.html', token=token)
        
        try:
            # Update password and clear reset token
            user.set_password(password)
            user.reset_token = None
            user.reset_token_expires = None
            db.session.commit()
            
            flash('Password reset successful! Please log in with your new password.', 'success')
            return redirect(url_for('postgresql_auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Password reset failed. Please try again.', 'error')
            return render_template('auth/reset_password.html', token=token)
    
    return render_template('auth/reset_password.html', token=token)

# Subuser Management Routes
@auth_bp.route('/settings/subusers')
@login_required
def manage_subusers():
    """Manage subusers"""
    if not current_user.can_manage_subusers():
        flash('You do not have permission to manage subusers.', 'error')
        return redirect(url_for('postgresql_auth.settings'))
    
    subusers = current_user.get_all_subusers()
    available_permissions = [
        'view_inventory', 'edit_inventory', 'delete_inventory',
        'view_sales', 'create_sales', 'edit_sales', 'delete_sales',
        'view_customers', 'edit_customers', 'delete_customers',
        'view_reports', 'view_financial_data', 'manage_locations',
        'view_settings', 'edit_business_settings'
    ]
    
    return render_template('auth/manage_subusers.html', 
                         subusers=subusers, 
                         available_permissions=available_permissions)

@auth_bp.route('/settings/subusers/create', methods=['GET', 'POST'])
@login_required
def create_subuser():
    """Create a new subuser"""
    if not current_user.can_manage_subusers():
        flash('You do not have permission to manage subusers.', 'error')
        return redirect(url_for('postgresql_auth.settings'))
    
    if request.method == 'POST':
        try:
            username = request.form.get('username', '').strip()
            email = request.form.get('email', '').strip().lower()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            permissions = request.form.getlist('permissions')
            
            # Validation
            errors = []
            
            if not username:
                errors.append('Username is required')
            elif len(username) < 3:
                errors.append('Username must be at least 3 characters long')
            
            if not email:
                errors.append('Email is required')
            elif not validate_email(email):
                errors.append('Please enter a valid email address')
            
            if not password:
                errors.append('Password is required')
            else:
                is_valid, message = validate_password(password)
                if not is_valid:
                    errors.append(message)
            
            if password != confirm_password:
                errors.append('Passwords do not match')
            
            if not first_name:
                errors.append('First name is required')
            
            if not last_name:
                errors.append('Last name is required')
            
            if errors:
                for error in errors:
                    flash(error, 'error')
                return render_template('auth/create_subuser.html')
            
            # Create subuser
            subuser = current_user.create_subuser(
                username=username,
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                permissions=permissions
            )
            
            db.session.add(subuser)
            db.session.commit()
            
            flash(f'Subuser {username} created successfully!', 'success')
            return redirect(url_for('postgresql_auth.manage_subusers'))
            
        except ValueError as e:
            flash(str(e), 'error')
        except Exception as e:
            db.session.rollback()
            import logging
            logging.error(f"Subuser creation error: {str(e)}")
            flash('Failed to create subuser. Please try again.', 'error')
    
    available_permissions = [
        'view_inventory', 'edit_inventory', 'delete_inventory',
        'view_sales', 'create_sales', 'edit_sales', 'delete_sales',
        'view_customers', 'edit_customers', 'delete_customers',
        'view_reports', 'view_financial_data', 'manage_locations',
        'view_settings', 'edit_business_settings'
    ]
    
    return render_template('auth/create_subuser.html', 
                         available_permissions=available_permissions)

@auth_bp.route('/settings/subusers/<int:subuser_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_subuser(subuser_id):
    """Edit subuser permissions and details"""
    if not current_user.can_manage_subusers():
        flash('You do not have permission to manage subusers.', 'error')
        return redirect(url_for('postgresql_auth.settings'))
    
    subuser = User.query.filter_by(id=subuser_id, parent_user_id=current_user.id).first()
    if not subuser:
        flash('Subuser not found.', 'error')
        return redirect(url_for('postgresql_auth.manage_subusers'))
    
    if request.method == 'POST':
        try:
            first_name = request.form.get('first_name', '').strip()
            last_name = request.form.get('last_name', '').strip()
            active = 'active' in request.form
            permissions = request.form.getlist('permissions')
            
            # Update subuser details
            subuser.first_name = first_name
            subuser.last_name = last_name
            subuser.active = active
            subuser.set_subuser_permissions(permissions)
            subuser.updated_at = datetime.utcnow()
            
            db.session.commit()
            
            flash(f'Subuser {subuser.username} updated successfully!', 'success')
            return redirect(url_for('postgresql_auth.manage_subusers'))
            
        except Exception as e:
            db.session.rollback()
            import logging
            logging.error(f"Subuser update error: {str(e)}")
            flash('Failed to update subuser. Please try again.', 'error')
    
    available_permissions = [
        'view_inventory', 'edit_inventory', 'delete_inventory',
        'view_sales', 'create_sales', 'edit_sales', 'delete_sales',
        'view_customers', 'edit_customers', 'delete_customers',
        'view_reports', 'view_financial_data', 'manage_locations',
        'view_settings', 'edit_business_settings'
    ]
    
    return render_template('auth/edit_subuser.html', 
                         subuser=subuser, 
                         available_permissions=available_permissions)

@auth_bp.route('/settings/subusers/<int:subuser_id>/delete', methods=['POST'])
@login_required
def delete_subuser(subuser_id):
    """Delete a subuser"""
    if not current_user.can_manage_subusers():
        flash('You do not have permission to manage subusers.', 'error')
        return redirect(url_for('postgresql_auth.settings'))
    
    subuser = User.query.filter_by(id=subuser_id, parent_user_id=current_user.id).first()
    if not subuser:
        flash('Subuser not found.', 'error')
        return redirect(url_for('postgresql_auth.manage_subusers'))
    
    try:
        username = subuser.username
        db.session.delete(subuser)
        db.session.commit()
        
        flash(f'Subuser {username} deleted successfully!', 'success')
        
    except Exception as e:
        db.session.rollback()
        import logging
        logging.error(f"Subuser deletion error: {str(e)}")
        flash('Failed to delete subuser. Please try again.', 'error')
    
    return redirect(url_for('postgresql_auth.manage_subusers'))

# Blueprint will be registered in routes.py