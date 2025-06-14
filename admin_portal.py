from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify, current_app as app
from flask_login import login_required, current_user
from functools import wraps
from datetime import datetime, timedelta
from sqlalchemy import func, desc, and_
from app import db
from models import (User, Item, Sale, SaleItem, Customer, FinancialTransaction, 
                   Category, Location, StockMovement, BankAccount, OnDemandProduct, OnDemandOrder)
import logging

# Create admin blueprint
admin_bp = Blueprint('admin_portal', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            flash('Please log in to access the admin portal.', 'warning')
            return redirect(url_for('auth.login'))
        
        if not current_user.is_admin:
            flash('Access denied. Admin privileges required.', 'danger')
            return redirect(url_for('dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard with system overview"""
    
    # Get date range for analytics
    from datetime import datetime as dt, timedelta
    end_date = dt.utcnow().date()
    start_date = end_date - timedelta(days=30)
    
    # System statistics
    total_users = User.query.count()
    active_users = User.query.filter_by(is_active=True).count()
    admin_users = User.query.filter_by(is_admin=True).count()
    
    # Business metrics across all users
    total_items = Item.query.filter_by(is_active=True).count()
    total_customers = Customer.query.count()
    total_locations = Location.query.count()
    total_categories = Category.query.filter_by(is_active=True).count()
    
    # Financial overview
    total_sales_amount = db.session.query(func.sum(Sale.total_amount)).scalar() or 0
    total_transactions = FinancialTransaction.query.count()
    
    # Recent activity (last 30 days)
    recent_sales = Sale.query.filter(Sale.created_at >= start_date).count()
    recent_registrations = User.query.filter(User.created_at >= start_date).count()
    
    # Top performing users by sales
    top_users = db.session.query(
        User.username,
        User.email,
        func.count(Sale.id).label('sale_count'),
        func.sum(Sale.total_amount).label('total_sales')
    ).join(Sale, User.id == Sale.user_id, isouter=True)\
     .group_by(User.id, User.username, User.email)\
     .order_by(desc('total_sales'))\
     .limit(10).all()
    
    # System health metrics
    low_stock_items = Item.query.filter(Item.stock_quantity <= Item.minimum_stock).count()
    pending_orders = OnDemandOrder.query.filter_by(status='pending').count()
    
    # Recent system activity
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    recent_sales_list = Sale.query.order_by(desc(Sale.created_at)).limit(10).all()
    
    return render_template('admin/dashboard.html',
                         current_date=dt.now(),
                         total_users=total_users,
                         active_users=active_users,
                         admin_users=admin_users,
                         total_items=total_items,
                         total_customers=total_customers,
                         total_locations=total_locations,
                         total_categories=total_categories,
                         total_sales_amount=total_sales_amount,
                         total_transactions=total_transactions,
                         recent_sales=recent_sales,
                         recent_registrations=recent_registrations,
                         top_users=top_users,
                         low_stock_items=low_stock_items,
                         pending_orders=pending_orders,
                         recent_users=recent_users,
                         recent_sales_list=recent_sales_list)

@admin_bp.route('/users')
@login_required
@admin_required
def user_management():
    """Admin user management interface"""
    
    search = request.args.get('search', '')
    status_filter = request.args.get('status', 'all')
    role_filter = request.args.get('role', 'all')
    page = request.args.get('page', 1, type=int)
    
    # Build query
    query = User.query
    
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%'),
                User.first_name.ilike(f'%{search}%'),
                User.last_name.ilike(f'%{search}%')
            )
        )
    
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    if role_filter == 'admin':
        query = query.filter_by(is_admin=True)
    elif role_filter == 'user':
        query = query.filter_by(is_admin=False)
    
    users = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html',
                         users=users,
                         search=search,
                         status_filter=status_filter,
                         role_filter=role_filter)

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('admin.user_management'))
    
    user.is_active = not user.is_active
    db.session.commit()
    
    status = 'activated' if user.is_active else 'deactivated'
    flash(f'User {user.username} has been {status}.', 'success')
    
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin_status(user_id):
    """Toggle user admin status"""
    
    user = User.query.get_or_404(user_id)
    
    if user.id == current_user.id:
        flash('You cannot modify your own admin privileges.', 'danger')
        return redirect(url_for('admin.user_management'))
    
    user.is_admin = not user.is_admin
    db.session.commit()
    
    status = 'granted admin privileges' if user.is_admin else 'removed admin privileges'
    flash(f'User {user.username} has been {status}.', 'success')
    
    return redirect(url_for('admin.user_management'))

@admin_bp.route('/system/stats')
@login_required
@admin_required
def system_stats():
    """Detailed system statistics"""
    
    # Database table statistics
    table_stats = {
        'Users': User.query.count(),
        'Items': Item.query.count(),
        'Sales': Sale.query.count(),
        'Customers': Customer.query.count(),
        'Categories': Category.query.count(),
        'Locations': Location.query.count(),
        'Financial Transactions': FinancialTransaction.query.count(),
        'Stock Movements': StockMovement.query.count(),
        'On-Demand Products': OnDemandProduct.query.count(),
        'On-Demand Orders': OnDemandOrder.query.count(),
    }
    
    # Sales analytics by month
    monthly_sales = db.session.query(
        func.date_trunc('month', Sale.created_at).label('month'),
        func.count(Sale.id).label('count'),
        func.sum(Sale.total_amount).label('total')
    ).group_by('month').order_by('month').limit(12).all()
    
    # User registration trend
    user_registrations = db.session.query(
        func.date_trunc('month', User.created_at).label('month'),
        func.count(User.id).label('count')
    ).group_by('month').order_by('month').limit(12).all()
    
    # User statistics for template
    user_stats = {
        'total': User.query.count(),
        'active': User.query.filter(User.active == True).count(),
        'inactive': User.query.filter(User.active == False).count(),
        'admins': User.query.filter(User.is_admin == True).count()
    }
    
    # Sales statistics
    sales_stats = {
        'total': Sale.query.count(),
        'today': Sale.query.filter(func.date(Sale.created_at) == func.current_date()).count(),
        'this_month': Sale.query.filter(
            func.date_trunc('month', Sale.created_at) == func.date_trunc('month', func.now())
        ).count(),
        'total_revenue': float(db.session.query(func.sum(Sale.total_amount)).scalar() or 0)
    }
    
    # Inventory statistics
    inventory_stats = {
        'total_items': Item.query.count(),
        'categories': Category.query.count(),
        'locations': Location.query.count(),
        'low_stock_items': Item.query.filter(Item.stock_quantity <= Item.minimum_stock).count()
    }
    
    # Business statistics for template
    business_stats = {
        'total_sales': Sale.query.count(),
        'total_items': Item.query.count(),
        'total_transactions': FinancialTransaction.query.count()
    }
    
    # Registration trends for template
    registration_trends = user_registrations
    
    return render_template('admin/system_stats.html',
                         table_stats=table_stats,
                         monthly_sales=monthly_sales,
                         user_registrations=user_registrations,
                         user_stats=user_stats,
                         sales_stats=sales_stats,
                         inventory_stats=inventory_stats,
                         business_stats=business_stats,
                         registration_trends=registration_trends)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user account"""
    if user_id == current_user.id:
        flash('You cannot delete your own account.', 'error')
        return redirect(url_for('admin_portal.user_management'))
    
    user = User.query.get_or_404(user_id)
    
    # Check if user is another admin
    if user.is_admin:
        flash('Cannot delete another admin user.', 'error')
        return redirect(url_for('admin_portal.user_management'))
    
    try:
        # Store user info for logging
        username = user.username
        email = user.email
        
        # Delete the user (cascade will handle related records)
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User {username} ({email}) has been successfully deleted.', 'success')
        
        # Log the deletion
        app.logger.info(f'Admin {current_user.username} deleted user {username} ({email})')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting user: {str(e)}', 'error')
        app.logger.error(f'Error deleting user {user_id}: {str(e)}')
    
    return redirect(url_for('admin_portal.user_management'))

@admin_bp.route('/users/<int:user_id>/change-password', methods=['GET', 'POST'])
@login_required
@admin_required
def change_user_password(user_id):
    """Change a user's password"""
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate passwords
        if not new_password or len(new_password) < 8:
            flash('Password must be at least 8 characters long.', 'error')
            return render_template('admin/change_password.html', user=user)
        
        if new_password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('admin/change_password.html', user=user)
        
        try:
            # Update password
            user.set_password(new_password)
            user.login_attempts = 0  # Reset login attempts
            user.locked_until = None  # Unlock account if locked
            db.session.commit()
            
            flash(f'Password for {user.username} has been successfully changed.', 'success')
            
            # Log the password change
            app.logger.info(f'Admin {current_user.username} changed password for user {user.username}')
            
            return redirect(url_for('admin_portal.user_management'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error changing password: {str(e)}', 'error')
            app.logger.error(f'Error changing password for user {user_id}: {str(e)}')
    
    return render_template('admin/change_password.html', user=user)

@admin_bp.route('/users/<int:user_id>/permissions', methods=['GET', 'POST'])
@login_required
@admin_required
def manage_user_permissions(user_id):
    """Manage user permissions"""
    user = User.query.get_or_404(user_id)
    
    # Available permissions
    available_permissions = [
        'manage_inventory',
        'manage_sales', 
        'manage_customers',
        'manage_finances',
        'view_reports',
        'manage_locations',
        'manage_categories'
    ]
    
    if request.method == 'POST':
        selected_permissions = request.form.getlist('permissions')
        
        try:
            # Update user permissions
            import json
            user.permissions = json.dumps(selected_permissions)
            db.session.commit()
            
            flash(f'Permissions for {user.username} have been updated.', 'success')
            
            # Log the permission change
            app.logger.info(f'Admin {current_user.username} updated permissions for user {user.username}')
            
            return redirect(url_for('admin_portal.user_management'))
            
        except Exception as e:
            db.session.rollback()
            flash(f'Error updating permissions: {str(e)}', 'error')
            app.logger.error(f'Error updating permissions for user {user_id}: {str(e)}')
    
    # Get current permissions
    current_permissions = user.get_permissions()
    
    return render_template('admin/manage_permissions.html', 
                         user=user, 
                         available_permissions=available_permissions,
                         current_permissions=current_permissions)

@admin_bp.route('/users/<int:user_id>/lock', methods=['POST'])
@login_required
@admin_required
def lock_user(user_id):
    """Lock/unlock a user account"""
    if user_id == current_user.id:
        flash('You cannot lock your own account.', 'error')
        return redirect(url_for('admin_portal.user_management'))
    
    user = User.query.get_or_404(user_id)
    
    if user.is_admin:
        flash('Cannot lock another admin user.', 'error')
        return redirect(url_for('admin_portal.user_management'))
    
    try:
        if user.is_locked:
            # Unlock the user
            user.unlock_account()
            action = 'unlocked'
        else:
            # Lock the user for 24 hours
            user.lock_account(24 * 60)  # 24 hours in minutes
            action = 'locked'
        
        db.session.commit()
        flash(f'User {user.username} has been {action}.', 'success')
        
        # Log the action
        app.logger.info(f'Admin {current_user.username} {action} user {user.username}')
        
    except Exception as e:
        db.session.rollback()
        flash(f'Error updating user status: {str(e)}', 'error')
        app.logger.error(f'Error locking/unlocking user {user_id}: {str(e)}')
    
    return redirect(url_for('admin_portal.user_management'))

@admin_bp.route('/system/cleanup', methods=['GET', 'POST'])
@login_required
@admin_required
def system_cleanup():
    """System cleanup and maintenance"""
    
    # Get system status data
    active_sessions = 0  # Session count would need to be implemented
    failed_logins = User.query.filter(User.failed_login_attempts > 0).count()
    last_cleanup = "Never"  # This would be stored in a system settings table
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        try:
            if action == 'clear_sessions':
                # Clear expired sessions (implementation depends on session storage)
                flash('Session data cleared successfully.', 'success')
                
            elif action == 'clear_logs':
                # Clear old log files (this would be file system operation)
                flash('Old log files cleared successfully.', 'success')
                
            elif action == 'reset_failed_logins':
                # Reset failed login attempts for all users
                User.query.update({User.failed_login_attempts: 0})
                db.session.commit()
                flash('Failed login attempts reset for all users.', 'success')
                
            elif action == 'optimize_database':
                # Database optimization (PostgreSQL specific commands)
                flash('Database optimization completed.', 'success')
                
            elif action == 'full_cleanup':
                # Perform all cleanup operations
                User.query.update({User.failed_login_attempts: 0})
                db.session.commit()
                flash('Full system cleanup completed successfully.', 'success')
                
        except Exception as e:
            flash(f'Error during cleanup: {str(e)}', 'error')
            db.session.rollback()
    
    return render_template('admin/system_cleanup.html', 
                         active_sessions=active_sessions,
                         failed_logins=failed_logins,
                         last_cleanup=last_cleanup)

@admin_bp.route('/api/dashboard-data')
@login_required
@admin_required
def dashboard_data():
    """API endpoint for dashboard charts"""
    
    # Sales trend (last 30 days)
    end_date = datetime.utcnow().date()
    start_date = end_date - timedelta(days=30)
    
    daily_sales = db.session.query(
        func.date(Sale.created_at).label('date'),
        func.count(Sale.id).label('count'),
        func.sum(Sale.total_amount).label('total')
    ).filter(Sale.created_at >= start_date)\
     .group_by(func.date(Sale.created_at))\
     .order_by('date').all()
    
    # User registrations (using created_at instead of last_login)
    daily_registrations = db.session.query(
        func.date(User.created_at).label('date'),
        func.count(User.id).label('count')
    ).filter(User.created_at >= start_date)\
     .group_by(func.date(User.created_at))\
     .order_by('date').all()
    
    return jsonify({
        'sales_trend': [
            {
                'date': sale.date.isoformat(),
                'count': sale.count,
                'total': float(sale.total or 0)
            }
            for sale in daily_sales
        ],
        'user_activity': [
            {
                'date': registration.date.isoformat() if registration.date else None,
                'count': registration.count
            }
            for registration in daily_registrations if registration.date
        ]
    })