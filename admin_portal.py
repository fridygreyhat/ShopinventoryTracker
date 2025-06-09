from flask import Blueprint, render_template, redirect, url_for, flash, request, session, jsonify
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
    end_date = datetime.utcnow().date()
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
    
    from datetime import datetime
    
    return render_template('admin/dashboard.html',
                         current_date=datetime.now(),
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
    
    return render_template('admin/system_stats.html',
                         table_stats=table_stats,
                         monthly_sales=monthly_sales,
                         user_registrations=user_registrations)

@admin_bp.route('/system/cleanup', methods=['GET', 'POST'])
@login_required
@admin_required
def system_cleanup():
    """System cleanup and maintenance"""
    
    if request.method == 'POST':
        cleanup_type = request.form.get('cleanup_type')
        
        try:
            if cleanup_type == 'inactive_users':
                # Find users inactive for 6+ months
                cutoff_date = datetime.utcnow() - timedelta(days=180)
                inactive_count = User.query.filter(
                    User.last_login < cutoff_date,
                    User.is_admin == False
                ).count()
                flash(f'Found {inactive_count} inactive users (6+ months).', 'info')
                
            elif cleanup_type == 'old_stock_movements':
                # Find stock movements older than 1 year
                cutoff_date = datetime.utcnow() - timedelta(days=365)
                old_movements = StockMovement.query.filter(
                    StockMovement.created_at < cutoff_date
                ).count()
                flash(f'Found {old_movements} old stock movements (1+ year).', 'info')
                
            elif cleanup_type == 'empty_categories':
                # Find categories with no items
                empty_categories = Category.query.outerjoin(Item).group_by(Category.id).having(func.count(Item.id) == 0).count()
                flash(f'Found {empty_categories} empty categories.', 'info')
                
        except Exception as e:
            flash(f'Error during cleanup: {str(e)}', 'danger')
    
    return render_template('admin/system_cleanup.html')

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
    
    # User activity
    daily_logins = db.session.query(
        func.date(User.last_login).label('date'),
        func.count(User.id).label('count')
    ).filter(User.last_login >= start_date)\
     .group_by(func.date(User.last_login))\
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
                'date': login.date.isoformat() if login.date else None,
                'count': login.count
            }
            for login in daily_logins if login.date
        ]
    })