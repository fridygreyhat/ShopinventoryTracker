import os
from flask import Flask, render_template, request, jsonify, session, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from functools import wraps
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "your-secret-key-change-in-production")

# Configure PostgreSQL database
database_url = os.environ.get("DATABASE_URL")
if not database_url:
    raise RuntimeError("DATABASE_URL environment variable is not set!")

app.config["SQLALCHEMY_DATABASE_URI"] = database_url
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Initialize database
db.init_app(app)

# Import models after db initialization
from models import User, Item, Customer, Sale, Category

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

# Context processor for templates
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

@app.route('/categories')
@login_required
def categories():
    return render_template('categories.html')

@app.route('/installments')
@login_required
def installments():
    return render_template('installments.html')

@app.route('/margin')
@login_required
def margin():
    return render_template('margin.html')

@app.route('/finance')
@login_required
def finance():
    return render_template('finance.html')

@app.route('/accounting')
@login_required
def accounting():
    return render_template('accounting.html')

@app.route('/reports')
@login_required
def reports():
    return render_template('reports.html')

@app.route('/on_demand')
@login_required
def on_demand():
    return render_template('on_demand.html')

@app.route('/admin_users')
@login_required
def admin_users():
    return render_template('admin_users.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/logout')
@login_required
def logout():
    session.clear()
    return redirect(url_for('login'))

# === AUTHENTICATION API ===

@app.route('/api/auth/login', methods=['POST'])
def api_login():
    try:
        data = request.get_json()
        email = data.get('email')
        password = data.get('password')
        
        if not email or not password:
            return jsonify({'error': 'Email and password required'}), 400
        
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password_hash, password):
            session['user_id'] = user.id
            session['email'] = user.email
            session.permanent = True
            
            # Update last login
            user.last_login = datetime.utcnow()
            db.session.commit()
            
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
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/register', methods=['POST'])
def api_register():
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
            
        email = data.get('email', '').strip()
        password = data.get('password', '')
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        
        # Validate required fields
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        if not first_name:
            return jsonify({'error': 'First name is required'}), 400
        if not last_name:
            return jsonify({'error': 'Last name is required'}), 400
            
        # Validate email format
        if '@' not in email or '.' not in email:
            return jsonify({'error': 'Invalid email format'}), 400
            
        # Validate password length
        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400
        
        # Check if user already exists
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'User with this email already exists'}), 400
        
        # Generate username from email if not provided
        username = data.get('username', '').strip()
        if not username:
            username = email.split('@')[0]
            # Ensure username is unique
            counter = 1
            base_username = username
            while User.query.filter_by(username=username).first():
                username = f"{base_username}{counter}"
                counter += 1
        else:
            # Check if provided username is unique
            if User.query.filter_by(username=username).first():
                return jsonify({'error': 'Username already exists'}), 400
        
        # Create new user
        user = User(
            email=email,
            password_hash=generate_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            username=username,
            phone=data.get('phone', '').strip(),
            shop_name=data.get('shop_name', '').strip(),
            active=True,
            created_at=datetime.utcnow()
        )
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"New user registered: {email}")
        
        return jsonify({
            'success': True,
            'message': 'Registration successful! You can now log in.',
            'user_id': user.id
        })
        
    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@app.route('/api/auth/logout', methods=['POST'])
@login_required
def api_logout():
    session.clear()
    return jsonify({'success': True, 'message': 'Logged out successfully'})

# === DASHBOARD API ===

@app.route('/api/dashboard/summary', methods=['GET'])
@login_required
def dashboard_summary():
    try:
        user_id = session.get('user_id')
        
        # Get counts
        total_items = Item.query.filter_by(user_id=user_id, is_active=True).count()
        total_customers = Customer.query.filter_by(user_id=user_id, active=True).count()
        total_sales = Sale.query.filter_by(user_id=user_id).count()
        total_categories = Category.query.filter_by(is_active=True).count()
        
        # Get low stock items
        low_stock_items = Item.query.filter(
            Item.user_id == user_id,
            Item.is_active == True,
            Item.stock_quantity <= Item.minimum_stock
        ).count()
        
        # Calculate total inventory value
        items = Item.query.filter_by(user_id=user_id, is_active=True).all()
        total_inventory_value = sum(
            (item.stock_quantity or 0) * (item.retail_price or 0) 
            for item in items
        )
        
        return jsonify({
            'success': True,
            'data': {
                'total_items': total_items,
                'total_customers': total_customers,
                'total_sales': total_sales,
                'total_categories': total_categories,
                'low_stock_items': low_stock_items,
                'total_inventory_value': total_inventory_value
            }
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
                'category_id': item.category_id,
                'stock_quantity': item.stock_quantity,
                'minimum_stock': item.minimum_stock,
                'buying_price': float(item.buying_price or 0),
                'retail_price': float(item.retail_price or 0),
                'wholesale_price': float(item.wholesale_price or 0),
                'sku': item.sku,
                'barcode': item.barcode,
                'created_at': item.created_at.isoformat() if item.created_at else None
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
            name=data['name'],
            description=data.get('description', ''),
            category_id=data.get('category_id'),
            stock_quantity=int(data.get('stock_quantity', 0)),
            minimum_stock=int(data.get('minimum_stock', 0)),
            buying_price=float(data.get('buying_price', 0)),
            retail_price=float(data.get('retail_price', 0)),
            wholesale_price=float(data.get('wholesale_price', 0)),
            sku=data.get('sku', ''),
            barcode=data.get('barcode', ''),
            user_id=user_id,
            is_active=True,
            created_at=datetime.utcnow()
        )
        
        db.session.add(item)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'item_id': item.id, 
            'message': 'Item created successfully'
        })
            
    except Exception as e:
        logger.error(f"Create item error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': 'Failed to create item'}), 500

# === SALES API ===

@app.route('/api/sales', methods=['GET'])
@login_required
def get_sales():
    try:
        user_id = session.get('user_id')
        sales = Sale.query.filter_by(user_id=user_id).order_by(Sale.created_at.desc()).all()
        
        sales_data = []
        for sale in sales:
            sales_data.append({
                'id': sale.id,
                'sale_number': sale.sale_number,
                'total_amount': float(sale.total_amount or 0),
                'customer_name': sale.customer_name,
                'payment_method': sale.payment_method,
                'created_at': sale.created_at.isoformat() if sale.created_at else None,
                'notes': sale.notes
            })
        
        return jsonify(sales_data)
    except Exception as e:
        logger.error(f"Get sales error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve sales'}), 500

# === CUSTOMERS API ===

@app.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    try:
        user_id = session.get('user_id')
        customers = Customer.query.filter_by(user_id=user_id, active=True).all()
        
        customers_data = []
        for customer in customers:
            customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'address': customer.address,
                'city': customer.city,
                'state': customer.state,
                'postal_code': customer.postal_code,
                'created_at': customer.created_at.isoformat() if customer.created_at else None
            })
        
        return jsonify(customers_data)
    except Exception as e:
        logger.error(f"Get customers error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve customers'}), 500

# === CATEGORIES API ===

@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    try:
        user_id = session.get('user_id')
        categories = Category.query.filter_by(is_active=True).all()
        
        # Transform categories to match expected frontend format
        formatted_categories = []
        category_map = {}
        
        # First pass: create category map and identify parents
        for category in categories:
            cat_data = {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'parent_id': category.parent_id,
                'sort_order': category.sort_order,
                'subcategories': []
            }
            category_map[category.id] = cat_data
            
            # If no parent_id, it's a main category
            if not category.parent_id:
                formatted_categories.append(cat_data)
        
        # Second pass: attach subcategories to their parents
        for category in categories:
            if category.parent_id and category.parent_id in category_map:
                cat_data = {
                    'id': category.id,
                    'name': category.name,
                    'description': category.description,
                    'parent_id': category.parent_id,
                    'sort_order': category.sort_order
                }
                category_map[category.parent_id]['subcategories'].append(cat_data)
        
        return jsonify(formatted_categories)
    except Exception as e:
        logger.error(f"Get categories error: {str(e)}")
        return jsonify({'error': 'Failed to retrieve categories'}), 500

# === ERROR HANDLERS ===

@app.errorhandler(404)
def not_found(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

# Initialize database tables
with app.app_context():
    try:
        db.create_all()
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {str(e)}")

logger.info("✅ Flask application initialized with PostgreSQL")

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)