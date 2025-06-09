from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from sqlalchemy import func, desc, and_
from functools import wraps
from app import db
from models import User, Sale, Item, FinancialTransaction
from datetime import datetime, timedelta
import logging

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    """Decorator to require admin access"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'error')
            return redirect(url_for('dashboard'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route('/')
@login_required
@admin_required
def admin_dashboard():
    """Admin dashboard with system overview"""
    try:
        # Get system statistics
        total_users = User.query.count()
        active_users = User.query.filter_by(active=True).count()
        admin_users = User.query.filter_by(is_admin=True).count()
        
        # Recent registrations (last 30 days)
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_registrations = User.query.filter(User.created_at >= thirty_days_ago).count()
        
        # Get recent users
        recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
        
        # System metrics
        total_sales = Sale.query.count()
        total_items = Item.query.count()
        total_transactions = FinancialTransaction.query.count()
        
        return render_template('admin/dashboard.html',
                             total_users=total_users,
                             active_users=active_users,
                             admin_users=admin_users,
                             recent_registrations=recent_registrations,
                             recent_users=recent_users,
                             total_sales=total_sales,
                             total_items=total_items,
                             total_transactions=total_transactions)
    except Exception as e:
        logging.error(f"Admin dashboard error: {str(e)}")
        flash('Error loading admin dashboard', 'error')
        return redirect(url_for('dashboard'))

@admin_bp.route('/users')
@login_required
@admin_required
def manage_users():
    """Manage all users in the system"""
    try:
        page = request.args.get('page', 1, type=int)
        search = request.args.get('search', '', type=str)
        status = request.args.get('status', '', type=str)
        
        # Build query
        query = User.query
        
        if search:
            query = query.filter(
                User.username.contains(search) |
                User.email.contains(search) |
                User.first_name.contains(search) |
                User.last_name.contains(search) |
                User.shop_name.contains(search)
            )
        
        if status == 'active':
            query = query.filter_by(active=True)
        elif status == 'inactive':
            query = query.filter_by(active=False)
        elif status == 'admin':
            query = query.filter_by(is_admin=True)
        
        # Paginate results
        users = query.order_by(desc(User.created_at)).paginate(
            page=page, per_page=20, error_out=False
        )
        
        return render_template('admin/users.html', 
                             users=users, 
                             search=search, 
                             status=status)
    except Exception as e:
        logging.error(f"Manage users error: {str(e)}")
        flash('Error loading users', 'error')
        return redirect(url_for('admin.admin_dashboard'))

@admin_bp.route('/users/<int:user_id>')
@login_required
@admin_required
def user_details(user_id):
    """View detailed information about a specific user"""
    try:
        user = User.query.get_or_404(user_id)
        
        # Get user statistics
        user_sales = Sale.query.filter_by(user_id=user_id).count()
        user_items = Item.query.filter_by(user_id=user_id).count()
        user_transactions = FinancialTransaction.query.filter_by(user_id=user_id).count()
        
        # Recent activity
        recent_sales = Sale.query.filter_by(user_id=user_id).order_by(desc(Sale.created_at)).limit(5).all()
        recent_items = Item.query.filter_by(user_id=user_id).order_by(desc(Item.created_at)).limit(5).all()
        
        return render_template('admin/user_details.html',
                             user=user,
                             user_sales=user_sales,
                             user_items=user_items,
                             user_transactions=user_transactions,
                             recent_sales=recent_sales,
                             recent_items=recent_items)
    except Exception as e:
        logging.error(f"User details error: {str(e)}")
        flash('Error loading user details', 'error')
        return redirect(url_for('admin.manage_users'))

@admin_bp.route('/users/<int:user_id>/toggle-status', methods=['POST'])
@login_required
@admin_required
def toggle_user_status(user_id):
    """Toggle user active status"""
    try:
        user = User.query.get_or_404(user_id)
        
        if user.id == current_user.id:
            flash('Cannot deactivate your own account', 'error')
            return redirect(url_for('admin.user_details', user_id=user_id))
        
        user.active = not user.active
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = 'activated' if user.active else 'deactivated'
        flash(f'User {user.username} has been {status}', 'success')
        
    except Exception as e:
        logging.error(f"Toggle user status error: {str(e)}")
        flash('Error updating user status', 'error')
        db.session.rollback()
    
    return redirect(url_for('admin.user_details', user_id=user_id))

@admin_bp.route('/users/<int:user_id>/toggle-admin', methods=['POST'])
@login_required
@admin_required
def toggle_admin_status(user_id):
    """Toggle user admin status"""
    try:
        user = User.query.get_or_404(user_id)
        
        if user.id == current_user.id:
            flash('Cannot modify your own admin status', 'error')
            return redirect(url_for('admin.user_details', user_id=user_id))
        
        user.is_admin = not user.is_admin
        user.role = 'admin' if user.is_admin else 'user'
        user.updated_at = datetime.utcnow()
        db.session.commit()
        
        status = 'granted' if user.is_admin else 'revoked'
        flash(f'Admin privileges {status} for {user.username}', 'success')
        
    except Exception as e:
        logging.error(f"Toggle admin status error: {str(e)}")
        flash('Error updating admin status', 'error')
        db.session.rollback()
    
    return redirect(url_for('admin.user_details', user_id=user_id))

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_user(user_id):
    """Edit user information"""
    try:
        user = User.query.get_or_404(user_id)
        
        if request.method == 'POST':
            # Update user information
            user.first_name = request.form.get('first_name', '').strip()
            user.last_name = request.form.get('last_name', '').strip()
            user.email = request.form.get('email', '').strip().lower()
            user.phone = request.form.get('phone', '').strip()
            user.shop_name = request.form.get('shop_name', '').strip()
            user.product_categories = request.form.get('product_categories', '').strip()
            user.updated_at = datetime.utcnow()
            
            # Validate email uniqueness
            existing_user = User.query.filter(User.email == user.email, User.id != user.id).first()
            if existing_user:
                flash('Email already exists', 'error')
                return render_template('admin/edit_user.html', user=user)
            
            db.session.commit()
            flash('User information updated successfully', 'success')
            return redirect(url_for('admin.user_details', user_id=user_id))
        
        return render_template('admin/edit_user.html', user=user)
        
    except Exception as e:
        logging.error(f"Edit user error: {str(e)}")
        flash('Error updating user information', 'error')
        db.session.rollback()
        return redirect(url_for('admin.user_details', user_id=user_id))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_user(user_id):
    """Delete a user (with confirmation)"""
    try:
        user = User.query.get_or_404(user_id)
        
        if user.id == current_user.id:
            flash('Cannot delete your own account', 'error')
            return redirect(url_for('admin.user_details', user_id=user_id))
        
        # Check if user has associated data
        has_sales = Sale.query.filter_by(user_id=user_id).count() > 0
        has_items = Item.query.filter_by(user_id=user_id).count() > 0
        has_transactions = FinancialTransaction.query.filter_by(user_id=user_id).count() > 0
        
        if has_sales or has_items or has_transactions:
            flash('Cannot delete user with associated business data. Deactivate instead.', 'error')
            return redirect(url_for('admin.user_details', user_id=user_id))
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        flash(f'User {username} has been deleted', 'success')
        return redirect(url_for('admin.manage_users'))
        
    except Exception as e:
        logging.error(f"Delete user error: {str(e)}")
        flash('Error deleting user', 'error')
        db.session.rollback()
        return redirect(url_for('admin.user_details', user_id=user_id))

@admin_bp.route('/system-stats')
@login_required
@admin_required
def system_stats():
    """View detailed system statistics"""
    try:
        # User statistics
        user_stats = {
            'total': User.query.count(),
            'active': User.query.filter_by(active=True).count(),
            'inactive': User.query.filter_by(active=False).count(),
            'admins': User.query.filter_by(is_admin=True).count(),
        }
        
        # Business statistics
        business_stats = {
            'total_sales': Sale.query.count(),
            'total_items': Item.query.count(),
            'total_transactions': FinancialTransaction.query.count(),
        }
        
        # Registration trends (last 12 months)
        registration_trends = []
        for i in range(12):
            month_start = datetime.utcnow().replace(day=1) - timedelta(days=30*i)
            month_end = (month_start + timedelta(days=32)).replace(day=1) - timedelta(days=1)
            count = User.query.filter(
                User.created_at >= month_start,
                User.created_at <= month_end
            ).count()
            registration_trends.append({
                'month': month_start.strftime('%Y-%m'),
                'count': count
            })
        
        registration_trends.reverse()
        
        return render_template('admin/system_stats.html',
                             user_stats=user_stats,
                             business_stats=business_stats,
                             registration_trends=registration_trends)
                             
    except Exception as e:
        logging.error(f"System stats error: {str(e)}")
        flash('Error loading system statistics', 'error')
        return redirect(url_for('admin.admin_dashboard'))