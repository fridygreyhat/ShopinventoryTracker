from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from datetime import datetime, timedelta
from functools import wraps
import logging
import os
import uuid

# Import extensions and models
from extensions import db, login_manager, configure_database
from models import User, Item, Customer, Sale, SaleItem, Category
from accounting_service import AccountingService

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Configure database
if not configure_database(app):
    logger.error("Failed to configure database")
    exit(1)

# Configure login manager
login_manager.init_app(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

def init_database():
    """Initialize database tables"""
    try:
        with app.app_context():
            db.create_all()
            logger.info("✅ Database tables created successfully")
            return True
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {str(e)}")
        return False

logger.info("✅ Flask application initialized with PostgreSQL")

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
            return User.query.get(user_id)
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

        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            session['user_id'] = user.id
            session['email'] = user.email
            session.permanent = True

            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()

            logger.info(f"Successful login for: {email}")
            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'username': user.username
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

        email = data['email'].strip().lower()

        # Check if user already exists
        if User.query.filter_by(email=email).first():
            return jsonify({'error': 'Email already exists'}), 400

        # Create new user
        user = User(
            id=str(uuid.uuid4()),
            email=email,
            first_name=data['first_name'],
            last_name=data['last_name'],
            username=data.get('username', email.split('@')[0]),
            shop_name=data.get('shop_name', ''),
            phone=data.get('phone', ''),
            product_categories=data.get('product_categories', '')
        )
        user.set_password(data['password'])

        db.session.add(user)
        db.session.commit()

        # Initialize chart of accounts for new user
        AccountingService.initialize_chart_of_accounts(user.id)

        return jsonify({
            'success': True,
            'message': 'Registration successful',
            'user_id': user.id
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Registration error: {str(e)}")
        return jsonify({'error': 'Registration failed'}), 500

# === DASHBOARD API ===

@app.route('/api/dashboard/summary')
@login_required
def get_dashboard_summary():
    try:
        user_id = session.get('user_id')

        # Get metrics from database
        total_items = Item.query.filter_by(user_id=user_id, is_active=True).count()
        total_stock = db.session.query(db.func.sum(Item.stock_quantity)).filter_by(user_id=user_id, is_active=True).scalar() or 0
        low_stock_items = Item.query.filter(
            Item.user_id == user_id, 
            Item.is_active == True,
            Item.stock_quantity <= Item.minimum_stock
        ).count()

        inventory_value = db.session.query(
            db.func.sum(Item.stock_quantity * Item.buying_price)
        ).filter_by(user_id=user_id, is_active=True).scalar() or 0

        total_sales = Sale.query.filter_by(user_id=user_id, is_active=True).count()
        total_revenue = db.session.query(db.func.sum(Sale.total_amount)).filter_by(user_id=user_id, is_active=True).scalar() or 0
        total_customers = Customer.query.filter_by(user_id=user_id, is_active=True).count()

        return jsonify({
            'inventory': {
                'total_items': total_items,
                'total_stock': int(total_stock),
                'low_stock_items': low_stock_items,
                'inventory_value': float(inventory_value)
            },
            'sales': {
                'total_sales': total_sales,
                'total_revenue': float(total_revenue)
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
        items = Item.query.filter_by(user_id=user_id, is_active=True).all()

        items_data = []
        for item in items:
            items_data.append({
                'id': item.id,
                'name': item.name,
                'description': item.description,
                'category': item.category,
                'stock_quantity': item.stock_quantity,
                'minimum_stock': item.minimum_stock,
                'buying_price': item.buying_price,
                'retail_price': item.retail_price,
                'sku': item.sku,
                'created_at': item.created_at.isoformat(),
                'updated_at': item.updated_at.isoformat()
            })

        return jsonify(items_data)
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

        item = Item(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=data['name'],
            description=data.get('description', ''),
            category=data.get('category', 'General'),
            stock_quantity=int(data.get('stock_quantity', 0)),
            minimum_stock=int(data.get('minimum_stock', 0)),
            buying_price=float(data.get('buying_price', 0.0)),
            retail_price=float(data.get('retail_price', 0.0)),
            sku=data.get('sku', '')
        )

        db.session.add(item)
        db.session.commit()

        return jsonify({'success': True, 'item_id': item.id, 'message': 'Item created successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Create item error: {str(e)}")
        return jsonify({'error': 'Failed to create item'}), 500

@app.route('/api/items/<item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        item = Item.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            return jsonify({'error': 'Item not found or unauthorized'}), 404

        # Update fields
        for key, value in data.items():
            if hasattr(item, key) and key != 'id':
                setattr(item, key, value)

        item.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'message': 'Item updated successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update item error: {str(e)}")
        return jsonify({'error': 'Failed to update item'}), 500

@app.route('/api/items/<item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    try:
        user_id = session.get('user_id')
        item = Item.query.filter_by(id=item_id, user_id=user_id).first()

        if not item:
            return jsonify({'error': 'Item not found or unauthorized'}), 404

        item.is_active = False
        db.session.commit()

        return jsonify({'success': True, 'message': 'Item deleted successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete item error: {str(e)}")
        return jsonify({'error': 'Failed to delete item'}), 500

# === CATEGORIES API ===

@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    try:
        user_id = session.get('user_id')
        categories = Category.query.filter_by(user_id=user_id, is_active=True, parent_id=None).all()

        formatted_categories = []
        for category in categories:
            subcategories = Category.query.filter_by(parent_id=category.id, is_active=True).all()

            category_data = {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'icon': category.icon,
                'color': category.color,
                'created_at': category.created_at.isoformat(),
                'subcategories': [{
                    'id': sub.id,
                    'name': sub.name,
                    'description': sub.description,
                    'parent_id': sub.parent_id,
                    'created_at': sub.created_at.isoformat()
                } for sub in subcategories]
            }
            formatted_categories.append(category_data)

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

        category = Category(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=data['name'],
            description=data.get('description', ''),
            parent_id=data.get('parent_id'),
            icon=data.get('icon', 'fas fa-folder'),
            color=data.get('color', '#007bff')
        )

        db.session.add(category)
        db.session.commit()

        return jsonify({'success': True, 'category_id': category.id, 'message': 'Category created successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Create category error: {str(e)}")
        return jsonify({'error': 'Failed to create category'}), 500

@app.route('/api/categories/<category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return jsonify({'error': 'Category not found or unauthorized'}), 404

        # Update fields
        for key, value in data.items():
            if hasattr(category, key) and key != 'id':
                setattr(category, key, value)

        category.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'message': 'Category updated successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update category error: {str(e)}")
        return jsonify({'error': 'Failed to update category'}), 500


@app.route('/api/categories/<category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    try:
        user_id = session.get('user_id')
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()

        if not category:
            return jsonify({'error': 'Category not found or unauthorized'}), 404

        category.is_active = False
        db.session.commit()

        return jsonify({'success': True, 'message': 'Category deleted successfully'})

    except Exception as e:
        db.session.rollback()
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
        parent_category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not parent_category:
             return jsonify({'error': 'Parent category not found'}), 404

        subcategory = Category(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=data['name'],
            description=data.get('description', ''),
            parent_id=category_id
        )
        
        db.session.add(subcategory)
        db.session.commit()

        return jsonify({'success': True, 'subcategory_id': subcategory.id, 'message': 'Subcategory created successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Create subcategory error: {str(e)}")
        return jsonify({'error': 'Failed to create subcategory'}), 500

@app.route('/api/subcategories/<subcategory_id>', methods=['PUT'])
@login_required
def update_subcategory(subcategory_id):
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        subcategory = Category.query.filter_by(id=subcategory_id, user_id=user_id).first()
        if not subcategory:
            return jsonify({'error': 'Subcategory not found or unauthorized'}), 404

        # Update fields
        for key, value in data.items():
            if hasattr(subcategory, key) and key != 'id':
                setattr(subcategory, key, value)

        subcategory.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'message': 'Subcategory updated successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update subcategory error: {str(e)}")
        return jsonify({'error': 'Failed to update subcategory'}), 500

@app.route('/api/subcategories/<subcategory_id>', methods=['DELETE'])
@login_required
def delete_subcategory(subcategory_id):
    try:
        user_id = session.get('user_id')
        subcategory = Category.query.filter_by(id=subcategory_id, user_id=user_id).first()

        if not subcategory:
            return jsonify({'error': 'Subcategory not found or unauthorized'}), 404

        subcategory.is_active = False
        db.session.commit()

        return jsonify({'success': True, 'message': 'Subcategory deleted successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete subcategory error: {str(e)}")
        return jsonify({'error': 'Failed to delete subcategory'}), 500

# === CUSTOMERS API ===

@app.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    try:
        user_id = session.get('user_id')
        customers = Customer.query.filter_by(user_id=user_id, is_active=True).all()

        customers_data = []
        for customer in customers:
            customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'address': customer.address,
                'created_at': customer.created_at.isoformat(),
                'updated_at': customer.updated_at.isoformat()
            })
        return jsonify(customers_data)
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

        customer = Customer(
            id=str(uuid.uuid4()),
            user_id=user_id,
            name=data['name'],
            email=data.get('email', ''),
            phone=data.get('phone', ''),
            address=data.get('address', '')
        )

        db.session.add(customer)
        db.session.commit()

        return jsonify({'success': True, 'customer_id': customer.id, 'message': 'Customer created successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Create customer error: {str(e)}")
        return jsonify({'error': 'Failed to create customer'}), 500

@app.route('/api/customers/<customer_id>', methods=['PUT'])
@login_required
def update_customer(customer_id):
    try:
        user_id = session.get('user_id')
        data = request.get_json()
        
        customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first()
        if not customer:
            return jsonify({'error': 'Customer not found or unauthorized'}), 404
        
        # Update fields
        for key, value in data.items():
            if hasattr(customer, key) and key != 'id':
                setattr(customer, key, value)

        customer.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Customer updated successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Update customer error: {str(e)}")
        return jsonify({'error': 'Failed to update customer'}), 500

@app.route('/api/customers/<customer_id>', methods=['DELETE'])
@login_required
def delete_customer(customer_id):
    try:
        user_id = session.get('user_id')
        customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first()

        if not customer:
            return jsonify({'error': 'Customer not found or unauthorized'}), 404

        customer.is_active = False
        db.session.commit()
        
        return jsonify({'success': True, 'message': 'Customer deleted successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Delete customer error: {str(e)}")
        return jsonify({'error': 'Failed to delete customer'}), 500

# === SALES API ===

@app.route('/api/sales', methods=['GET'])
@login_required
def get_sales():
    try:
        user_id = session.get('user_id')
        sales = Sale.query.filter_by(user_id=user_id, is_active=True).all()

        sales_data = []
        for sale in sales:
            sales_data.append({
                'id': sale.id,
                'total_amount': sale.total_amount,
                'customer_name': sale.customer_name,
                'payment_type': sale.payment_type,
                'created_at': sale.created_at.isoformat()
            })
        return jsonify(sales_data)
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

        sale = Sale(
            id=str(uuid.uuid4()),
            user_id=user_id,
            total_amount=float(data['total_amount']),
            customer_name=data.get('customer_name', 'Walk-in Customer'),
            payment_type=data.get('payment_type', 'cash')
        )

        db.session.add(sale)
        db.session.commit()

        # Process sale items
        sale_items = data['sale_items']
        for item_data in sale_items:
             item_id = item_data.get('item_id')
             quantity = int(item_data.get('quantity', 1))

             item = Item.query.get(item_id)
             if item:
                  sale_item = SaleItem(
                       sale_id = sale.id,
                       item_id = item.id,
                       quantity = quantity,
                       price = item.retail_price
                  )
                  db.session.add(sale_item)
                  item.stock_quantity -= quantity
        
        db.session.commit()

        return jsonify({'success': True, 'sale_id': sale.id, 'message': 'Sale created successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Create sale error: {str(e)}")
        return jsonify({'error': 'Failed to create sale'}), 500

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
    # Initialize database on startup
    init_database()
    app.run(debug=True, host='0.0.0.0', port=5000)