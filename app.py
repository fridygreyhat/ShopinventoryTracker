import os
import logging
import uuid
import json
from datetime import datetime, timedelta, date
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy import func, or_, and_
from werkzeug.middleware.proxy_fix import ProxyFix
import io
import csv
import requests
from flask_mail import Mail
from dotenv import load_dotenv
from flask_login import LoginManager, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_migrate import Migrate
from functools import wraps





# Import db from extensions to avoid circular imports
from extensions import db, configure_database

# Import models to ensure they're available
from models import Item, Sale, SaleItem, StockMovement, User, Setting, Customer, FinancialTransaction, InstallmentSale, InstallmentPayment
from datetime import timedelta

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom login_required decorator for session-based authentication
def login_required(f):
    """Custom login required decorator that works with session-based authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Create Flask app
app = Flask(__name__)

# Configure secret key
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')

# Configure PostgreSQL database (ONLY PostgreSQL - No Firebase)
configure_database(app)



# Initialize extensions with app
db.init_app(app)

# Configure Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Make User inherit from UserMixin for Flask-Login
# class User(db.Model, UserMixin):
#     pass


@app.context_processor
def inject_user():
    def get_current_user():
        user_id = session.get('user_id')
        if user_id:
            from models import User
            return User.query.get(user_id)
        return None
    return dict(get_current_user=get_current_user)

@app.route('/debug')
def debug():
    user_id = session.get('user_id')
    print(f"Session: {session}")
    print(f"User ID in session: {user_id}")
    if user_id:
        from models import User
        user = User.query.get(user_id)
        print(f"Current user: {user}")
        print(f"Is authenticated: {user is not None}")
    return "Check console"

def init_database():
    """Initialize PostgreSQL database tables and default data"""
    with app.app_context():
        try:
            # Import all models to ensure they're registered
            from models import (User, Item, Setting, Sale, SaleItem, FinancialTransaction, 
                Category, Customer, OnDemandProduct, StockMovement, ChartOfAccounts,
                Journal, Supplier, PurchaseOrder, UserTwoFactor, Employee, InstallmentSale, InstallmentPayment
            )

            # Create all tables
            db.create_all()
            logger.info("Database tables created successfully")

            # Test database connection
            db.session.execute(db.text('SELECT 1'))
            db.session.commit()
            logger.info("Database connection test successful")

            # Helper function to check if column exists
            def column_exists(table_name, column_name):
                try:
                    # PostgreSQL query to check if column exists - using parameterized query
                    result = db.session.execute(
                        db.text("""
                            SELECT column_name 
                            FROM information_schema.columns 
                            WHERE table_name = :table_name 
                            AND column_name = :column_name
                        """), 
                        {"table_name": table_name, "column_name": column_name}
                    )
                    return result.fetchone() is not None
                except Exception as e:
                    logger.error(f"Error checking column existence: {str(e)}")
                    return False

            # Helper function to add column safely
            def add_column_safely(table_name, column_name, column_definition, default_value=None):
                try:
                    if not column_exists(table_name, column_name):
                        logger.info(f"Adding {column_name} column to {table_name} table")

                        # Use parameterized query for ALTER TABLE
                        alter_sql = f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                        db.session.execute(db.text(alter_sql))

                        if default_value:
                            update_sql = f"UPDATE {table_name} SET {column_name} = :default_value"
                            db.session.execute(db.text(update_sql), {"default_value": default_value})

                        db.session.commit()
                        logger.info(f"Successfully added {column_name} column to {table_name}")
                        return True
                    else:
                        logger.info(f"{column_name} column already exists in {table_name}")
                        return False
                except Exception as e:
                    logger.error(f"Error adding {column_name} column to {table_name}: {str(e)}")
                    db.session.rollback()
                    return False

            # Add missing columns if they don't exist
            def add_missing_columns():
                try:
                    # Add columns to user table
                    add_column_safely('user', 'is_active', 'BOOLEAN DEFAULT TRUE', True)
                    add_column_safely('user', 'phone', 'VARCHAR(20)')

                    # Add columns to item table
                    add_column_safely('item', 'subcategory', 'VARCHAR(100)')
                    add_column_safely('item', 'unit_type', "VARCHAR(20) DEFAULT 'quantity'", 'quantity')
                    add_column_safely('item', 'sell_by', "VARCHAR(20) DEFAULT 'quantity'", 'quantity')
                    add_column_safely('item', 'category_id', 'INTEGER')
                    add_column_safely('item', 'user_id', 'INTEGER')
                    add_column_safely('item', 'is_active', 'BOOLEAN DEFAULT TRUE', True)
                    add_column_safely('item', 'stock_quantity', 'INTEGER DEFAULT 0', 0)
                    add_column_safely('item', 'minimum_stock', 'INTEGER DEFAULT 0', 0)
                    add_column_safely('item', 'retail_price', 'FLOAT DEFAULT 0', 0)
                    add_column_safely('item', 'wholesale_price', 'FLOAT DEFAULT 0', 0)

                    # Add columns to sale table
                    add_column_safely('sale', 'user_id', 'INTEGER')
                    add_column_safely('sale', 'customer_id', 'INTEGER')
                    add_column_safely('sale', 'total_amount', 'FLOAT DEFAULT 0', 0)
                    add_column_safely('sale', 'payment_type', "VARCHAR(20) DEFAULT 'cash'", 'cash')
                    add_column_safely('sale', 'payment_status', "VARCHAR(20) DEFAULT 'completed'", 'completed')
                    add_column_safely('sale', 'sale_number', 'VARCHAR(50)')
                    add_column_safely('sale', 'is_installment', 'BOOLEAN DEFAULT FALSE', False)
                    add_column_safely('sale', 'down_payment', 'FLOAT DEFAULT 0', 0)
                    add_column_safely('sale', 'installment_months', 'INTEGER DEFAULT 0', 0)
                    add_column_safely('sale', 'monthly_payment', 'FLOAT DEFAULT 0', 0)

                    # Add columns to supplier table
                    add_column_safely('supplier', 'is_active', 'BOOLEAN DEFAULT TRUE', True)
                    add_column_safely('supplier', 'updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

                    # Add columns to purchase_order table
                    add_column_safely('purchase_order', 'updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

                    # Add columns to installment_plan table
                    add_column_safely('installment_plan', 'payments_made', 'INTEGER DEFAULT 0', 0)
                    add_column_safely('installment_plan', 'next_due_date', 'DATE')
                    add_column_safely('installment_plan', 'updated_at', 'TIMESTAMP DEFAULT CURRENT_TIMESTAMP')

                    # Add columns to chart_of_accounts table
                    add_column_safely('chart_of_accounts', 'parent_account_id', 'INTEGER')
                    add_column_safely('chart_of_accounts', 'balance', 'FLOAT DEFAULT 0', 0)

                    # Add columns to journal table
                    add_column_safely('journal', 'journal_number', 'VARCHAR(50)')
                    add_column_safely('journal', 'total_debit', 'FLOAT DEFAULT 0', 0)
                    add_column_safely('journal', 'total_credit', 'FLOAT DEFAULT 0', 0)

                    # Check if Customer table exists, if not create it
                    check_and_create_customer_table()

                    # Add columns to financial_transaction table
                    add_column_safely('financial_transaction', 'user_id', 'INTEGER')

                except Exception as e:
                    logger.error(f"Error adding missing columns: {str(e)}")
                    db.session.rollback()

            def check_and_create_customer_table():
                """Check if Customer table exists and create if not"""
                try:
                    result = db.session.execute(db.text("""
                        SELECT table_name 
                        FROM information_schema.tables 
                        WHERE table_name = :table_name 
                        AND table_schema = current_schema()
                    """), {"table_name": "customer"})

                    if not result.fetchone():
                        # Create Customer table
                        db.session.execute(db.text("""
                            CREATE TABLE customer (
                                id SERIAL PRIMARY KEY,
                                name VARCHAR(100) NOT NULL,
                                email VARCHAR(120),
                                phone VARCHAR(20),
                                address TEXT,
                                customer_type VARCHAR(20) DEFAULT 'retail',
                                credit_limit FLOAT DEFAULT 0.0,
                                loyalty_points INTEGER DEFAULT 0,
                                preferred_payment_method VARCHAR(50),
                                user_id INTEGER NOT NULL,
                                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                            )
                        """))
                        db.session.commit()
                        logger.info("Customer table created successfully")
                    else:
                        logger.info("Customer table already exists")

                except Exception as e:
                    logger.error(f"Error checking/creating Customer table: {str(e)}")
                    db.session.rollback()

            # Initialize default settings
            def initialize_default_settings():
                """Initialize default application settings"""
                try:
                    default_settings = [
                        {
                            'key': 'sms_notifications_enabled',
                            'value': 'false',
                            'description': 'Enable SMS notifications for low stock alerts',
                            'category': 'notifications'
                        },
                        {
                            'key': 'notification_phone',
                            'value': '',
                            'description': 'Phone number to receive SMS notifications (include country code)',
                            'category': 'notifications'
                        },
                        {
                            'key': 'low_stock_threshold',
                            'value': '10',
                            'description': 'Quantity threshold for low stock alerts',
                            'category': 'notifications'
                        },
                        {
                            'key': 'email_notifications_enabled',
                            'value': 'false',
                            'description': 'Enable email notifications for low stock alerts',
                            'category': 'notifications'
                        },
                        {
                            'key': 'notification_email',
                            'value': '',
                            'description': 'Email address to receive notifications',
                            'category': 'notifications'
                        },
                        {
                            'key': 'sender_email',
                            'value': 'inventory@yourbusiness.com',
                            'description': 'Email address to send notifications from',
                            'category': 'notifications'
                        }
                    ]

                    for setting_data in default_settings:
                        existing_setting = Setting.query.filter_by(key=setting_data['key']).first()
                        if not existing_setting:
                            new_setting = Setting(
                                key=setting_data['key'],
                                value=setting_data['value'],
                                description=setting_data['description'],
                                category=setting_data['category']
                            )
                            db.session.add(new_setting)

                    db.session.commit()
                    logger.info("Default settings initialized successfully")

                except Exception as e:
                    logger.warning(f"Could not initialize default settings: {str(e)}")
                    db.session.rollback()

            # Execute initialization steps
            add_missing_columns()
            initialize_default_settings()

            logger.info("Database initialization completed successfully")
            return True

        except Exception as e:
            logger.error(f"Database initialization error: {str(e)}")
            db.session.rollback()
            return False


# Auth API Routes
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API endpoint for user login - authenticates against PostgreSQL"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Check user credentials in PostgreSQL
        from models import User
        user = User.query.filter_by(email=email, is_active=True).first()

        if user and user.check_password(password):
            try:
                # Update last login in PostgreSQL
                user.last_login = datetime.utcnow()

                # Create session
                session.clear()  # Clear any existing session data
                session['user_id'] = user.id
                session['user_email'] = user.email
                session['user_name'] = f"{user.first_name or ''} {user.last_name or ''}".strip()

                # Commit changes to PostgreSQL
                db.session.commit()
                logger.info(f"User {email} logged in successfully from PostgreSQL (ID: {user.id})")

                return jsonify({
                    'success': True,
                    'message': 'Login successful - authenticated from PostgreSQL',
                    'user': {
                        'id': user.id,
                        'email': user.email,
                        'username': user.username,
                        'first_name': user.first_name,
                        'last_name': user.last_name
                    }
                }), 200
            except Exception as session_error:
                logger.error(f"Session creation error: {str(session_error)}")
                db.session.rollback()
                return jsonify({'error': 'Login failed during session creation'}), 500
        else:
            logger.warning(f"Failed login attempt for email: {email} - user not found in PostgreSQL or invalid password")
            return jsonify({'error': 'Invalid email or password'}), 401

    except Exception as e:
        logger.error(f"PostgreSQL login error: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@app.route('/api/auth/register', methods=['POST'])
@app.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for user registration - stores users in PostgreSQL"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        username = data.get('username', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        shop_name = data.get('shop_name', '').strip()
        phone = data.get('phone', '').strip()
        product_categories = data.get('product_categories', '')

        # Validate required fields
        if not email:
            return jsonify({'error': 'Email is required'}), 400
        if not password:
            return jsonify({'error': 'Password is required'}), 400
        if not username:
            return jsonify({'error': 'Username is required'}), 400
        if not first_name:
            return jsonify({'error': 'First name is required'}), 400
        if not last_name:
            return jsonify({'error': 'Last name is required'}), 400

        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            return jsonify({'error': 'Invalid email format'}), 400

        if len(password) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400

        if len(username) < 3:
            return jsonify({'error': 'Username must be at least 3 characters long'}), 400

        # Check if user already exists in PostgreSQL
        from models import User
        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            return jsonify({'error': 'Email already registered'}), 400

        # Check if username already exists
        existing_username = User.query.filter_by(username=username).first()
        if existing_username:
            return jsonify({'error': 'Username already taken'}), 400

        # Create new user in PostgreSQL
        new_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            phone=phone if phone else None,
            shop_name=shop_name if shop_name else None,
            product_categories=product_categories if product_categories else None,
            is_active=True,
            is_admin=False,
            email_verified=False,
            created_at=datetime.utcnow()
        )

        # Set password hash using secure method
        new_user.set_password(password)

        # Verify password was set correctly
        if not new_user.password_hash:
            return jsonify({'error': 'Failed to set password'}), 500

        # Save to PostgreSQL database
        db.session.add(new_user)
        db.session.flush()  # Get the user ID without committing

        # Verify user was created in PostgreSQL
        if not new_user.id:
            return jsonify({'error': 'Failed to create user in PostgreSQL'}), 500

        # Create session for the new user
        session.clear()  # Clear any existing session
        session['user_id'] = new_user.id
        session['user_email'] = new_user.email
        session['user_name'] = f"{new_user.first_name} {new_user.last_name}".strip()

        # Commit to PostgreSQL
        db.session.commit()

        logger.info(f"New user registered in PostgreSQL: {email} (ID: {new_user.id})")

        return jsonify({
            'success': True,
            'message': 'Account created successfully in PostgreSQL',
            'user': {
                'id': new_user.id,
                'username': new_user.username,
                'email': new_user.email,
                'first_name': new_user.first_name,
                'last_name': new_user.last_name
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"PostgreSQL registration error: {str(e)}")
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@app.route('/api/auth/session', methods=['POST'])
def api_create_session():
    """API endpoint to create user session"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember = data.get('remember', False)

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Check user credentials
        user = User.query.filter_by(email=email).first()

        if user and user.check_password(password):
            # Create session
            session['user_id'] = user.id
            session['user_email'] = user.email
            session['user_name'] = f"{user.first_name} {user.last_name}"

            if remember:
                session.permanent = True

            return jsonify({
                'success': True,
                'user': {
                    'id': user.id,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                }
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

    except Exception as e:
        logger.error(f"Session creation error: {str(e)}")
        return jsonify({'error': 'Session creation failed'}), 500

@app.route('/api/auth/profile', methods=['GET'])
def api_get_profile():
    """API endpoint to get user profile"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': {
                'id': user.id,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        }), 200

    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({'error': 'Failed to get profile'}), 500

@app.route('/api/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    """API endpoint for password reset"""
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        user = User.query.filter_by(email=email).first()

        if user:
            # Here you would typically send a password reset email
            # For now, we'll just return success
            logger.info(f"Password reset requested for: {email}")

        return jsonify({'success': True, 'message': 'Password reset email sent if account exists'}), 200

    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return jsonify({'error': 'Password reset failed'}), 500

@app.route('/api/auth/validate-session', methods=['GET'])
def api_validate_session():
    """API endpoint to validate current session"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'No active session'}), 401

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'email': user.email,
                'username': user.username,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        }), 200

    except Exception as e:
        logger.error(f"Session validation error: {str(e)}")
        return jsonify({'error': 'Session validation failed'}), 500

# API Routes
@app.route('/api/inventory', methods=['GET'])
@login_required
def get_inventory():
    """Get all inventory items with optional filtering and enhanced category support"""
    try:
        from models import Item, Category

        # Get current user ID
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify([])

        # Start query filtered by user only
        query = Item.query.filter(Item.user_id == current_user_id, Item.is_active == True)

        # Optional filtering
        category = request.args.get('category')
        subcategory = request.args.get('subcategory')
        search_term = request.args.get('search', '').lower()
        min_stock = request.args.get('min_stock')
        max_stock = request.args.get('max_stock')
        include_inactive = request.args.get('include_inactive', 'false').lower() == 'true'

        # Include inactive items if requested (for admin purposes)
        if include_inactive:
            query = Item.query.filter(Item.user_id == current_user_id)

        # Apply category filter (support both category name and subcategory)
        if category:
            if subcategory:
                # Filter by both category and subcategory
                query = query.filter(
                    or_(
                        Item.category == category,
                        Item.subcategory == subcategory
                    )
                )
            else:
                # Filter by category or subcategory matching the category name
                query = query.filter(
                    or_(
                        Item.category == category,
                        Item.subcategory == category
                    )
                )

        # Enhanced search filter
        if search_term:
            search_filter = (
                Item.name.ilike(f'%{search_term}%')
                | Item.sku.ilike(f'%{search_term}%')
                | Item.description.ilike(f'%{search_term}%')
                | Item.category.ilike(f'%{search_term}%')
                | Item.subcategory.ilike(f'%{search_term}%')
            )
            query = query.filter(search_filter)

        # Stock level filters
        if min_stock:
            try:
                min_stock = int(min_stock)
                query = query.filter(Item.stock_quantity >= min_stock)
            except ValueError:
                pass

        if max_stock:
            try:
                max_stock = int(max_stock)
                query = query.filter(Item.stock_quantity <= max_stock)
            except ValueError:
                pass

        # Order by name for consistent results
        query = query.order_by(Item.name)

        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 100, type=int)
        limit = request.args.get('limit', type=int)

        # Apply limit if specified (for dashboard widgets)
        if limit:
            items = query.limit(limit).all()
            total_count = query.count()
        else:
            # Use pagination for large datasets
            paginated = query.paginate(page=page, per_page=per_page, error_out=False)
            items = paginated.items
            total_count = paginated.total

        # Convert items to dictionary format
        items_data = []
        for item in items:
            item_dict = item.to_dict()

            # Ensure backward compatibility with frontend expectations
            item_dict['quantity'] = item.stock_quantity
            item_dict['price'] = item.retail_price or 0

            # Add category relationship data if available
            if item.category_rel:
                item_dict['category_details'] = {
                    'id': item.category_rel.id,
                    'name': item.category_rel.name,
                    'description': item.category_rel.description,
                    'parent_id': item.category_rel.parent_id
                }

            # Add stock status indicators
            item_dict['stock_status'] = 'out_of_stock' if item.stock_quantity == 0 else (
                'low_stock' if item.stock_quantity <= (item.minimum_stock or 5) else 'in_stock'
            )

            # Calculate profit margins
            if item.buying_price and item.retail_price:
                profit = item.retail_price - item.buying_price
                item_dict['profit_margin'] = round((profit / item.retail_price) * 100, 2) if item.retail_price > 0 else 0
                item_dict['profit_per_unit'] = profit
            else:
                item_dict['profit_margin'] = 0
                item_dict['profit_per_unit'] = 0

            items_data.append(item_dict)

        # Calculate inventory analytics
        analytics = {}
        if request.args.get('include_analytics') == 'true':
            total_value = sum(item.stock_quantity * (item.buying_price or 0) for item in items)
            low_stock_count = sum(1 for item in items if item.stock_quantity <= (item.minimum_stock or 5))
            out_of_stock_count = sum(1 for item in items if item.stock_quantity == 0)

            analytics = {
                'total_inventory_value': total_value,
                'low_stock_count': low_stock_count,
                'out_of_stock_count': out_of_stock_count,
                'average_stock_level': sum(item.stock_quantity for item in items) / len(items) if items else 0,
                'categories_represented': len(set(item.category for item in items if item.category))
            }

        # Prepare response with metadata
        response_data = {
            'items': items_data,
            'total_count': total_count,
            'page': page if not limit else 1,
            'per_page': per_page if not limit else len(items_data),
            'has_more': total_count > (page * per_page) if not limit else False,
            'analytics': analytics if analytics else None
        }

        # If simple format requested (backward compatibility)
        if request.args.get('format') == 'simple':
            return jsonify(items_data)

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error getting inventory: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/shop/details', methods=['GET'])
@login_required
def get_shop_details():
    """API endpoint to get shop/user details for the dashboard"""
    try:
        user_id = session.get('user_id')
        from models import User

        user = User.query.get(user_id)
        if not user:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'shop_name': user.shop_name or f"{user.first_name}'s Shop" if user.first_name else "Your Shop",
                'phone': user.phone,
                'is_admin': user.is_admin,
                'created_at': user.created_at.isoformat() if user.created_at else None
            }
        })
    except Exception as e:
        logger.error(f"Error getting shop details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory', methods=['POST'])
@login_required
def add_item():
    """API endpoint to add a new inventory item"""
    try:
        from models import Item

        item_data = request.get_json()
        if not item_data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        if not item_data.get('name'):
            return jsonify({"error": "Item name is required"}), 400

        # Get current user ID
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Handle quantity field mapping (support both 'quantity' and 'stock_quantity')
        quantity = item_data.get('quantity', item_data.get('stock_quantity', 0))
        try:
            quantity = int(quantity) if quantity is not None else 0
        except (ValueError, TypeError):
            quantity = 0

        # Handle price fields with proper validation
        buying_price = item_data.get("buying_price", 0)
        selling_price_retail = item_data.get("selling_price_retail", item_data.get("retail_price", 0))
        selling_price_wholesale = item_data.get("selling_price_wholesale", item_data.get("wholesale_price", 0))

        try:
            buying_price = float(buying_price) if buying_price else 0.0
            selling_price_retail = float(selling_price_retail) if selling_price_retail else 0.0
            selling_price_wholesale = float(selling_price_wholesale) if selling_price_wholesale else 0.0
        except (ValueError, TypeError):
            return jsonify({"error": "Invalid price format"}), 400

        # Generate SKU if not provided
        sku = item_data.get("sku")
        if not sku:
            sku = Item.generate_sku(item_data["name"], item_data.get("category", ""))

        # Check if SKU already exists
        existing_item = Item.query.filter_by(sku=sku, user_id=current_user_id).first()
        if existing_item:
            return jsonify({"error": f"SKU '{sku}' already exists"}), 400

        # Handle category and category_id
        category_name = item_data.get("category", "Uncategorized")
        category_id = item_data.get("category_id")

        # If category_id is provided, validate it exists and belongs to user
        if category_id:
            from models import Category
            category_obj = Category.query.filter_by(id=category_id, user_id=current_user_id).first()
            if category_obj:
                category_name = category_obj.name
            else:
                category_id = None  # Reset if invalid

        # Create new item
        new_item = Item(
            name=item_data["name"].strip(),
            description=item_data.get("description", "").strip(),
            sku=sku,
            stock_quantity=quantity,
            minimum_stock=int(item_data.get("minimum_stock", 5)),
            buying_price=buying_price,
            retail_price=selling_price_retail,
            wholesale_price=selling_price_wholesale,
            sales_type=item_data.get("sales_type", "both"),
            category=category_name,
            category_id=category_id,
            subcategory=item_data.get("subcategory"),
            unit_type=item_data.get("unit_type", "quantity"),
            sell_by=item_data.get("sell_by", "quantity"),
            user_id=current_user_id,
            is_active=True
        )

        # Add to database
        db.session.add(new_item)
        db.session.commit()

        logger.info(f"New item created: {new_item.name} (ID: {new_item.id}) by user {current_user_id}")

        # Check for low stock notification (if applicable)
        if quantity <= int(item_data.get("minimum_stock", 5)):
            try:
                from notifications.notification_manager import check_low_stock_and_notify
                import threading

                notification_thread = threading.Thread(
                    target=check_low_stock_and_notify,
                    args=(db, Item, Setting))
                notification_thread.daemon = True
                notification_thread.start()
            except Exception as e:
                logger.warning(f"Could not trigger low stock notification: {str(e)}")

        return jsonify(new_item.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding item: {str(e)}")
        return jsonify({"error": f"Failed to add item: {str(e)}"}), 500

@app.route('/api/inventory/<int:item_id>', methods=['GET'])
def get_item(item_id):
    """API endpoint to get a specific inventory item"""
    from models import Item

    item = Item.query.get(item_id)

    if not item:
        return jsonify({"error": "Item not found"}), 404

    return jsonify(item.to_dict())

@app.route('/api/inventory/<int:item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    """API endpoint to update an inventory item"""
    try:
        from models import Item, Setting

        item_data = request.get_json()
        if not item_data:
            return jsonify({"error": "No data provided"}), 400

        # Get current user ID
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Get item and verify ownership
        item = Item.query.filter_by(id=item_id, user_id=current_user_id).first()
        if not item:
            return jsonify({"error": "Item not found"}), 404

        # Handle quantity field mapping
        if 'quantity' in item_data and 'stock_quantity' not in item_data:
            item_data['stock_quantity'] = item_data['quantity']
        elif 'stock_quantity' in item_data and 'quantity' not in item_data:
            item_data['quantity'] = item_data['stock_quantity']

        # Handle price field mappings
        price_mappings = {
            'selling_price_retail': 'retail_price',
            'selling_price_wholesale': 'wholesale_price',
            'price': 'retail_price'  # Legacy support
        }

        for old_field, new_field in price_mappings.items():
            if old_field in item_data:
                try:
                    item_data[new_field] = float(item_data[old_field])
                except (ValueError, TypeError):
                    return jsonify({"error": f"Invalid {old_field} format"}), 400

        # Handle category and category_id
        if 'category_id' in item_data:
            category_id = item_data.get('category_id')
            if category_id:
                from models import Category
                category_obj = Category.query.filter_by(id=category_id, user_id=current_user_id).first()
                if category_obj:
                    item.category_id = category_id
                    item.category = category_obj.name
                else:
                    return jsonify({"error": "Invalid category ID"}), 400
            else:
                item.category_id = None

        # Update allowed fields only
        allowed_fields = [
            'name', 'description', 'sku', 'stock_quantity', 'minimum_stock',
            'buying_price', 'retail_price', 'wholesale_price', 'sales_type',
            'category', 'subcategory', 'unit_type', 'sell_by', 'is_active'
        ]

        # Validate and update fields
        for key, value in item_data.items():
            if key in allowed_fields and key not in ['category']:  # Skip category as it's handled above
                # Special handling for numeric fields
                if key in ['stock_quantity', 'minimum_stock']:
                    try:
                        value = int(value) if value is not None else 0
                    except (ValueError, TypeError):
                        return jsonify({"error": f"Invalid {key} format"}), 400
                elif key in ['buying_price', 'retail_price', 'wholesale_price']:
                    try:
                        value = float(value) if value is not None else 0.0
                    except (ValueError, TypeError):
                        return jsonify({"error": f"Invalid {key} format"}), 400
                elif key == 'name' and not value:
                    return jsonify({"error": "Item name cannot be empty"}), 400

                setattr(item, key, value)

        # Update timestamp
        item.updated_at = datetime.utcnow()

        # Check SKU uniqueness if changed
        if 'sku' in item_data and item_data['sku'] != item.sku:
            existing_item = Item.query.filter_by(
                sku=item_data['sku'], 
                user_id=current_user_id
            ).filter(Item.id != item_id).first()

            if existing_item:
                return jsonify({"error": f"SKU '{item_data['sku']}' already exists"}), 400

        # Save to database
        db.session.commit()

        logger.info(f"Item updated: {item.name} (ID: {item.id}) by user {current_user_id}")

        # Check for low stock notification
        if item.stock_quantity <= item.minimum_stock:
            try:
                from notifications.notification_manager import check_low_stock_and_notify
                import threading

                notification_thread = threading.Thread(
                    target=check_low_stock_and_notify,
                    args=(db, Item, Setting))
                notification_thread.daemon = True
                notification_thread.start()
            except Exception as e:
                logger.warning(f"Could not trigger low stock notification: {str(e)}")

        return jsonify(item.to_dict())

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating item: {str(e)}")
        return jsonify({"error": f"Failed to update item: {str(e)}"}), 500

def verify_postgresql_auth():
    """Verify that PostgreSQL authentication is working properly"""
    try:
        # Test database connection
        from models import User
        user_count = User.query.count()
        logger.info(f"✅ PostgreSQL authentication ready - {user_count} users in database")
        return True
    except Exception as e:
        logger.error(f"❌ PostgreSQL authentication error: {str(e)}")
        return False

# Verify PostgreSQL authentication on startup
with app.app_context():
    if verify_postgresql_auth():
        logger.info("🔐 PostgreSQL authentication system initialized successfully")
    else:
        logger.warning("⚠️ PostgreSQL authentication system may have issues")

@app.route('/api/inventory/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    """API endpoint to delete an inventory item"""
    from models import Item

    try:
        item = Item.query.get(item_id)

        if item is None:
            return jsonify({"error": "Item not found"}), 404

        # Store item details before deletion
        item_dict = item.to_dict()
        item_name = item.name

        # Remove item from database
        db.session.delete(item)
        db.session.commit()

        return jsonify({"message": f"Deleted {item_name}", "item": item_dict})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting item: {str(e)}")
        return jsonify({"error": "Failed to delete item"}), 500

@app.route('/api/inventory/batch-update', methods=['PUT'])
@login_required
def batch_update_inventory():
    """API endpoint for batch updating inventory items"""
    try:
        from models import Item

        batch_data = request.get_json()
        if not batch_data or 'items' not in batch_data:
            return jsonify({"error": "No items provided for batch update"}), 400

        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({"error": "User not authenticated"}), 401

        updated_items = []
        errors = []

        for item_update in batch_data['items']:
            try:
                item_id = item_update.get('id')
                if not item_id:
                    errors.append("Item ID is required for batch update")
                    continue

                item = Item.query.filter_by(id=item_id, user_id=current_user_id).first()
                if not item:
                    errors.append(f"Item with ID {item_id} not found")
                    continue

                # Update allowed fields
                allowed_fields = ['stock_quantity', 'minimum_stock', 'retail_price', 'wholesale_price', 'buying_price']
                for field in allowed_fields:
                    if field in item_update:
                        if field in ['stock_quantity', 'minimum_stock']:
                            setattr(item, field, int(item_update[field]))
                        else:
                            setattr(item, field, float(item_update[field]))

                item.updated_at = datetime.utcnow()
                updated_items.append(item.to_dict())

            except Exception as e:
                errors.append(f"Error updating item {item_id}: {str(e)}")

        if updated_items:
            db.session.commit()
            logger.info(f"Batch updated {len(updated_items)} items for user {current_user_id}")

        return jsonify({
            "success": True,
            "updated_count": len(updated_items),
            "updated_items": updated_items,
            "errors": errors
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in batch update: {str(e)}")
        return jsonify({"error": f"Batch update failed: {str(e)}"}), 500

@app.route('/api/inventory/bulk-import', methods=['POST'])
@login_required
def bulk_import_inventory():
    """API endpoint to handle bulk import of inventory items from CSV"""
    from services.csv_import_service import CSVImportService

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    if not file or file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        # Get current user ID
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Initialize import service with user_id
        import_service = CSVImportService(db.session, Item, current_user_id)

        # Process the import
        result = import_service.process_csv_import(file)

        # Log the import result
        logger.info(f"CSV import result for user {current_user_id}: {result}")

        # Return appropriate status code
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        db.session.rollback()
        logger.error(f"Bulk import failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Import failed: {str(e)}",
            "imported_count": 0,
            "total_rows": 0,
            "errors": [f"System error: {str(e)}"]
        }), 500

@app.route('/api/inventory/csv-template', methods=['GET'])
def get_csv_template():
    """API endpoint to get CSV template and format information"""
    from services.csv_import_service import CSVTemplateGenerator

    template_type = request.args.get('type', 'info')

    if template_type == 'download':
        # Return sample CSV data for download
        sample_data = CSVTemplateGenerator.get_sample_csv_data()

        return send_file(
            io.BytesIO(sample_data.encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'inventory_import_template_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    else:
        # Return format information
        format_info = CSVTemplateGenerator.get_format_instructions()
        return jsonify(format_info)

@app.route('/api/inventory/categories', methods=['GET'])
def get_inventory_categories():
    """API endpoint to get all unique inventory categories"""
    from models import Item
    from sqlalchemy import func

    # Query distinct categories
    categories = db.session.query(
        func.coalesce(Item.category,
                      'Uncategorized').label('category')).distinct().all()

    return jsonify([c.category for c in categories])

@app.route('/api/products', methods=['GET'])
def get_products():
    """API endpoint to get all products (alias for inventory)"""
    from models import Item

    # Start query
    query = Item.query

    # Optional filtering
    category = request.args.get('category')
    search_term = request.args.get('search', '').lower()
    min_stock = request.args.get('min_stock')
    max_stock = request.args.get('max_stock')

    # Apply filters if provided
    if category:
        query = query.filter(Item.category == category)

    if search_term:
        search_filter = (Item.name.ilike(f'%{search_term}%')
                         | Item.sku.ilike(f'%{search_term}%')
                         | Item.description.ilike(f'%{search_term}%'))
        query = query.filter(search_filter)

    if min_stock:
        try:
            min_stock = int(min_stock)
            query = query.filter(Item.stock_quantity >= min_stock)
        except ValueError:
            pass

    if max_stock:
        try:
            max_stock = int(max_stock)
            query = query.filter(Item.stock_quantity <= max_stock)
        except ValueError:
            pass

    # Execute query and convert to dictionary
    items = [item.to_dict() for item in query.all()]
    return jsonify(items)

# Removed duplicate sales reports endpoint - use /api/sales instead

@app.route('/api/reports/stock')
@login_required
def api_stock_reports():
    try:
        report_type = request.args.get('type', 'stock-available')
        threshold = request.args.get('threshold', 10, type=int)

        if report_type == 'stock-available':
            items = Item.query.filter_by(user_id=session['user_id']).all()

            total_items = len(items)
            total_stock = sum(item.stock_quantity for item in items)
            low_stock_items = [item for item in items if item.stock_quantity <= threshold]
            out_of_stock_items = [item for item in items if item.stock_quantity == 0]

            items_data = []
            for item in items:
                items_data.append({
                    'id': item.id,
                    'name': item.name,
                    'sku': item.sku,
                    'category': item.category.name if item.category else None,
                    'stock_quantity': item.stock_quantity,
                    'minimum_stock': item.minimum_stock or 0,
                    'price': float(item.retail_price or 0)
                })

            return jsonify({
                'success': True,
                'total_items': total_items,
                'total_stock': total_stock,
                'low_stock_count': len(low_stock_items),
                'out_of_stock_count': len(out_of_stock_items),
                'items': items_data
            })

        elif report_type == 'stock-transactions':
            # Get stock movements
            movements = StockMovement.query.filter_by(user_id=session['user_id']).order_by(
                StockMovement.created_at.desc()
            ).limit(100).all()

            transactions_data = []
            for movement in movements:
                transactions_data.append({
                    'date': movement.created_at.isoformat(),
                    'item_name': movement.item.name,
                    'type': movement.movement_type,
                    'quantity': movement.quantity,
                    'reason': movement.reason,
                    'reference': movement.reference_number
                })

            return jsonify({
                'success': True,
                'transactions': transactions_data
            })

        elif report_type == 'stock-issues':
            # Get stock issues (expired, broken, stolen)
            issues = StockMovement.query.filter_by(
                user_id=session['user_id'],
                movement_type='out'
            ).filter(
                StockMovement.reason.in_(['expired', 'broken', 'stolen'])
            ).order_by(StockMovement.created_at.desc()).all()

            issues_data = []
            for issue in issues:
                value_lost = issue.quantity * (issue.item.buying_price or 0)
                issues_data.append({
                    'date': issue.created_at.isoformat(),
                    'item_name': issue.item.name,
                    'type': issue.reason,
                    'quantity': issue.quantity,
                    'value_lost': float(value_lost),
                    'notes': issue.notes
                })

            return jsonify({
                'success': True,
                'issues': issues_data
            })

    except Exception as e:
        logger.error(f"Error generating stock report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/accounting')
@login_required
def api_accounting_reports():
    try:
        report_type = request.args.get('type', 'profit-loss')
        period = request.args.get('period', 'month')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')

        # Calculate date range
        if period == 'month':
            start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = datetime.now()
        elif period == 'quarter':
            current_month = datetime.now().month
            quarter_start_month = 1 + 3 * ((current_month - 1) // 3)
            start = datetime.now().replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = datetime.now()
        elif period == 'year':
            start = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = datetime.now()
        elif period == 'custom' and start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        else:
            start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = datetime.now()

        if report_type == 'profit-loss' or report_type == 'income-statement':
            # Calculate revenue from sales
            total_revenue = db.session.query(func.sum(Sale.total_amount)).filter(
                Sale.user_id == session['user_id'],
                Sale.created_at >= start,
                Sale.created_at <= end,
                Sale.payment_status == 'completed'
            ).scalar() or 0

            # Calculate expenses
            total_expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == session['user_id'],
                FinancialTransaction.transaction_type == 'expense',
                FinancialTransaction.created_at >= start,
                FinancialTransaction.created_at <= end
            ).scalar() or 0

            net_profit = total_revenue - total_expenses
            profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

            breakdown = [
                {'account': 'Sales Revenue', 'amount': float(total_revenue), 'percentage': 100.0},
                {'account': 'Operating Expenses', 'amount': float(total_expenses), 'percentage': (total_expenses / total_revenue * 100) if total_revenue > 0 else 0},
                {'account': 'Net Profit', 'amount': float(net_profit), 'percentage': profit_margin}
            ]

            return jsonify({
                'success': True,
                'revenue': float(total_revenue),
                'expenses': float(total_expenses),
                'net_profit': float(net_profit),
                'profit_margin': profit_margin,
                'breakdown': breakdown
            })

        elif report_type == 'balance-sheet':
            # Simplified balance sheet
            inventory_value = db.session.query(func.sum(Item.stock_quantity * Item.buying_price)).filter(
                Item.user_id == session['user_id']
            ).scalar() or 0

            cash_balance = 50000  # Placeholder - you'd get this from a cash account

            items = [
                {'type': 'Assets', 'account': 'Inventory', 'amount': float(inventory_value)},
                {'type': 'Assets', 'account': 'Cash', 'amount': float(cash_balance)},
                {'type': 'Equity', 'account': 'Owner Equity', 'amount': float(inventory_value + cash_balance)}
            ]

            return jsonify({
                'success': True,
                'items': items
            })

        elif report_type == 'expenses':
            expenses = FinancialTransaction.query.filter(
                FinancialTransaction.user_id == session['user_id'],
                FinancialTransaction.transaction_type == 'expense',
                FinancialTransaction.created_at >= start,
                FinancialTransaction.created_at <= end
            ).order_by(FinancialTransaction.created_at.desc()).all()

            items = []
            for expense in expenses:
                items.append({
                    'date': expense.created_at.isoformat(),
                    'category': expense.category,
                    'description': expense.description,
                    'amount': float(expense.amount)
                })

            return jsonify({
                'success': True,
                'items': items
            })

    except Exception as e:
        logger.error(f"Error generating accounting report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/stock-status')
@login_required
def api_stock_status_report():
    try:
        low_stock_threshold = request.args.get('low_stock_threshold', 10, type=int)

        # Get all items for current user
        items = Item.query.filter_by(user_id=session['user_id']).all()

        total_items = len(items)
        total_stock = sum(item.stock_quantity for item in items)

        # Low stock items
        low_stock_items = [item for item in items if item.stock_quantity <= low_stock_threshold]
        out_of_stock_items = [item for item in items if item.stock_quantity == 0]

        # Format low stock items data
        low_stock_data = []
        for item in low_stock_items:
            low_stock_data.append({
                'id': item.id,
                'name': item.name,
                'sku': item.sku,
                'category': item.category,
                'quantity': item.stock_quantity,
                'price': float(item.retail_price or 0)
            })

        return jsonify({
            'success': True,
            'total_items': total_items,
            'total_stock': total_stock,
            'low_stock_items_count': len(low_stock_items),
            'out_of_stock_items_count': len(out_of_stock_items),
            'low_stock_items': low_stock_data
        })

    except Exception as e:
        logger.error(f"Error generating stock status report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Removed duplicate transactions endpoint - use /api/sales instead

# Sales API Routes
@app.route('/api/sales', methods=['GET'])
@login_required
def get_sales():
    """API endpoint to get all sales"""
    try:
        user_id = session.get('user_id')
        sales = Sale.query.filter_by(user_id=user_id).order_by(Sale.created_at.desc()).all()

        sales_data = []
        for sale in sales:
            sale_dict = {
                'id': sale.id,
                'sale_number': sale.sale_number,
                'created_at': sale.created_at.isoformat(),
                'customer_name': sale.customer.name if sale.customer else None,
                'customer_id': sale.customer_id,
                'total_amount': float(sale.total_amount),
                'payment_type': sale.payment_type,
                'payment_status': sale.payment_status,
                'is_installment': sale.is_installment,
                'items_count': len(sale.sale_items)
            }

            # Add installment details if applicable
            if sale.is_installment:
                sale_dict.update({
                    'down_payment': float(sale.down_payment or 0),
                    'installment_months': sale.installment_months,
                    'monthly_payment': float(sale.monthly_payment or 0)
                })

            sales_data.append(sale_dict)

        return jsonify(sales_data)

    except Exception as e:
        logger.error(f"Error getting sales: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales', methods=['POST'])
@login_required
def create_sale():
    """API endpoint to create a new sale"""
    try:
        from models import Sale, SaleItem, Customer, Item

        sale_data = request.get_json()
        if not sale_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Validate required fields
        items = sale_data.get('items', [])
        if not items:
            return jsonify({"error": "No items provided"}), 400

        payment_type = sale_data.get('payment_type', 'cash')
        customer_id = sale_data.get('customer_id')
        is_installment = sale_data.get('is_installment', False)

        # Handle customer data
        customer = None
        if customer_id:
            customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first()
        elif sale_data.get('customer_name'):
            # Create new customer if provided
            customer = Customer(
                name=sale_data['customer_name'],
                email=sale_data.get('customer_email'),
                phone=sale_data.get('customer_phone'),
                address=sale_data.get('customer_address'),
                user_id=user_id
            )
            db.session.add(customer)
            db.session.flush()

        # Calculate total amount
        total_amount = 0
        sale_items_data = []

        for item_data in items:
            item_id = item_data.get('item_id') or item_data.get('id')
            quantity = int(item_data.get('quantity', 1))
            unit_price = float(item_data.get('unit_price') or item_data.get('price', 0))

            if not item_id:
                return jsonify({"error": "Item ID is required"}), 400

            # Get item and verify stock
            item = Item.query.filter_by(id=item_id, user_id=user_id).first()
            if not item:
                return jsonify({"error": f"Item with ID {item_id} not found"}), 404

            if item.stock_quantity < quantity:
                return jsonify({"error": f"Insufficient stock for {item.name}"}), 400

            subtotal = quantity * unit_price
            total_amount += subtotal

            sale_items_data.append({
                'item': item,
                'quantity': quantity,
                'unit_price': unit_price,
                'subtotal': subtotal
            })

        # Create sale record
        sale = Sale(
            user_id=user_id,
            customer_id=customer.id if customer else None,
            total_amount=total_amount,
            payment_type=payment_type,
            payment_status='completed' if not is_installment else 'pending',
            is_installment=is_installment,
            sale_number=Sale.generate_sale_number()
        )

        # Handle installment data
        if is_installment:
            sale.down_payment = float(sale_data.get('down_payment', 0))
            sale.installment_months = int(sale_data.get('installment_months', 1))
            remaining_amount = total_amount - sale.down_payment
            sale.monthly_payment = remaining_amount / sale.installment_months if sale.installment_months > 0 else 0

        db.session.add(sale)
        db.session.flush()

        # Create sale items and update stock
        for item_data in sale_items_data:
            sale_item = SaleItem(
                sale_id=sale.id,
                item_id=item_data['item'].id,
                quantity=item_data['quantity'],
                unit_price=item_data['unit_price'],
                subtotal=item_data['subtotal']
            )
            db.session.add(sale_item)

            # Update stock
            item_data['item'].stock_quantity -= item_data['quantity']

        # Create installment plan if needed
        if is_installment:
            from models import InstallmentSale, InstallmentPayment

            installment_sale = InstallmentSale(
                sale_id=sale.id,
                customer_id=customer.id if customer else None,
                total_amount=total_amount,
                down_payment=sale.down_payment,
                remaining_amount=total_amount - sale.down_payment,
                payment_frequency='monthly',
                duration_months=sale.installment_months,
                monthly_payment=sale.monthly_payment,
                user_id=user_id
            )
            db.session.add(installment_sale)
            db.session.flush()

            # Create initial payment record for down payment if any
            if sale.down_payment > 0:
                payment = InstallmentPayment(
                    installment_sale_id=installment_sale.id,
                    amount=sale.down_payment,
                    payment_date=datetime.utcnow(),
                    payment_method=payment_type,
                    status='completed',
                    user_id=user_id
                )
                db.session.add(payment)

        db.session.commit()

        logger.info(f"Sale created: {sale.sale_number} for user {user_id}")

        return jsonify({
            'success': True,
            'sale': {
                'id': sale.id,
                'sale_number': sale.sale_number,
                'total_amount': float(sale.total_amount),
                'payment_type': sale.payment_type,
                'is_installment': sale.is_installment
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating sale: {str(e)}")
        return jsonify({"error": f"Failed to create sale: {str(e)}"}), 500

# Customer API Routes
@app.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    """API endpoint to get all customers"""
    try:
        from models import Customer

        user_id = session.get('user_id')
        customers = Customer.query.filter_by(user_id=user_id).order_by(Customer.name).all()

        customers_data = []
        for customer in customers:
            customers_data.append({
                'id': customer.id,
                'name': customer.name,
                'email': customer.email,
                'phone': customer.phone,
                'address': customer.address,
                'customer_type': customer.customer_type,
                'credit_limit': float(customer.credit_limit or 0),
                'loyalty_points': customer.loyalty_points or 0,
                'created_at': customer.created_at.isoformat() if customer.created_at else None
            })

        return jsonify(customers_data)

    except Exception as e:
        logger.error(f"Error getting customers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers', methods=['POST'])
@login_required
def create_customer():
    """API endpoint to create a new customer"""
    try:
        from models import Customer

        customer_data = request.get_json()
        if not customer_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Validate required fields
        if not customer_data.get('name'):
            return jsonify({"error": "Customer name is required"}), 400

        # Create new customer
        customer = Customer(
            name=customer_data['name'].strip(),
            email=customer_data.get('email', '').strip() or None,
            phone=customer_data.get('phone', '').strip() or None,
            address=customer_data.get('address', '').strip() or None,
            customer_type=customer_data.get('customer_type', 'retail'),
            credit_limit=float(customer_data.get('credit_limit', 0)),
            preferred_payment_method=customer_data.get('preferred_payment_method'),
            user_id=user_id
        )

        db.session.add(customer)
        db.session.commit()

        logger.info(f"Customer created: {customer.name} (ID: {customer.id}) by user {user_id}")

        return jsonify({
            'id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'address': customer.address,
            'customer_type': customer.customer_type,
            'credit_limit': float(customer.credit_limit),
            'created_at': customer.created_at.isoformat()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating customer: {str(e)}")
        return jsonify({"error": f"Failed to create customer: {str(e)}"}), 500

# Additional Customer API Routes
@app.route('/api/customers/<int:customer_id>', methods=['GET'])
@login_required
def get_customer(customer_id):
    """API endpoint to get a specific customer"""
    try:
        from models import Customer
        user_id = session.get('user_id')
        customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first()

        if not customer:
            return jsonify({'error': 'Customer not found'}), 404

        return jsonify({
            'id': customer.id,
            'name': customer.name,
            'email': customer.email,
            'phone': customer.phone,
            'address': customer.address,
            'customer_type': customer.customer_type,
            'credit_limit': float(customer.credit_limit or 0),
            'loyalty_points': customer.loyalty_points or 0,
            'created_at': customer.created_at.isoformat() if customer.created_at else None
        })
    except Exception as e:
        logger.error(f"Error getting customer: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Installment API Routes
@app.route('/api/installments', methods=['GET'])
@login_required
def get_installments():
    """API endpoint to get all installment sales"""
    try:
        from models import InstallmentSale

        user_id = session.get('user_id')
        installments = InstallmentSale.query.filter_by(user_id=user_id).order_by(InstallmentSale.created_at.desc()).all()

        installments_data = []
        for installment in installments:
            installments_data.append({
                'id': installment.id,
                'sale_id': installment.sale_id,
                'customer_name': installment.customer.name if installment.customer else None,
                'total_amount': float(installment.total_amount),
                'down_payment': float(installment.down_payment or 0),
                'remaining_amount': float(installment.remaining_amount),
                'monthly_payment': float(installment.monthly_payment),
                'duration_months': installment.duration_months,
                'payments_made': len(installment.payments),
                'status': installment.status,
                'created_at': installment.created_at.isoformat()
            })

        return jsonify(installments_data)

    except Exception as e:
        logger.error(f"Error getting installments: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/installments', methods=['POST'])
@login_required
def create_installment():
    """API endpoint to create a new installment sale"""
    try:
        from models import InstallmentSale, Sale, Customer

        installment_data = request.get_json()
        if not installment_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Validate required fields
        sale_id = installment_data.get('sale_id')
        if not sale_id:
            return jsonify({"error": "Sale ID is required"}), 400

        # Get the sale
        sale = Sale.query.filter_by(id=sale_id, user_id=user_id).first()
        if not sale:
            return jsonify({"error": "Sale not found"}), 404

        # Check if installment already exists
        existing_installment = InstallmentSale.query.filter_by(sale_id=sale_id).first()
        if existing_installment:
            return jsonify({"error": "Installment plan already exists for this sale"}), 400

        # Create installment plan
        down_payment = float(installment_data.get('down_payment', 0))
        duration_months = int(installment_data.get('duration_months', 1))
        remaining_amount = sale.total_amount - down_payment
        monthly_payment = remaining_amount / duration_months if duration_months > 0 else 0

        installment = InstallmentSale(
            sale_id=sale.id,
            customer_id=sale.customer_id,
            total_amount=sale.total_amount,
            down_payment=down_payment,
            remaining_amount=remaining_amount,
            payment_frequency='monthly',
            duration_months=duration_months,
            monthly_payment=monthly_payment,
            status='active',
            user_id=user_id
        )

        db.session.add(installment)
        db.session.commit()

        logger.info(f"Installment created for sale {sale_id} by user {user_id}")

        return jsonify({
            'success': True,
            'installment': {
                'id': installment.id,
                'sale_id': installment.sale_id,
                'total_amount': float(installment.total_amount),
                'down_payment': float(installment.down_payment),
                'monthly_payment': float(installment.monthly_payment),
                'duration_months': installment.duration_months
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating installment: {str(e)}")
        return jsonify({"error": f"Failed to create installment: {str(e)}"}), 500

# Categories API Routes
@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    """API endpoint to get all categories with hierarchical structure"""
    try:
        from models import Category

        user_id = session.get('user_id')
        all_categories = Category.query.filter_by(user_id=user_id).order_by(Category.name).all()

        # Separate parent categories and subcategories
        parent_categories = [cat for cat in all_categories if cat.parent_id is None]
        subcategories_dict = {}

        # Group subcategories by parent_id
        for cat in all_categories:
            if cat.parent_id is not None:
                if cat.parent_id not in subcategories_dict:
                    subcategories_dict[cat.parent_id] = []
                subcategories_dict[cat.parent_id].append(cat)

        categories_data = []
        for category in parent_categories:
            category_dict = {
                'id': category.id,
                'name': category.name,
                'description': category.description,
                'parent_id': category.parent_id,
                'is_active': category.is_active,
                'item_count': category.get_item_count(),
                'total_item_count': category.get_total_item_count(),
                'created_at': category.created_at.isoformat() if category.created_at else None,
                'subcategories': []
            }

            # Add subcategories if they exist
            if category.id in subcategories_dict:
                for subcategory in subcategories_dict[category.id]:
                    subcategory_dict = {
                        'id': subcategory.id,
                        'name': subcategory.name,
                        'description': subcategory.description,
                        'parent_id': subcategory.parent_id,
                        'is_active': subcategory.is_active,
                        'item_count': subcategory.get_item_count(),
                        'total_item_count': subcategory.get_total_item_count(),
                        'created_at': subcategory.created_at.isoformat() if subcategory.created_at else None
                    }
                    category_dict['subcategories'].append(subcategory_dict)

            categories_data.append(category_dict)

        return jsonify(categories_data)

    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<int:category_id>', methods=['GET'])
@login_required
def get_category(category_id):
    """API endpoint to get a specific category"""
    try:
        from models import Category
        user_id = session.get('user_id')
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()

        if not category:
            return jsonify({'error': 'Category not found'}), 404

        return jsonify({
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'parent_id': category.parent_id,
            'created_at': category.created_at.isoformat() if category.created_at else None
        })
    except Exception as e:
        logger.error(f"Error getting category: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['POST'])
@login_required
def create_category():
    """API endpoint to create a new category"""
    try:
        from models import Category

        category_data = request.get_json()
        if not category_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Validate required fields
        if not category_data.get('name'):
            return jsonify({"error": "Category name is required"}), 400

        # Check if category already exists
        existing_category = Category.query.filter_by(
            name=category_data['name'], 
            user_id=user_id
        ).first()
        if existing_category:
            return jsonify({"error": "Category already exists"}), 400

        # Create new category
        category = Category(
            name=category_data['name'].strip(),
            description=category_data.get('description', '').strip(),
            parent_id=category_data.get('parent_id'),
            user_id=user_id
        )

        db.session.add(category)
        db.session.commit()

        logger.info(f"Category created: {category.name} (ID: {category.id}) by user {user_id}")

        return jsonify({
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'parent_id': category.parent_id,
            'created_at': category.created_at.isoformat()
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating category: {str(e)}")
        return jsonify({"error": f"Failed to create category: {str(e)}"}), 500

@app.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    """API endpoint to update an existing category"""
    try:
        from models import Category

        category_data = request.get_json()
        if not category_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not category:
            return jsonify({"error": "Category not found"}), 404

        # Update allowed fields only
        if 'name' in category_data:
            # Check if the updated name already exists for another category owned by the same user
            existing_category = Category.query.filter_by(
                name=category_data['name'],
                user_id=user_id
            ).filter(Category.id != category_id).first()

            if existing_category:
                return jsonify({"error": "Category name already exists"}), 400
            category.name = category_data['name'].strip()

        if 'description' in category_data:
            category.description = category_data['description'].strip()
        if 'parent_id' in category_data:
            category.parent_id = category_data['parent_id']

        db.session.commit()

        logger.info(f"Category updated: {category.name} (ID: {category.id}) by user {user_id}")

        return jsonify({
            'id': category.id,
            'name': category.name,
            'description': category.description,
            'parent_id': category.parent_id,
            'created_at': category.created_at.isoformat() if category.created_at else None
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating category: {str(e)}")
        return jsonify({"error": f"Failed to update category: {str(e)}"}), 500

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    """API endpoint to delete a category"""
    try:
        from models import Category

        user_id = session.get('user_id')
        category = Category.query.filter_by(id=category_id, user_id=user_id).first()

        if not category:
            return jsonify({"error": "Category not found"}), 404

        # Check if there are items associated with the category
        from models import Item
        items_in_category = Item.query.filter_by(category_id=category_id, user_id=user_id).count()

        if items_in_category > 0:
            return jsonify({"error": "Cannot delete category with associated items"}), 400

        # Check if there are subcategories
        subcategories = Category.query.filter_by(parent_id=category_id, user_id=user_id).count()
        if subcategories > 0:
            return jsonify({"error": "Cannot delete category with subcategories"}), 400

        # Delete the category
        db.session.delete(category)
        db.session.commit()

        logger.info(f"Category deleted: {category.name} (ID: {category.id}) by user {user_id}")

        return jsonify({"success": True, "message": f"Category '{category.name}' deleted successfully"})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting category: {str(e)}")
        return jsonify({"error": f"Failed to delete category: {str(e)}"}), 500

@app.route('/api/categories/<int:category_id>/subcategories', methods=['GET'])
@login_required
def get_subcategories(category_id):
    """API endpoint to get subcategories of a category"""
    try:
        from models import Category

        user_id = session.get('user_id')
        parent_category = Category.query.filter_by(id=category_id, user_id=user_id).first()

        if not parent_category:
            return jsonify({"error": "Parent category not found"}), 404

        subcategories = Category.query.filter_by(parent_id=category_id, user_id=user_id).order_by(Category.name).all()

        subcategories_data = []
        for subcategory in subcategories:
            subcategories_data.append({
                'id': subcategory.id,
                'name': subcategory.name,
                'description': subcategory.description,
                'parent_id': subcategory.parent_id,
                'item_count': subcategory.get_item_count(),
                'total_item_count': subcategory.get_total_item_count(),
                'created_at': subcategory.created_at.isoformat() if subcategory.created_at else None
            })

        return jsonify(subcategories_data)

    except Exception as e:
        logger.error(f"Error getting subcategories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<int:category_id>/subcategories', methods=['POST'])
@login_required
def create_subcategory(category_id):
    """API endpoint to create a subcategory"""
    try:
        from models import Category

        subcategory_data = request.get_json()
        if not subcategory_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Verify parent category exists
        parent_category = Category.query.filter_by(id=category_id, user_id=user_id).first()
        if not parent_category:
            return jsonify({"error": "Parent category not found"}), 404

        # Validate required fields
        if not subcategory_data.get('name'):
            return jsonify({"error": "Subcategory name is required"}), 400

        # Check if subcategory already exists under this parent
        existing_subcategory = Category.query.filter_by(
            name=subcategory_data['name'], 
            parent_id=category_id,
            user_id=user_id
        ).first()
        if existing_subcategory:
            return jsonify({"error": "Subcategory already exists under this category"}), 400

        # Create new subcategory
        subcategory = Category(
            name=subcategory_data['name'].strip(),
            description=subcategory_data.get('description', '').strip(),
            parent_id=category_id,
            user_id=user_id
        )

        db.session.add(subcategory)
        db.session.commit()

        logger.info(f"Subcategory created: {subcategory.name} (ID: {subcategory.id}) under category {parent_category.name} by user {user_id}")

        return jsonify({
            'success': True,
            'subcategory': {
                'id': subcategory.id,
                'name': subcategory.name,
                'description': subcategory.description,
                'parent_id': subcategory.parent_id,
                'item_count': subcategory.get_item_count(),
                'created_at': subcategory.created_at.isoformat()
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating subcategory: {str(e)}")
        return jsonify({"error": f"Failed to create subcategory: {str(e)}"}), 500

# Dashboard API Routes
@app.route('/api/dashboard/summary')
@login_required
def get_dashboard_summary():
    """API endpoint to get comprehensive dashboard summary data organized by categories"""
    try:
        from models import Item, Sale, Customer, FinancialTransaction, SaleItem, Category
        from sqlalchemy import func
        from datetime import datetime, timedelta

        user_id = session.get('user_id')

        # === INVENTORY METRICS ===
        total_items = Item.query.filter_by(user_id=user_id, is_active=True).count()
        total_stock = db.session.query(func.sum(Item.stock_quantity)).filter(
            Item.user_id == user_id,
            Item.is_active == True
        ).scalar() or 0

        # Calculate inventory value (stock_quantity * buying_price)
        inventory_value = db.session.query(
            func.sum(Item.stock_quantity * Item.buying_price)
        ).filter(
            Item.user_id == user_id,
            Item.is_active == True,
            Item.buying_price.isnot(None)
        ).scalar() or 0

        # Low stock items analysis
        low_stock_items_query = Item.query.filter(
            Item.user_id == user_id,
            Item.is_active == True,
            Item.stock_quantity <= Item.minimum_stock
        )
        low_stock_count = low_stock_items_query.count()

        # Get detailed low stock items
        low_stock_items = []
        for item in low_stock_items_query.limit(10).all():
            low_stock_items.append({
                'id': item.id,
                'name': item.name,
                'current_stock': item.stock_quantity,
                'minimum_stock': item.minimum_stock,
                'category': item.category
            })

        # === SALES METRICS ===
        total_sales = Sale.query.filter_by(user_id=user_id).count()

        # Get revenue (completed sales only)
        total_revenue = db.session.query(func.sum(Sale.total_amount)).filter(
            Sale.user_id == user_id,
            Sale.payment_status == 'completed'
        ).scalar() or 0

        # Today's sales
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        tomorrow = today + timedelta(days=1)

        today_sales = db.session.query(func.sum(Sale.total_amount)).filter(
            Sale.user_id == user_id,
            Sale.payment_status == 'completed',
            Sale.created_at >= today,
            Sale.created_at < tomorrow
        ).scalar() or 0

        today_sales_count = Sale.query.filter(
            Sale.user_id == user_id,
            Sale.created_at >= today,
            Sale.created_at < tomorrow
        ).count()

        # === CUSTOMER METRICS ===
        total_customers = Customer.query.filter_by(user_id=user_id).count()

        # New customers this month
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        new_customers_this_month = Customer.query.filter(
            Customer.user_id == user_id,
            Customer.created_at >= current_month
        ).count()

        # === FINANCIAL METRICS ===
        next_month = (current_month + timedelta(days=32)).replace(day=1)

        # Monthly income from sales
        monthly_income = db.session.query(func.sum(Sale.total_amount)).filter(
            Sale.user_id == user_id,
            Sale.payment_status == 'completed',
            Sale.created_at >= current_month,
            Sale.created_at < next_month
        ).scalar() or 0

        # Monthly expenses
        monthly_expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
            FinancialTransaction.user_id == user_id,
            FinancialTransaction.transaction_type == 'expense',
            FinancialTransaction.created_at >= current_month,
            FinancialTransaction.created_at < next_month
        ).scalar() or 0

        # Monthly profit
        monthly_profit = monthly_income - monthly_expenses

        # === TOP SELLING ITEMS ===
        top_selling = db.session.query(
            Item.name,
            func.sum(SaleItem.quantity).label('total_sold')
        ).join(SaleItem).join(Sale).filter(
            Sale.user_id == user_id,
            Sale.created_at >= current_month
        ).group_by(Item.id, Item.name).order_by(
            func.sum(SaleItem.quantity).desc()
        ).limit(5).all()

        top_selling_items = []
        for item_name, quantity_sold in top_selling:
            top_selling_items.append({
                'name': item_name,
                'quantity_sold': int(quantity_sold)
            })

        # === RECENT SALES ===
        recent_sales = Sale.query.filter_by(user_id=user_id).order_by(
            Sale.created_at.desc()
        ).limit(5).all()

        recent_sales_data = []
        for sale in recent_sales:
            recent_sales_data.append({
                'id': sale.id,
                'sale_number': sale.sale_number,
                'customer_name': sale.customer.name if sale.customer else 'Walk-in Customer',
                'total_amount': float(sale.total_amount),
                'payment_status': sale.payment_status,
                'created_at': sale.created_at.isoformat()
            })

        # === CATEGORY BREAKDOWN ===
        category_stats = db.session.query(
            Item.category,
            func.count(Item.id).label('item_count'),
            func.sum(Item.stock_quantity).label('total_stock')
        ).filter(
            Item.user_id == user_id,
            Item.is_active == True
        ).group_by(Item.category).all()

        category_breakdown = []
        for category, item_count, total_stock in category_stats:
            category_breakdown.append({
                'category': category or 'Uncategorized',
                'item_count': int(item_count),
                'total_stock': int(total_stock or 0)
            })

        return jsonify({
            'success': True,
            'inventory': {
                'total_items': total_items,
                'total_stock': total_stock,
                'inventory_value': float(inventory_value),
                'low_stock_count': low_stock_count,
                'low_stock_items': low_stock_items,
                'category_breakdown': category_breakdown
            },
            'sales': {
                'total_sales': total_sales,
                'total_revenue': float(total_revenue),
                'today_sales': float(today_sales),
                'today_sales_count': today_sales_count,
                'top_selling_items': top_selling_items
            },
            'customers': {
                'total_customers': total_customers,
                'new_customers_this_month': new_customers_this_month
            },
            'financial': {
                'monthly_income': float(monthly_income),
                'monthly_expenses': float(monthly_expenses),
                'monthly_profit': float(monthly_profit)
            },
            'recent_activity': {
                'recent_sales': recent_sales_data
            }
        })

    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Financial API Routes
@app.route('/api/finance/transactions')
@login_required
def get_financial_transactions():
    """API endpoint to get financial transactions with date filtering"""
    try:
        from models import FinancialTransaction
        from datetime import datetime

        user_id = session.get('user_id')

        # Get date parameters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        transaction_type = request.args.get('type')  # 'income', 'expense', or None for all

        # Build query
        query = FinancialTransaction.query.filter_by(user_id=user_id)

        # Apply date filters
        if start_date:
            try:
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(FinancialTransaction.created_at >= start_date_obj)
            except ValueError:
                pass

        if end_date:
            try:
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(FinancialTransaction.created_at <= end_date_obj)
            except ValueError:
                pass

        # Apply transaction type filter
        if transaction_type:
            query = query.filter(FinancialTransaction.transaction_type == transaction_type)

        # Execute query
        transactions = query.order_by(FinancialTransaction.created_at.desc()).all()

        # Format response
        transactions_data = []
        for transaction in transactions:
            transactions_data.append({
                'id': transaction.id,
                'date': transaction.created_at.strftime('%Y-%m-%d'),
                'description': transaction.description,
                'amount': float(transaction.amount),
                'transaction_type': transaction.transaction_type,
                'category': transaction.category,                'payment_method': transaction.payment_method,
                'reference_id': transaction.reference_id,
                'notes': transaction.notes
            })

        return jsonify({
            'success': True,
            'transactions': transactions_data,
            'total_count': len(transactions_data)
        })

    except Exception as e:
        logger.error(f"Error getting financial transactions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/finance/summaries/monthly')
@login_required
def get_monthly_financial_summary():
    """API endpoint to get monthly financial summary"""
    try:
        from datetime import datetime, timedelta

        user_id = session.get('user_id')
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        next_month = (current_month + timedelta(days=32)).replace(day=1)

        # Get monthly data for the past 12 months
        monthly_data = {}
        for i in range(12):
            month_start = (current_month - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)

            # Get sales for this month
            monthly_sales = db.session.query(func.sum(Sale.total_amount)).filter(
                Sale.user_id == user_id,
                Sale.payment_status == 'completed',
                Sale.created_at >= month_start,
                Sale.created_at < month_end
            ).scalar() or 0

            # Get expenses for this month
            monthly_expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == user_id,
                FinancialTransaction.transaction_type == 'expense',
                FinancialTransaction.created_at >= month_start,
                FinancialTransaction.created_at < month_end
            ).scalar() or 0

            monthly_data[month_start.month] = {
                'income': float(monthly_sales),
                'expenses': float(monthly_expenses),
                'profit': float(monthly_sales - monthly_expenses)
            }

        return jsonify({
            'success': True,
            'monthly_data': monthly_data,
            'current_month': {
                'income': float(monthly_data.get(current_month.month, {}).get('income', 0)),
                'expenses': float(monthly_data.get(current_month.month, {}).get('expenses', 0)),
                'profit': float(monthly_data.get(current_month.month, {}).get('profit', 0))
            }
        })

    except Exception as e:
        logger.error(f"Error getting monthly financial summary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Missing API endpoints that frontend is trying to access
@app.route('/api/installment-sales', methods=['GET'])
@login_required
def get_installment_sales():
    """API endpoint to get all installment sales"""
    try:
        from models import InstallmentSale

        user_id = session.get('user_id')
        installment_sales = InstallmentSale.query.filter_by(user_id=user_id).order_by(InstallmentSale.created_at.desc()).all()

        sales_data = []
        for sale in installment_sales:
            sales_data.append({
                'id': sale.id,
                'sale_number': sale.sale.sale_number if sale.sale else f"INST-{sale.id}",
                'customer_name': sale.customer.name if sale.customer else 'Unknown Customer',
                'total_amount': float(sale.total_amount),
                'down_payment': float(sale.down_payment or 0),
                'remaining_amount': float(sale.remaining_amount),
                'monthly_payment': float(sale.monthly_payment),
                'duration_months': sale.duration_months,
                'status': sale.status,
                'created_at': sale.created_at.isoformat()
            })

        return jsonify({'success': True, 'installment_sales': sales_data})

    except Exception as e:
        logger.error(f"Error getting installment sales: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/installment-sales', methods=['POST'])
@login_required
def create_installment_sale():
    """API endpoint to create a new installment sale"""
    try:
        from models import InstallmentSale, InstallmentPayment, Customer, Item, Sale, SaleItem

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        user_id = session.get('user_id')

        # Handle customer creation or selection
        customer_id = data.get('customer_id')
        customer_data = data.get('customer_data')

        if customer_data and not customer_id:
            # Create new customer
            customer = Customer(
                name=customer_data['name'],
                phone=customer_data.get('phone'),
                email=customer_data.get('email'),
                address=customer_data.get('address'),
                national_id=customer_data.get('national_id'),
                customer_type='retail',
                user_id=user_id
            )
            db.session.add(customer)
            db.session.flush()
            customer_id = customer.id
        elif customer_id:
            customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first()
            if not customer:
                return jsonify({'error': 'Customer not found'}), 404
        else:
            return jsonify({'error': 'Customer information is required'}), 400

        # Get item details
        item_id = data.get('item_id')
        quantity = int(data.get('quantity', 1))

        item = Item.query.filter_by(id=item_id, user_id=user_id).first()
        if not item:
            return jsonify({'error': 'Item not found'}), 404

        if item.stock_quantity < quantity:
            return jsonify({'error': 'Insufficient stock'}), 400

        # Calculate amounts
        total_amount = float(data.get('total_amount'))
        down_payment = float(data.get('down_payment', 0))
        duration_months = int(data.get('number_of_installments', 1))
        remaining_amount = total_amount - down_payment
        monthly_payment = remaining_amount / duration_months if duration_months > 0 else 0

        # Create sale record first
        sale = Sale(
            user_id=user_id,
            customer_id=customer_id,
            total_amount=total_amount,
            payment_type='installment',
            payment_status='pending',
            is_installment=True,
            sale_number=Sale.generate_sale_number(),
            down_payment=down_payment,
            installment_months=duration_months,
            monthly_payment=monthly_payment
        )
        db.session.add(sale)
        db.session.flush()

        # Create sale item
        sale_item = SaleItem(
            sale_id=sale.id,
            item_id=item.id,
            quantity=quantity,
            unit_price=total_amount / quantity,
            subtotal=total_amount
        )
        db.session.add(sale_item)

        # Update stock
        item.stock_quantity -= quantity

        # Create installment plan
        installment_sale = InstallmentSale(
            sale_id=sale.id,
            customer_id=customer_id,
            total_amount=total_amount,
            down_payment=down_payment,
            remaining_amount=remaining_amount,
            payment_frequency='monthly',
            duration_months=duration_months,
            monthly_payment=monthly_payment,
            status='active',
            user_id=user_id
        )
        db.session.add(installment_sale)
        db.session.flush()

        # Create down payment record if applicable
        if down_payment > 0:
            payment = InstallmentPayment(
                installment_sale_id=installment_sale.id,
                amount=down_payment,
                payment_date=datetime.utcnow(),
                payment_method='cash',
                status='completed',
                user_id=user_id
            )
            db.session.add(payment)

        db.session.commit()

        return jsonify({
            'success': True,
            'sale_number': sale.sale_number,
            'installment_sale_id': installment_sale.id
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating installment sale: {str(e)}")
        return jsonify({'error': f'Failed to create installment sale: {str(e)}'}), 500

@app.route('/api/suppliers', methods=['GET'])
@login_required
def get_suppliers():
    """API endpoint to get all suppliers"""
    try:
        from models import Supplier

        user_id = session.get('user_id')
        suppliers = Supplier.query.filter_by(user_id=user_id, is_active=True).order_by(Supplier.name).all()

        suppliers_data = []
        for supplier in suppliers:
            suppliers_data.append({
                'id': supplier.id,
                'name': supplier.name,
                'contact_person': supplier.contact_person,
                'email': supplier.email,
                'phone': supplier.phone,
                'address': supplier.address,
                'payment_terms': supplier.payment_terms,
                'created_at': supplier.created_at.isoformat() if supplier.created_at else None
            })

        return jsonify({'success': True, 'suppliers': suppliers_data})

    except Exception as e:
        logger.error(f"Error getting suppliers: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/purchase-orders', methods=['GET'])
@login_required
def get_purchase_orders():
    """API endpoint to get all purchase orders"""
    try:
        from models import PurchaseOrder

        user_id = session.get('user_id')
        orders = PurchaseOrder.query.filter_by(user_id=user_id).order_by(PurchaseOrder.created_at.desc()).all()

        orders_data = []
        for order in orders:
            orders_data.append({
                'id': order.id,
                'order_number': order.order_number,
                'supplier_name': order.supplier.name if order.supplier else 'Unknown',
                'total_amount': float(order.total_amount),
                'status': order.status,
                'order_date': order.order_date.isoformat() if order.order_date else None,
                'expected_delivery': order.expected_delivery_date.isoformat() if order.expected_delivery_date else None
            })

        return jsonify({'success': True, 'purchase_orders': orders_data})

    except Exception as e:
        logger.error(f"Error getting purchase orders: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stock-movements', methods=['GET'])
@login_required
def get_stock_movements():
    """API endpoint to get stock movements"""
    try:
        from models import StockMovement

        user_id = session.get('user_id')
        movements = StockMovement.query.filter_by(user_id=user_id).order_by(StockMovement.created_at.desc()).limit(100).all()

        movements_data = []
        for movement in movements:
            movements_data.append({
                'id': movement.id,
                'item_name': movement.item.name if movement.item else 'Unknown Item',
                'movement_type': movement.movement_type,
                'quantity': movement.quantity,
                'reason': movement.reason,
                'reference_number': movement.reference_number,
                'notes': movement.notes,
                'created_at': movement.created_at.isoformat()
            })

        return jsonify({'success': True, 'stock_movements': movements_data})

    except Exception as e:
        logger.error(f"Error getting stock movements: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """API endpoint to get user settings"""
    try:
        from models import Setting

        user_id = session.get('user_id')
        settings = Setting.query.filter_by(user_id=user_id).all()

        settings_data = {}
        for setting in settings:
            settings_data[setting.key] = {
                'value': setting.value,
                'description': setting.description,
                'category': setting.category
            }

        return jsonify({'success': True, 'settings': settings_data})

    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    """API endpoint to update user settings"""
    try:
        from models import Setting

        data = request.get_json()
        user_id = session.get('user_id')

        for key, value in data.items():
            setting = Setting.query.filter_by(key=key, user_id=user_id).first()
            if setting:
                setting.value = str(value)
            else:
                setting = Setting(
                    key=key,
                    value=str(value),
                    user_id=user_id
                )
                db.session.add(setting)

        db.session.commit()

        return jsonify({'success': True, 'message': 'Settings updated successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Web Routes (Pages)
@app.route('/')
def index():
    """Home page route"""
    return render_template('cover.html')

@app.route('/login')
def login():
    """Login page route"""
    return render_template('login.html')

@app.route('/register')
def register():
    """Registration page route"""
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Dashboard page route"""
    return render_template('dashboard.html')

@app.route('/inventory')
@login_required
def inventory():
    """Inventory page route"""
    return render_template('inventory.html')

@app.route('/inventory/add')
@login_required
def add_item_page():
    """Add item page route"""
    return render_template('inventory.html')

# For backward compatibility
@app.route('/add-item')
@login_required
def add_item_redirect():
    """Redirect to inventory page for adding items"""
    return redirect(url_for('inventory'))

@app.route('/sales')
@login_required
def sales():
    """Sales page route"""
    return render_template('sales.html')

@app.route('/sales/new')
@login_required
def new_sale():
    """New sale page route"""
    return render_template('sales.html')

@app.route('/customers')
@login_required
def customers():
    """Customers page route"""
    # Check if template exists, fallback to placeholder
    try:
        return render_template('customers.html')
    except:
        return render_template('dashboard.html')  # Fallback

@app.route('/installments')
@login_required
def installments():
    """Installments page route"""
    return render_template('installments.html')

@app.route('/categories')
@login_required
def categories():
    """Categories page route"""
    return render_template('categories.html')

@app.route('/reports')
@login_required
def reports():
    """Reports page route"""
    return render_template('reports.html')

@app.route('/settings')
@login_required
def settings():
    """Settings page route"""
    return render_template('settings.html')

@app.route('/account')
@login_required
def account():
    """User account management page"""
    return render_template('account.html')

@app.route('/margin')
@login_required
def margin():
    """Margin analysis page"""
    return render_template('margin.html')

@app.route('/finance')
@login_required
def finance():
    """Finance management page"""
    return render_template('finance.html')

@app.route('/on_demand')
@login_required
def on_demand():
    """On-demand products page"""
    return render_template('on_demand.html')

@app.route('/admin_users')
@login_required
def admin_users():
    """Admin users management page"""
    user_id = session.get('user_id')
    from models import User
    if not user_id:
        return redirect(url_for('login'))

    user = User.query.get(user_id)
    if not user or not user.is_admin:
        flash('Access denied. Admin privileges required.', 'danger')
        return redirect(url_for('dashboard'))

    return render_template('admin_users.html')

@app.route('/accounting')
@login_required
def accounting():
    """Accounting dashboard page"""
    return render_template('accounting.html')

@app.route('/analytics')
@login_required
def analytics():
    """Analytics dashboard route"""
    return render_template('analytics_dashboard.html')

@app.route('/performance')
@login_required
def performance():
    """Performance dashboard route"""
    return render_template('performance_dashboard.html')

@app.route('/logout')
def logout():
    """Logout route"""
    session.clear()
    return redirect(url_for('index'))

# Debug route to help identify routing issues
@app.route('/debug/routes')
def debug_routes():
    """Debug endpoint to list all available routes"""
    routes = []
    for rule in app.url_map.iter_rules():
        routes.append({
            'endpoint': rule.endpoint,
            'methods': list(rule.methods),
            'rule': str(rule)
        })
    return jsonify(routes)

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    # Log the requested URL for debugging
    logger.warning(f"404 error for URL: {request.url}")
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Not found', 'path': request.path}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Initialize database
    init_database()

    # Run the application
    app.run(host='0.0.0.0', port=5000, debug=True)
import logging
import uuid
import json