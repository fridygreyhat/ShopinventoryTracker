# Clean Firebase-Only Business Management System
import os
import sys
import logging
from datetime import datetime, timedelta
from functools import wraps
from flask import Flask, render_template, request, jsonify, session, redirect, url_for

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Import Firebase components
from firebase_config import firebase_config
from firebase_adapter import firebase_adapter
from firebase_models import UserModel, ItemModel, SaleModel, CustomerModel, CategoryModel

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Initialize Firebase
if not firebase_config.initialize_firebase():
    logger.error("❌ Firebase initialization failed")
    sys.exit(1)

logger.info("✅ Clean Firebase-only system initialized")

# Authentication decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Context processor
@app.context_processor
def inject_user():
    def get_current_user():
        user_id = session.get('user_id')
        if user_id:
            return firebase_adapter.get_user_by_id(user_id)
        return None
    return dict(get_current_user=get_current_user)

# === WEB ROUTES ===

@app.route('/')
def index():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login')
def login():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register')
def register():
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')

@app.route('/inventory')
@login_required
def inventory():
    return render_template('inventory.html')

@app.route('/sales')
@login_required
def sales():
    return render_template('sales.html')

@app.route('/customers')
@login_required
def customers():
    return render_template('customers.html')

@app.route('/account')
@login_required
def account():
    return render_template('account.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/logout')
@login_required  
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/categories')
@login_required
def categories():
    return render_template('categories.html')

@app.route('/installments')
@login_required
def installments():
    return render_template('installments.html')

@app.route('/analytics')
@login_required
def analytics():
    return render_template('analytics.html')

@app.route('/margin')
@login_required
def margin():
    return render_template('margin.html')

@app.route('/admin')
@login_required
def admin():
    return render_template('admin.html')

@app.route('/admin/users')
@login_required
def admin_users():
    return render_template('admin_users.html')

@app.route('/admin/system')
@login_required
def admin_system():
    return render_template('admin_system.html')

@app.route('/barcode-scanner')
@login_required
def barcode_scanner():
    return render_template('barcode_scanner.html')

@app.route('/price-rules')
@login_required
def price_rules():
    return render_template('price_rules.html')

@app.route('/smart-inventory')
@login_required
def smart_inventory():
    return render_template('smart_inventory.html')

@app.route('/accounting')
@login_required
def accounting():
    return render_template('accounting.html')

@app.route('/finance')
@login_required
def finance():
    return render_template('finance.html')

@app.route('/on-demand')
@login_required
def on_demand():
    return render_template('on_demand.html')

# === AUTHENTICATION API ===

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        # Authenticate with Firebase
        user = firebase_adapter.authenticate_user(email, password)
        if user:
            session['user_id'] = user['id']
            session['email'] = user['email']
            session.permanent = True
            
            # Update last login
            firebase_adapter.service.update_user_last_login(user['id'])
            
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user['id'],
                    'email': user['email'],
                    'first_name': user.get('first_name', ''),
                    'last_name': user.get('last_name', ''),
                    'username': user.get('username', '')
                }
            })
        else:
            return jsonify({'error': 'Invalid email or password'}), 401
            
    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    try:
        data = request.get_json()
        required_fields = ['email', 'password', 'first_name', 'last_name']
        
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'{field} is required'}), 400
        
        # Create user with Firebase
        user_data = UserModel.create_user_data(
            email=data['email'],
            first_name=data['first_name'],
            last_name=data['last_name'],
            username=data.get('username')
        )
        
        user_id = firebase_adapter.create_user(user_data, data['password'])
        if user_id:
            return jsonify({
                'success': True,
                'message': 'Registration successful',
                'user_id': user_id
            })
        else:
            return jsonify({'error': 'Registration failed'}), 500
            
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

# === DASHBOARD API ===

@app.route('/api/dashboard/summary')
@login_required
def get_dashboard_summary():
    try:
        user_id = session.get('user_id')
        
        # Get inventory metrics
        items_data = firebase_adapter.get_items_by_user(user_id)
        total_items = len(items_data)
        total_stock = sum(item.get('stock_quantity', 0) for item in items_data)
        low_stock_items = len([item for item in items_data 
                             if item.get('stock_quantity', 0) <= item.get('minimum_stock', 0)])
        
        inventory_value = sum(
            item.get('stock_quantity', 0) * item.get('buying_price', 0) 
            for item in items_data
        )
        
        # Get sales metrics
        sales_data = firebase_adapter.get_sales_by_user(user_id)
        total_sales = len(sales_data)
        total_revenue = sum(float(sale.get('total_amount', 0)) for sale in sales_data)
        
        # Get customer count
        customers_data = firebase_adapter.get_customers_by_user(user_id)
        total_customers = len(customers_data)
        
        return jsonify({
            'inventory': {
                'total_items': total_items,
                'total_stock': total_stock,
                'low_stock_items': low_stock_items,
                'inventory_value': inventory_value
            },
            'sales': {
                'total_sales': total_sales,
                'total_revenue': total_revenue
            },
            'customers': {
                'total_customers': total_customers
            },
            'success': True
        })
        
    except Exception as e:
        logger.error(f"Dashboard summary error: {str(e)}")
        return jsonify({'error': 'Failed to load dashboard data'}), 500

# === INVENTORY API ===

@app.route('/api/items', methods=['GET'])
@login_required
def get_items():
    try:
        user_id = session.get('user_id')
        items = firebase_adapter.get_items_by_user(user_id)
        return jsonify(items)
    except Exception as e:
        logger.error(f"Get items error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve items'}), 500

@app.route('/api/items', methods=['POST'])
@login_required
def create_item():
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'Item name is required'}), 400
        
        item_data = ItemModel.create_item_data(
            name=data['name'],
            user_id=user_id,
            **data
        )
        
        item_id = firebase_adapter.create_item(item_data)
        if item_id:
            return jsonify({'success': True, 'item_id': item_id, 'message': 'Item created successfully'})
        else:
            return jsonify({'error': 'Failed to create item'}), 500
            
    except Exception as e:
        logger.error(f"Create item error: {str(e)}")
        return jsonify({'error': 'Failed to create item'}), 500

@app.route('/api/items/<item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        success = firebase_adapter.update_item(item_id, data, user_id)
        if success:
            return jsonify({'success': True, 'message': 'Item updated successfully'})
        else:
            return jsonify({'error': 'Failed to update item'}), 500
            
    except Exception as e:
        logger.error(f"Update item error: {str(e)}")
        return jsonify({'error': 'Failed to update item'}), 500

@app.route('/api/items/<item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    try:
        user_id = session.get('user_id')
        success = firebase_adapter.delete_item(item_id, user_id)
        if success:
            return jsonify({'success': True, 'message': 'Item deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete item'}), 500
            
    except Exception as e:
        logger.error(f"Delete item error: {str(e)}")
        return jsonify({'error': 'Failed to delete item'}), 500

# === SALES API ===

@app.route('/api/sales', methods=['GET'])
@login_required
def get_sales():
    try:
        user_id = session.get('user_id')
        sales = firebase_adapter.get_sales_by_user(user_id)
        return jsonify(sales)
    except Exception as e:
        logger.error(f"Get sales error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve sales'}), 500

@app.route('/api/sales', methods=['POST'])
@login_required
def create_sale():
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data.get('sale_items') or not data.get('total_amount'):
            return jsonify({'error': 'Sale items and total amount are required'}), 400
        
        sale_data = SaleModel.create_sale_data(
            user_id=user_id,
            total_amount=data['total_amount'],
            sale_items=data['sale_items'],
            **data
        )
        
        sale_id = firebase_adapter.create_sale(sale_data)
        if sale_id:
            return jsonify({'success': True, 'sale_id': sale_id, 'message': 'Sale created successfully'})
        else:
            return jsonify({'error': 'Failed to create sale'}), 500
            
    except Exception as e:
        logger.error(f"Create sale error: {str(e)}")
        return jsonify({'error': 'Failed to create sale'}), 500

# === CATEGORIES API ===

@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    try:
        user_id = session.get('user_id')
        categories = firebase_adapter.get_categories_by_user(user_id)
        
        # Transform categories to match expected frontend format
        formatted_categories = []
        category_map = {}
        
        # First pass: create category map and identify parents
        for category in categories:
            if isinstance(category, dict):
                cat_data = category
            else:
                cat_data = category.to_dict() if hasattr(category, 'to_dict') else category.__dict__
            
            cat_data['subcategories'] = []
            category_map[cat_data.get('id')] = cat_data
            
            # If no parent_id, it's a main category
            if not cat_data.get('parent_id'):
                formatted_categories.append(cat_data)
        
        # Second pass: attach subcategories to their parents
        for category in categories:
            if isinstance(category, dict):
                cat_data = category
            else:
                cat_data = category.to_dict() if hasattr(category, 'to_dict') else category.__dict__
            
            parent_id = cat_data.get('parent_id')
            if parent_id and parent_id in category_map:
                category_map[parent_id]['subcategories'].append(cat_data)
        
        return jsonify(formatted_categories)
    except Exception as e:
        logger.error(f"Get categories error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve categories'}), 500

@app.route('/api/categories', methods=['POST'])
@login_required
def create_category():
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'Category name is required'}), 400
        
        category_data = CategoryModel.create_category_data(
            name=data['name'],
            user_id=user_id,
            description=data.get('description', ''),
            parent_id=data.get('parent_id'),
            icon=data.get('icon', 'fas fa-folder'),
            color=data.get('color', '#007bff'),
            is_active=True
        )
        
        category_id = firebase_adapter.create_category(category_data, user_id)
        if category_id:
            return jsonify({'success': True, 'category_id': category_id, 'message': 'Category created successfully'})
        else:
            return jsonify({'error': 'Failed to create category'}), 500
            
    except Exception as e:
        logger.error(f"Create category error: {str(e)}")
        return jsonify({'error': 'Failed to create category'}), 500

@app.route('/api/categories/<category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        # Update category in Firebase
        success = firebase_adapter.service.update_category(category_id, data, user_id)
        if success:
            return jsonify({'success': True, 'message': 'Category updated successfully'})
        else:
            return jsonify({'error': 'Failed to update category'}), 500
            
    except Exception as e:
        logger.error(f"Update category error: {str(e)}")
        return jsonify({'error': 'Failed to update category'}), 500

@app.route('/api/categories/<category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    try:
        user_id = session.get('user_id')
        success = firebase_adapter.service.delete_category(category_id, user_id)
        if success:
            return jsonify({'success': True, 'message': 'Category deleted successfully'})
        else:
            return jsonify({'error': 'Failed to delete category'}), 500
            
    except Exception as e:
        logger.error(f"Delete category error: {str(e)}")
        return jsonify({'error': 'Failed to delete category'}), 500

@app.route('/api/categories/<category_id>/subcategories', methods=['POST'])
@login_required
def create_subcategory(category_id):
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'Subcategory name is required'}), 400
        
        # Create subcategory with parent_id set
        subcategory_data = CategoryModel.create_category_data(
            name=data['name'],
            user_id=user_id,
            description=data.get('description', ''),
            parent_id=category_id,
            is_active=True
        )
        
        subcategory_id = firebase_adapter.create_category(subcategory_data, user_id)
        if subcategory_id:
            return jsonify({'success': True, 'subcategory_id': subcategory_id, 'message': 'Subcategory created successfully'})
        else:
            return jsonify({'error': 'Failed to create subcategory'}), 500
            
    except Exception as e:
        logger.error(f"Create subcategory error: {str(e)}")
        return jsonify({'error': 'Failed to create subcategory'}), 500

# === CUSTOMERS API ===

@app.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    try:
        user_id = session.get('user_id')
        customers = firebase_adapter.get_customers_by_user(user_id)
        return jsonify(customers)
    except Exception as e:
        logger.error(f"Get customers error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve customers'}), 500

@app.route('/api/customers', methods=['POST'])
@login_required
def create_customer():
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if not data.get('name'):
            return jsonify({'error': 'Customer name is required'}), 400
        
        customer_data = CustomerModel.create_customer_data(
            name=data['name'],
            user_id=user_id,
            **data
        )
        
        customer_id = firebase_adapter.create_customer(customer_data)
        if customer_id:
            return jsonify({'success': True, 'customer_id': customer_id, 'message': 'Customer created successfully'})
        else:
            return jsonify({'error': 'Failed to create customer'}), 500
            
    except Exception as e:
        logger.error(f"Create customer error: {str(e)}")
        return jsonify({'error': 'Failed to create customer'}), 500

# === DEBUG ROUTES ===

@app.route('/debug/firebase-status')
def debug_firebase_status():
    try:
        status = {
            'firebase_initialized': firebase_config.initialized,
            'project_id': firebase_config.db.project if firebase_config.db else None,
            'collections_accessible': False,
            'auth_working': False,
            'user_session': session.get('user_id') is not None
        }
        
        # Test database access
        try:
            collections = list(firebase_config.db.collections())
            status['collections_accessible'] = True
            status['collection_count'] = len(collections)
        except Exception as e:
            status['db_error'] = str(e)
        
        # Test auth
        try:
            from firebase_admin import auth
            test_user = firebase_adapter.get_user_by_id(session.get('user_id', 'test'))
            status['auth_working'] = True
        except Exception as e:
            status['auth_error'] = str(e)
        
        return jsonify(status)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)