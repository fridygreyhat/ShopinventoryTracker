from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
from functools import wraps
import logging
import os

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# In-memory data storage (replace with your preferred database)
users_db = {}
items_db = {}
sales_db = {}
customers_db = {}
categories_db = {}

logger.info("✅ Simple Flask application initialized without Firebase")

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
        if user_id and user_id in users_db:
            return users_db[user_id]
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
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Simple authentication check (replace with your logic)
        user_found = None
        for user_id, user_data in users_db.items():
            if user_data.get('email') == email and user_data.get('password') == password:
                user_found = user_data
                break

        if user_found:
            session['user_id'] = user_found['id']
            session['email'] = user_found['email']
            session.permanent = True

            logger.info(f"Successful login for: {email}")
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user_found['id'],
                    'email': user_found['email'],
                    'first_name': user_found.get('first_name', ''),
                    'last_name': user_found.get('last_name', ''),
                    'username': user_found.get('username', '')
                }
            })
        else:
            return jsonify({'error': 'Invalid email or password'}), 401

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': 'Authentication failed. Please try again.'}), 500

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

        # Check if user already exists
        email = data['email'].strip().lower()
        for user_data in users_db.values():
            if user_data.get('email') == email:
                return jsonify({'error': 'Email already exists'}), 400

        # Create new user
        user_id = f"user_{len(users_db) + 1}"
        user_data = {
            'id': user_id,
            'email': email,
            'password': data['password'],  # In production, hash this!
            'first_name': data['first_name'],
            'last_name': data['last_name'],
            'username': data.get('username', email.split('@')[0]),
            'created_at': datetime.now().isoformat()
        }

        users_db[user_id] = user_data

        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user_id': user_id
        })

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

# === DASHBOARD API ===

@app.route('/api/dashboard/summary')
@login_required
def get_dashboard_summary():
    try:
        user_id = session.get('user_id')

        # Get user's data
        user_items = [item for item in items_db.values() if item.get('user_id') == user_id]
        user_sales = [sale for sale in sales_db.values() if sale.get('user_id') == user_id]
        user_customers = [customer for customer in customers_db.values() if customer.get('user_id') == user_id]

        # Calculate metrics
        total_items = len(user_items)
        total_stock = sum(item.get('stock_quantity', 0) for item in user_items)
        low_stock_items = len([item for item in user_items 
                             if item.get('stock_quantity', 0) <= item.get('minimum_stock', 0)])

        inventory_value = sum(
            item.get('stock_quantity', 0) * item.get('buying_price', 0) 
            for item in user_items
        )

        total_sales = len(user_sales)
        total_revenue = sum(float(sale.get('total_amount', 0)) for sale in user_sales)
        total_customers = len(user_customers)

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
        user_items = [item for item in items_db.values() if item.get('user_id') == user_id]
        return jsonify(user_items)
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

        item_id = f"item_{len(items_db) + 1}"
        item_data = {
            'id': item_id,
            'user_id': user_id,
            'name': data['name'],
            'description': data.get('description', ''),
            'category': data.get('category', 'General'),
            'stock_quantity': int(data.get('stock_quantity', 0)),
            'minimum_stock': int(data.get('minimum_stock', 0)),
            'buying_price': float(data.get('buying_price', 0.0)),
            'retail_price': float(data.get('retail_price', 0.0)),
            'sku': data.get('sku', ''),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'is_active': True
        }

        items_db[item_id] = item_data

        return jsonify({'success': True, 'item_id': item_id, 'message': 'Item created successfully'})

    except Exception as e:
        logger.error(f"Create item error: {str(e)}")
        return jsonify({'error': 'Failed to create item'}), 500

@app.route('/api/items/<item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if item_id in items_db and items_db[item_id]['user_id'] == user_id:
            for key, value in data.items():
                items_db[item_id][key] = value
            items_db[item_id]['updated_at'] = datetime.now().isoformat()
            return jsonify({'success': True, 'message': 'Item updated successfully'})
        else:
            return jsonify({'error': 'Item not found or unauthorized'}), 404
            
    except Exception as e:
        logger.error(f"Update item error: {str(e)}")
        return jsonify({'error': 'Failed to update item'}), 500

@app.route('/api/items/<item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    try:
        user_id = session.get('user_id')
        if item_id in items_db and items_db[item_id]['user_id'] == user_id:
            del items_db[item_id]
            return jsonify({'success': True, 'message': 'Item deleted successfully'})
        else:
            return jsonify({'error': 'Item not found or unauthorized'}), 404
            
    except Exception as e:
        logger.error(f"Delete item error: {str(e)}")
        return jsonify({'error': 'Failed to delete item'}), 500

# === SALES API ===

@app.route('/api/sales', methods=['GET'])
@login_required
def get_sales():
    try:
        user_id = session.get('user_id')
        user_sales = [sale for sale in sales_db.values() if sale.get('user_id') == user_id]
        return jsonify(user_sales)
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

        sale_id = f"sale_{len(sales_db) + 1}"
        sale_data = {
            'id': sale_id,
            'user_id': user_id,
            'total_amount': float(data['total_amount']),
            'sale_items': data['sale_items'],
            'customer_name': data.get('customer_name', 'Walk-in Customer'),
            'payment_type': data.get('payment_type', 'cash'),
            'created_at': datetime.now().isoformat()
        }

        sales_db[sale_id] = sale_data

        return jsonify({'success': True, 'sale_id': sale_id, 'message': 'Sale created successfully'})

    except Exception as e:
        logger.error(f"Create sale error: {str(e)}")
        return jsonify({'error': 'Failed to create sale'}), 500

# === CATEGORIES API ===

@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    try:
        user_id = session.get('user_id')
        user_categories = [cat for cat in categories_db.values() if cat.get('user_id') == user_id]
        
        formatted_categories = []
        category_map = {}
        
        # First pass: create category map and identify parents
        for category in user_categories:
            category['subcategories'] = []
            category_map[category.get('id')] = category
            if not category.get('parent_id'):
                formatted_categories.append(category)

        # Second pass: attach subcategories to their parents
        for category in user_categories:
            parent_id = category.get('parent_id')
            if parent_id and parent_id in category_map:
                category_map[parent_id]['subcategories'].append(category)

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

        category_id = f"cat_{len(categories_db) + 1}"
        category_data = {
            'id': category_id,
            'user_id': user_id,
            'name': data['name'],
            'description': data.get('description', ''),
            'parent_id': data.get('parent_id'),
            'icon': data.get('icon', 'fas fa-folder'),
            'color': data.get('color', '#007bff'),
            'is_active': True,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }

        categories_db[category_id] = category_data

        return jsonify({'success': True, 'category_id': category_id, 'message': 'Category created successfully'})

    except Exception as e:
        logger.error(f"Create category error: {str(e)}")
        return jsonify({'error': 'Failed to create category'}), 500

@app.route('/api/categories/<category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if category_id in categories_db and categories_db[category_id]['user_id'] == user_id:
            for key, value in data.items():
                categories_db[category_id][key] = value
            categories_db[category_id]['updated_at'] = datetime.now().isoformat()
            return jsonify({'success': True, 'message': 'Category updated successfully'})
        else:
            return jsonify({'error': 'Category not found or unauthorized'}), 404
            
    except Exception as e:
        logger.error(f"Update category error: {str(e)}")
        return jsonify({'error': 'Failed to update category'}), 500

@app.route('/api/categories/<category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    try:
        user_id = session.get('user_id')
        if category_id in categories_db and categories_db[category_id]['user_id'] == user_id:
            del categories_db[category_id]
            return jsonify({'success': True, 'message': 'Category deleted successfully'})
        else:
            return jsonify({'error': 'Category not found or unauthorized'}), 404
            
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
        
        # Verify parent category exists and belongs to user
        if category_id not in categories_db or categories_db[category_id]['user_id'] != user_id:
             return jsonify({'error': 'Parent category not found'}), 404

        subcategory_id = f"subcat_{len(categories_db) + 1}"
        subcategory_data = {
            'id': subcategory_id,
            'user_id': user_id,
            'name': data['name'],
            'description': data.get('description', ''),
            'parent_id': category_id,
            'is_active': True,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        
        categories_db[subcategory_id] = subcategory_data

        return jsonify({'success': True, 'subcategory_id': subcategory_id, 'message': 'Subcategory created successfully'})

    except Exception as e:
        logger.error(f"Create subcategory error: {str(e)}")
        return jsonify({'error': 'Failed to create subcategory'}), 500

@app.route('/api/subcategories/<subcategory_id>', methods=['PUT'])
@login_required
def update_subcategory(subcategory_id):
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if subcategory_id in categories_db and categories_db[subcategory_id]['user_id'] == user_id:
            for key, value in data.items():
                categories_db[subcategory_id][key] = value
            categories_db[subcategory_id]['updated_at'] = datetime.now().isoformat()
            return jsonify({'success': True, 'message': 'Subcategory updated successfully'})
        else:
            return jsonify({'error': 'Subcategory not found or unauthorized'}), 404
            
    except Exception as e:
        logger.error(f"Update subcategory error: {str(e)}")
        return jsonify({'error': 'Failed to update subcategory'}), 500

@app.route('/api/subcategories/<subcategory_id>', methods=['DELETE'])
@login_required
def delete_subcategory(subcategory_id):
    try:
        user_id = session.get('user_id')
        if subcategory_id in categories_db and categories_db[subcategory_id]['user_id'] == user_id:
            del categories_db[subcategory_id]
            return jsonify({'success': True, 'message': 'Subcategory deleted successfully'})
        else:
            return jsonify({'error': 'Subcategory not found or unauthorized'}), 404
            
    except Exception as e:
        logger.error(f"Delete subcategory error: {str(e)}")
        return jsonify({'error': 'Failed to delete subcategory'}), 500

# === CUSTOMERS API ===

@app.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    try:
        user_id = session.get('user_id')
        user_customers = [customer for customer in customers_db.values() if customer.get('user_id') == user_id]
        return jsonify(user_customers)
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

        customer_id = f"cust_{len(customers_db) + 1}"
        customer_data = {
            'id': customer_id,
            'user_id': user_id,
            'name': data['name'],
            'email': data.get('email', ''),
            'phone': data.get('phone', ''),
            'address': data.get('address', ''),
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'is_active': True
        }

        customers_db[customer_id] = customer_data

        return jsonify({'success': True, 'customer_id': customer_id, 'message': 'Customer created successfully'})

    except Exception as e:
        logger.error(f"Create customer error: {str(e)}")
        return jsonify({'error': 'Failed to create customer'}), 500

@app.route('/api/customers/<customer_id>', methods=['PUT'])
@login_required
def update_customer(customer_id):
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        if customer_id in customers_db and customers_db[customer_id]['user_id'] == user_id:
            for key, value in data.items():
                customers_db[customer_id][key] = value
            customers_db[customer_id]['updated_at'] = datetime.now().isoformat()
            return jsonify({'success': True, 'message': 'Customer updated successfully'})
        else:
            return jsonify({'error': 'Customer not found or unauthorized'}), 404
            
    except Exception as e:
        logger.error(f"Update customer error: {str(e)}")
        return jsonify({'error': 'Failed to update customer'}), 500

@app.route('/api/customers/<customer_id>', methods=['DELETE'])
@login_required
def delete_customer(customer_id):
    try:
        user_id = session.get('user_id')
        if customer_id in customers_db and customers_db[customer_id]['user_id'] == user_id:
            del customers_db[customer_id]
            return jsonify({'success': True, 'message': 'Customer deleted successfully'})
        else:
            return jsonify({'error': 'Customer not found or unauthorized'}), 404
            
    except Exception as e:
        logger.error(f"Delete customer error: {str(e)}")
        return jsonify({'error': 'Failed to delete customer'}), 500

# === DEBUG ROUTES ===

# === DEBUG AUTHENTICATION ===

# Error handlers
@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)