import os
import logging
import uuid
import json
from datetime import datetime, timedelta
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
from models import Item, Sale, SaleItem, StockMovement, User, Setting, Customer, FinancialTransaction

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
                Journal, Supplier, PurchaseOrder, UserTwoFactor, Employee, InstallmentPlan
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
    """Get all inventory items with optional filtering"""
    try:
        from models import Item

        # Get current user ID
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify([])

        # Start query filtered by user only
        query = Item.query.filter(Item.user_id == current_user_id, Item.is_active == True)

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
        items = query.order_by(Item.name).all()
        items_data = []
        
        for item in items:
            item_dict = item.to_dict()
            # Ensure backward compatibility with frontend expecting 'quantity' field
            item_dict['quantity'] = item.stock_quantity
            item_dict['price'] = item.retail_price or 0
            items_data.append(item_dict)
            
        return jsonify(items_data)
        
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
            category=item_data.get("category", "Uncategorized"),
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

        # Update allowed fields only
        allowed_fields = [
            'name', 'description', 'sku', 'stock_quantity', 'minimum_stock',
            'buying_price', 'retail_price', 'wholesale_price', 'sales_type',
            'category', 'subcategory', 'unit_type', 'sell_by', 'is_active'
        ]

        # Validate and update fields
        for key, value in item_data.items():
            if key in allowed_fields:
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

@app.route('/api/reports/stock-status', methods=['GET'])
def stock_status_report():
    """API endpoint to get stock status report"""
    from models import Item
    from sqlalchemy import func

    low_stock_threshold = int(request.args.get('low_stock_threshold', 10))

    # Get counts and sums
    item_count = db.session.query(func.count(Item.id)).scalar() or 0
    total_stock = db.session.query(func.sum(Item.stock_quantity)).scalar() or 0

    # Get all items, low stock items, and out of stock items
    all_items = Item.query.all()
    low_stock_items = Item.query.filter(
        Item.stock_quantity <= low_stock_threshold).all()
    out_of_stock_items = Item.query.filter(Item.stock_quantity == 0).all()

    # Calculate inventory value using selling price retail with fallback to price
    total_value_query = db.session.query(
        func.sum(Item.stock_quantity * func.coalesce(Item.retail_price, 0))).scalar()
    total_value = float(
        total_value_query) if total_value_query is not None else 0

    report = {
        "total_items": item_count,
        "total_stock": total_stock,
        "average_stock_per_item":
        total_stock / item_count if item_count > 0 else 0,
        "low_stock_items_count": len(low_stock_items),
        "out_of_stock_items_count": len(out_of_stock_items),
        "all_items": [item.to_dict() for item in all_items],
        "low_stock_items": [item.to_dict() for item in low_stock_items],
        "out_of_stock_items": [item.to_dict() for item in out_of_stock_items],
        "total_inventory_value": total_value
    }

    return jsonify(report)

@app.route('/api/reports/category-breakdown', methods=['GET'])
@login_required
def category_breakdown_report():
    """API endpoint to get category breakdown report"""
    from models import Item
    from sqlalchemy import func

    # Get current user ID for filtering
    current_user_id = session.get('user_id')
    if not current_user_id:
        return jsonify({})

    # Group items by category
    categories = {}

    # First get all distinct categories for current user
    category_list = db.session.query(
        func.coalesce(Item.category,
                      'Uncategorized').label('category')).filter(
        Item.user_id == current_user_id).distinct().all()

    # For each category, get the stats
    for cat in category_list:
        category = cat.category

        # Get items count in this category
        count = db.session.query(func.count(Item.id)).filter(
            func.coalesce(Item.category, 'Uncategorized') == category,
            Item.user_id == current_user_id).scalar() or 0

        # Get total quantity
        total_quantity = db.session.query(func.sum(Item.stock_quantity)).filter(
            func.coalesce(Item.category, 'Uncategorized') == category,
            Item.user_id == current_user_id).scalar() or 0

        # Get total value based on retail selling price
        total_value_query = db.session.query(
            func.sum(Item.stock_quantity * Item.retail_price)).filter(
                func.coalesce(Item.category, 'Uncategorized') == category,
                Item.user_id == current_user_id).scalar()
        total_value = float(
            total_value_query) if total_value_query is not None else 0

        categories[category] = {
            "count": count,
            "total_quantity": total_quantity,
            "total_value": total_value
        }

    return jsonify(categories)

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """API endpoint to export inventory as CSV"""
    from models import Item

    output = io.StringIO()
    writer = csv.writer(output)

    # Write header row
    writer.writerow([
        'ID', 'SKU', 'Name', 'Description', 'Category', 'Quantity', 'Price',
        'Created At', 'Updated At'
    ])

    # Get all items
    items = Item.query.all()

    # Write data rows
    for item in items:
        writer.writerow([
            item.id, item.sku or '', item.name, item.description or '',
            item.category or 'Uncategorized', item.stock_quantity, item.price,
            item.created_at.isoformat() if item.created_at else '',
            item.updated_at.isoformat() if item.updated_at else ''
        ])

    # Create binary stream
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=
        f'inventory_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')

# On-Demand Products API endpoints
@app.route('/api/on-demand', methods=['GET'])
@login_required
def get_on_demand_products():
    """API endpoint to get all on-demand products"""
    from models import OnDemandProduct

    # Get current user ID
    current_user_id = session.get('user_id')
    if not current_user_id:
        return jsonify([])

    # Start query filtered by user
    query = OnDemandProduct.query.filter_by(user_id=current_user_id)

    # Optional filtering
    category = request.args.get('category')
    search_term = request.args.get('search', '').lower()
    active_only = request.args.get('active_only', 'false').lower() == 'true'

    # Apply filters if provided
    if category:
        query = query.filter(OnDemandProduct.category == category)

    if search_term:
        search_filter = (OnDemandProduct.name.ilike(f'%{search_term}%') |
                         OnDemandProduct.description.ilike(f'%{search_term}%')
                         | OnDemandProduct.materials.ilike(f'%{search_term}%'))
        query = query.filter(search_filter)

    if active_only:
        query = query.filter(OnDemandProduct.is_active == True)

    # Execute query and convert to dictionary
    products = [product.to_dict() for product in query.all()]
    return jsonify(products)

@app.route('/api/on-demand', methods=['POST'])
def add_on_demand_product():
    """API endpoint to add a new on-demand product"""
    from models import OnDemandProduct

    try:
        product_data = request.json

        # Validate required fields
        required_fields = ['name', 'base_price']
        for field in required_fields:
            if field not in product_data:
                return jsonify({"error":
                                f"Missing required field: {field}"}), 400

        # Get current user ID
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Create new product
        new_product = OnDemandProduct(
            name=product_data["name"],
            description=product_data.get("description", ""),
            base_price=float(product_data["base_price"]),
            production_time=int(product_data.get("production_time", 0)),
            category=product_data.get("category", "Uncategorized"),
            materials=product_data.get("materials", ""),
            is_active=product_data.get("is_active", True),
            user_id=current_user_id)

        # Add to database
        db.session.add(new_product)
        db.session.commit()

        return jsonify(new_product.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding on-demand product: {str(e)}")
        return jsonify({"error": "Failed to add on-demand product"}), 500

@app.route('/api/on-demand/<int:product_id>', methods=['GET'])
def get_on_demand_product(product_id):
    """API endpoint to get a specific on-demand product"""
    from models import OnDemandProduct

    product = OnDemandProduct.query.get(product_id)

    if not product:
        return jsonify({"error": "Product not found"}), 404

    return jsonify(product.to_dict())

@app.route('/api/on-demand/<int:product_id>', methods=['PUT'])
def update_on_demand_product(product_id):
    """API endpoint to update an on-demand product"""
    from models import OnDemandProduct

    try:
        product_data = request.json
        product = OnDemandProduct.query.get(product_id)

        if product is None:
            return jsonify({"error": "Product not found"}), 404

        # Update the product with new data
        for key, value in product_data.items():
            if key not in ['id',
                           'created_at']:  # Don't allow changing these fields
                setattr(product, key, value)

        # Save to database
        db.session.commit()

        return jsonify(product.to_dict())

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating on-demand product: {str(e)}")
        return jsonify({"error": "Failed to update on-demand product"}), 500

@app.route('/api/on-demand/<int:product_id>', methods=['DELETE'])
def delete_on_demand_product(product_id):
    """API endpoint to delete an on-demand product"""
    from models import OnDemandProduct

    try:
        product = OnDemandProduct.query.get(product_id)

        if product is None:
            return jsonify({"error": "Product not found"}), 404

        # Store product details before deletion
        product_dict = product.to_dict()
        product_name = product.name

        # Remove product from database
        db.session.delete(product)
        db.session.commit()

        return jsonify({
            "message": f"Deleted {product_name}",
            "product": product_dict
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting on-demand product: {str(e)}")
        return jsonify({"error": "Failed to delete on-demand product"}), 500

@app.route('/api/on-demand/categories', methods=['GET'])
def get_on_demand_product_categories():
    """API endpoint to get all unique on-demand product categories"""
    from models import OnDemandProduct
    from sqlalchemy import func

    # Query distinct categories
    categories = db.session.query(
        func.coalesce(OnDemandProduct.category,
                      'Uncategorized').label('category')).distinct().all()

    return jsonify([c.category for c in categories])

# Settings API endpoints
@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """API endpoint to get all settings or settings by category"""
    from models import Setting

    try:
        user_id = session.get('user_id')
        category = request.args.get('category')

        # Start query - filter by user
        query = Setting.query.filter_by(user_id=user_id)

        # Filter by category if provided
        if category:
            query = query.filter(Setting.category == category)

        # Execute query
        settings = [setting.to_dict() for setting in query.all()]

        # Group settings by category for easier UI rendering
        if not request.args.get('format') == 'flat':
            grouped_settings = {}
            for setting in settings:
                cat = setting['category']
                if cat not in grouped_settings:
                    grouped_settings[cat] = []
                grouped_settings[cat].append(setting)
            return jsonify(grouped_settings)

        return jsonify(settings)
        
    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/settings/<string:key>', methods=['GET'])
def get_setting(key):
    """API endpoint to get a specific setting"""
    from models import Setting

    setting = Setting.query.filter_by(key=key).first()

    if not setting:
        return jsonify({"error": "Setting not found"}), 404

    return jsonify(setting.to_dict())

@app.route('/api/settings/get/user_theme', methods=['GET'])
def get_user_theme():
    """API endpoint to get user's theme preference"""
    # First check if theme is in session
    if 'user_theme' in session:
        return jsonify({'success': True, 'value': session['user_theme']})

    # If not in session, try to get from database
    user_id = session.get('user_id')
    if user_id:
        from models import Setting

        theme_key = f"user_{user_id}_theme"
        setting = Setting.query.filter_by(key=theme_key).first()

        if setting:
            # Update session
            session['user_theme'] = setting.value
            return jsonify({'success': True, 'value': setting.value})

    # Return defaulttheme if not found
    return jsonify({
        'success': True,
        'value': 'tanzanite'  # Default theme
    })

@app.route('/api/settings', methods=['POST'])
def add_setting():
    """API endpoint to add or update a setting"""
    from models import Setting

    try:
        setting_data = request.json

        # Validate required fields
        if 'key' not in setting_data or 'value' not in setting_data:
            return jsonify({"error": "Both key and value are required"}), 400

        # Check if setting exists
        existing_setting = Setting.query.filter_by(
            key=setting_data['key']).first()

        if existing_setting:
            # Update existing setting
            existing_setting.value = setting_data['value']
            if 'description' in setting_data:
                existing_setting.description = setting_data['description']
            if 'category' in setting_data:
                existing_setting.category = setting_data['category']

            db.session.commit()
            return jsonify(existing_setting.to_dict())
        else:
            # Create new setting
            new_setting = Setting(
                key=setting_data['key'],
                value=setting_data['value'],
                description=setting_data.get('description', ''),
                category=setting_data.get('category', 'general'))

            db.session.add(new_setting)
            db.session.commit()

            return jsonify(new_setting.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding/updating setting: {str(e)}")
        return jsonify({"error": "Failed to add/update setting"}), 500

@app.route('/api/settings/<string:key>', methods=['PUT'])
def update_setting(key):
    """API endpoint to update a setting"""
    from models import Setting

    try:
        setting_data = request.json
        setting = Setting.query.filter_by(key=key).first()

        if setting is None:
            return jsonify({"error": "Setting not found"}), 404

        # Update setting
        if 'value' in setting_data:
            setting.value = setting_data['value']
        if 'description' in setting_data:
            setting.description = setting_data['description']
        if 'category' in setting_data:
            setting.category = setting_data['category']

        db.session.commit()

        return jsonify(setting.to_dict())

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating setting: {str(e)}")
        return jsonify({"error": "Failed to update setting"}), 500

@app.route('/api/settings/<string:key>', methods=['DELETE'])
def delete_setting(key):
    """API endpoint to delete a setting"""
    from models import Setting

    try:
        setting = Setting.query.filter_by(key=key).first()

        if setting is None:
            return jsonify({"error": "Setting not found"}), 404

        # Store setting details before deletion
        setting_dict = setting.to_dict()

        # Remove setting from database
        db.session.delete(setting)
        db.session.commit()

        return jsonify({
            "message": f"Deleted setting '{key}'",
            "setting": setting_dict
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting setting: {str(e)}")
        return jsonify({"error": "Failed to delete setting"}), 500

@app.route('/api/settings/appearance', methods=['POST'])
@login_required
def update_appearance_settings():
    """API endpoint to update appearance settings"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        from models import Setting
        
        # Update theme setting
        if 'theme' in data:
            theme_key = f"user_{user_id}_theme"
            theme_setting = Setting.query.filter_by(key=theme_key).first()
            
            if not theme_setting:
                theme_setting = Setting(
                    key=theme_key,
                    value=data['theme'],
                    description='User theme preference',
                    category='appearance'
                )
                db.session.add(theme_setting)
            else:
                theme_setting.value = data['theme']
            
            # Also update session
            session['user_theme'] = data['theme']
        
        # Update other appearance settings
        settings_to_update = [
            ('items_per_page', data.get('itemsPerPage')),
            ('date_format', data.get('dateFormat'))
        ]
        
        for key, value in settings_to_update:
            if value is not None:
                setting = Setting.query.filter_by(key=key).first()
                if not setting:
                    setting = Setting(
                        key=key,
                        value=str(value),
                        description=f'User {key} preference',
                        category='appearance'
                    )
                    db.session.add(setting)
                else:
                    setting.value = str(value)
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Appearance settings updated successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating appearance settings: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/logout')
def logout():
    """Logout route to clear session data"""
    # Clear session data
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))

@app.route('/account')
@login_required
def account():
    """User account management page"""
    return render_template('account.html')

# Financial Statement Routes
@app.route('/finance')
@login_required
def finance():
    """Render the financial statement page"""
    return render_template('finance.html')

# Installments Routes
@app.route('/installments')
@login_required
def installments():
    """Render the installments page"""
    return render_template('installments.html')

# Financial API Routes
@app.route('/api/finance/transactions', methods=['GET'])
@app.route('/api/transactions', methods=['GET'])
@login_required
def get_transactions():
    """API endpoint to get financial transactions with optional filtering"""
    from models import FinancialTransaction
    from datetime import datetime, timedelta

    # Get filter parameters
    transaction_type = request.args.get('type')
    category = request.args.get('category')
    start_date_str = request.args.get('start_date')
    end_date_str = request.args.get('end_date')

    # Parse dates if provided
    start_date = None
    end_date = None

    if start_date_str:
        try:
            start_date = datetime.strptime(start_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify(
                {"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400

    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify(
                {"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400

    # If no dates provided, default to current month
    if not start_date and not end_date:
        today = datetime.utcnow().date()
        start_date = datetime(today.year, today.month, 1).date()
        end_date = today
    elif start_date and not end_date:
        end_date = datetime.utcnow().date()
    elif not start_date and end_date:
        start_date = end_date - timedelta(days=30)

    # Get current user and filter transactions
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    # Build query with user filtering
    query = FinancialTransaction.query.filter(
        FinancialTransaction.user_id == user_id,
        FinancialTransaction.date >= start_date, 
        FinancialTransaction.date <= end_date)

    if transaction_type:
        query = query.filter(
            FinancialTransaction.transaction_type == transaction_type)

    if category:
        query = query.filter(FinancialTransaction.category == category)

    # Execute query and order by date (most recent first)
    transactions = query.order_by(FinancialTransaction.date.desc()).all()

    # Calculate totals
    total_income = sum(t.amount for t in transactions
                       if t.transaction_type == 'Income')
    total_expenses = sum(t.amount for t in transactions
                         if t.transaction_type == 'Expense')
    net_profit = total_income - total_expenses

    return jsonify({
        "transactions": [t.to_dict() for t in transactions],
        "period": {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat()
        },
        "summary": {
            "total_income": total_income,
            "total_expenses": total_expenses,
            "net_profit": net_profit
        }
    })

@app.route('/api/finance/transactions', methods=['POST'])
@app.route('/api/transactions', methods=['POST'])
@login_required
def add_transaction():
    """API endpoint to add a new financial transaction"""
    from models import FinancialTransaction
    
    # Get current user
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.json

    if not data:
        return jsonify({"error": "No data provided"}), 400

    required_fields = ['description', 'amount', 'transaction_type', 'category']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400

    # Validate transaction type
    if data['transaction_type'] not in ['Income', 'Expense']:
        return jsonify(
            {"error": "transaction_type must be 'Income' or 'Expense'"}), 400

    # Parse date if provided, otherwise use current date
    date = datetime.utcnow().date()
    if 'date' in data and data['date']:
        try:
            date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error":
                            "Invalid date format. Use YYYY-MM-DD"}), 400

    # Create new transaction
    transaction = FinancialTransaction(
        date=date,
        description=data['description'],
        amount=data['amount'],
        transaction_type=data['transaction_type'],
        category=data['category'],
        reference_id=data.get('reference_id'),
        payment_method=data.get('payment_method'),
        notes=data.get('notes'),
        user_id=user_id)

    try:
        db.session.add(transaction)
        db.session.commit()
        return jsonify(transaction.to_dict()), 201
    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Failed to add transaction: {str(e)}"}), 500

@app.route('/api/finance/transactions/<int:transaction_id>', methods=['GET'])
def get_transaction(transaction_id):
    """API endpoint to get a specific financial transaction"""
    from models import FinancialTransaction

    transaction = FinancialTransaction.query.get(transaction_id)
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404

    return jsonify(transaction.to_dict())

@app.route('/api/finance/transactions/<int:transaction_id>', methods=['PUT'])
@app.route('/api/transactions/<int:transaction_id>', methods=['PUT'])
@login_required
def update_transaction(transaction_id):
    """API endpoint to update a financial transaction"""
    from models import FinancialTransaction
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    transaction = FinancialTransaction.query.filter_by(id=transaction_id, user_id=user_id).first()
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404

    data = request.json
    if not data:
        return jsonify({"error": "No data provided"}), 400

    # Update fields
    if 'date' in data and data['date']:
        try:
            transaction.date = datetime.strptime(data['date'],
                                                 '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error":
                            "Invalid date format. Use YYYY-MM-DD"}), 400

    if 'description' in data:
        transaction.description = data['description']

    if 'amount' in data:
        transaction.amount = data['amount']

    if 'transaction_type' in data:
        if data['transaction_type'] not in ['Income', 'Expense']:
            return jsonify(
                {"error":
                 "transaction_type must be 'Income' or 'Expense'"}), 400
        transaction.transaction_type = data['transaction_type']

    if 'category' in data:
        transaction.category = data['category']

    if 'reference_id' in data:
        transaction.reference_id = data['reference_id']

    if 'payment_method' in data:
        transaction.payment_method = data['payment_method']

    if 'notes' in data:
        transaction.notes = data['notes']

    try:
        db.session.commit()
        return jsonify(transaction.to_dict())
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":
                        f"Failed to update transaction: {str(e)}"}), 500

@app.route('/api/finance/transactions/<int:transaction_id>',
           methods=['DELETE'])
def delete_transaction(transaction_id):
    """API endpoint to delete a financial transaction"""
    from models import FinancialTransaction

    try:
        transaction = FinancialTransaction.query.get(transaction_id)

        if transaction is None:
            return jsonify({"error": "Transaction not found"}), 404

        # Store transaction details before deletion
        transaction_dict = transaction.to_dict()
        transaction_description = transaction.description

        # Remove transaction from database
        db.session.delete(transaction)
        db.session.commit()

        return jsonify({
            "message": f"Deleted transaction: {transaction_description}",
            "transaction": transaction_dict
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting transaction: {str(e)}")
        return jsonify({"error": "Failed to delete transaction"}), 500

@app.route('/api/finance/categories', methods=['GET'])
def get_transaction_categories():
    from models import FinancialTransaction
    try:
        # Get distinct categories from existing transactions
        categories = db.session.query(FinancialTransaction.category).distinct().all()
        category_list = [cat[0] for cat in categories if cat[0]]

        # Default categories
        default_categories = {
            'income': ['Sales Revenue', 'Service Income', 'Interest Income', 'Other Income'],
            'expense': ['Rent', 'Utilities', 'Supplies', 'Marketing', 'Transportation', 'Equipment', 'Professional Services', 'Insurance', 'Other Expenses']
        }

        # Combine with existing categories
        all_categories = {
            'income': list(set(default_categories['income'] + [cat for cat in category_list if cat not in default_categories['expense']])),
            'expense': list(set(default_categories['expense'] + [cat for cat in category_list if cat not in default_categories['income']])),
            'custom': category_list
        }

        return jsonify(all_categories)
    except Exception as e:
        logger.error(f"Error getting categories: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/finance/categories', methods=['POST'])
def add_transaction_category():
    try:
        data = request.json
        category_name = data.get('name', '').strip()
        category_type = data.get('type', '').strip()

        if not category_name or not category_type:
            return jsonify({'error': 'Category name and type are required'}), 400

        if category_type not in ['Income', 'Expense']:
            return jsonify({'error': 'Category type must be Income or Expense'}), 400

        # Check if category already exists
        existing = FinancialTransaction.query.filter_by(category=category_name).first()
        if existing:
            return jsonify({'error': 'Category already exists'}), 400

        return jsonify({
            'success': True, 
            'message': 'Category can be used in transactions',
            'category': {'name': category_name, 'type': category_type}
        })
    except Exception as e:
        logger.error(f"Error adding category: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/finance/summaries/monthly', methods=['GET'])
@login_required
def get_monthly_summaries():
    """API endpoint to get monthly financial summaries for charts"""
    try:
        from models import FinancialTransaction
        from sqlalchemy import extract, func
        from datetime import datetime

        year = request.args.get('year', datetime.now().year)

        try:
            year = int(year)
        except ValueError:
            return jsonify({'error': 'Invalid year format'}), 400

        # Get current user for filtering
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        # Query monthly summaries
        monthly_data = []
        months = [
            'January', 'February', 'March', 'April', 'May', 'June',
            'July', 'August', 'September', 'October', 'November', 'December'
        ]

        for month_num in range(1, 13):
            # Get income for this month
            income = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                extract('year', FinancialTransaction.date) == year,
                extract('month', FinancialTransaction.date) == month_num,
                FinancialTransaction.transaction_type == 'Income',
                FinancialTransaction.user_id == user_id
            ).scalar() or 0

            # Get expenses for this month
            expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                extract('year', FinancialTransaction.date) == year,
                extract('month', FinancialTransaction.date) == month_num,
                FinancialTransaction.transaction_type == 'Expense',
                FinancialTransaction.user_id == user_id
            ).scalar() or 0

            monthly_data.append({                'month': month_num,
                'month_name': months[month_num - 1],
                'income': float(income),
                'expenses': float(expenses),
                'profit': float(income - expenses)
            })

        return jsonify({
            'year': year,
            'monthly_data': monthly_data
        })

    except Exception as e:
        logger.error(f"Error getting monthly summaries: {e}")
        return jsonify({'error': str(e)}), 500

# Additional imports for enhanced functionality
import uuid
from werkzeug.utils import secure_filename
from datetime import date
from services.predictive_analytics import PredictiveAnalyticsService
from services.smart_inventory import SmartInventoryService
from services.business_intelligence import BusinessIntelligenceService
from services.supply_chain_service import SupplyChainService
from services.localization_service import LocalizationService
from services.marketing_service import MarketingService

# ===== CATEGORIES API ROUTES =====

@app.route('/api/categories/<int:category_id>/subcategories', methods=['POST'])
@login_required
def add_subcategory(category_id):
    """API endpoint to add a subcategory to a given category."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401

    data = request.get_json()
    name = data.get('name')
    description = data.get('description', '')

    if not name:
        return jsonify({'error': 'Subcategory name is required'}), 400

    try:
        from models import Category
        
        # Check if parent category exists and belongs to the current user
        parent_category = Category.query.filter_by(
            id=category_id, 
            user_id=user_id, 
            is_active=True
        ).first()
        
        if not parent_category:
            return jsonify({'error': 'Parent category does not exist or access denied'}), 404

        # Check if subcategory with same name already exists under this parent
        existing_subcategory = Category.query.filter_by(
            name=name,
            parent_id=category_id,
            user_id=user_id,
            is_active=True
        ).first()
        
        if existing_subcategory:
            return jsonify({'error': 'Subcategory with this name already exists'}), 400

        # Create the subcategory
        new_subcategory = Category(
            name=name,
            description=description,
            parent_id=parent_category.id,
            user_id=user_id,  # Set the user_id
            sort_order=0,  # Default sort order
            is_active=True
        )
        
        db.session.add(new_subcategory)
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'subcategory': {
                'id': new_subcategory.id,
                'name': new_subcategory.name,
                'description': new_subcategory.description,
                'parent_id': new_subcategory.parent_id,
                'user_id': new_subcategory.user_id,
                'is_active': new_subcategory.is_active,
                'created_at': new_subcategory.created_at.isoformat() if new_subcategory.created_at else None
            }
        }), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating subcategory: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
def update_category_api(category_id):
    """Update a category"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        from models import Category

        # Get category and verify ownership
        category = Category.query.filter_by(
            id=category_id, 
            user_id=user_id, 
            is_active=True
        ).first()
        
        if not category:
            return jsonify({'error': 'Category not found'}), 404

        # Update fields
        if 'name' in data:
            category.name = data['name'].strip()
        if 'description' in data:
            category.description = data['description'].strip()
        if 'sort_order' in data:
            category.sort_order = int(data['sort_order'])
        
        category.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'category': category.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating category: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category_api(category_id):
    """Delete a category"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        from models import Category

        # Get category and verify ownership
        category = Category.query.filter_by(
            id=category_id, 
            user_id=user_id, 
            is_active=True
        ).first()
        
        if not category:
            return jsonify({'error': 'Category not found'}), 404

        # Check if category has subcategories
        subcategories = Category.query.filter_by(
            parent_id=category_id,
            user_id=user_id,
            is_active=True
        ).count()
        
        if subcategories > 0:
            return jsonify({'error': 'Cannot delete category with subcategories'}), 400

        # Soft delete - mark as inactive
        category.is_active = False
        category.updated_at = datetime.utcnow()
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Category "{category.name}" deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting category: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories_api():
    """Get all categories for current user"""
    try:
        from models import Category
        user_id = session.get('user_id')
        
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Get all active categories for the user
        categories = Category.query.filter_by(
            user_id=user_id, 
            is_active=True
        ).order_by(Category.sort_order, Category.name).all()
        
        if not categories:
            # Return empty array instead of error to allow frontend to handle gracefully
            return jsonify([])
        
        # Separate parent and child categories
        parent_categories = [cat for cat in categories if not cat.parent_id]
        child_categories = [cat for cat in categories if cat.parent_id]
        
        # Build categories with subcategories and item counts
        categories_data = []
        for parent in parent_categories:
            subcategories = [child for child in child_categories if child.parent_id == parent.id]
            
            category_dict = {
                'id': parent.id,
                'name': parent.name,
                'description': parent.description or '',
                'parent_id': parent.parent_id,
                'sort_order': parent.sort_order,
                'is_active': parent.is_active,
                'user_id': parent.user_id,
                'item_count': parent.get_item_count(),
                'total_item_count': parent.get_total_item_count(),
                'category_path': parent.get_category_path(),
                'created_at': parent.created_at.isoformat() if parent.created_at else None,
                'subcategories': [
                    {
                        'id': sub.id,
                        'name': sub.name,
                        'description': sub.description or '',
                        'parent_id': sub.parent_id,
                        'sort_order': sub.sort_order,
                        'is_active': sub.is_active,
                        'user_id': sub.user_id,
                        'item_count': sub.get_item_count(),
                        'total_item_count': sub.get_total_item_count(),
                        'category_path': sub.get_category_path(),
                        'created_at': sub.created_at.isoformat() if sub.created_at else None
                    }
                    for sub in sorted(subcategories, key=lambda x: (x.sort_order, x.name))
                ]
            }
            categories_data.append(category_dict)
        
        # Add any orphaned subcategories (subcategories without valid parents)
        orphaned_subs = [child for child in child_categories 
                        if not any(parent.id == child.parent_id for parent in parent_categories)]
        
        for orphaned in orphaned_subs:
            category_dict = {
                'id': orphaned.id,
                'name': orphaned.name,
                'description': orphaned.description or '',
                'parent_id': orphaned.parent_id,
                'sort_order': orphaned.sort_order,
                'is_active': orphaned.is_active,
                'user_id': orphaned.user_id,
                'created_at': orphaned.created_at.isoformat() if orphaned.created_at else None,
                'subcategories': []
            }
            categories_data.append(category_dict)
        
        return jsonify(categories_data)
        
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        db.session.rollback()
        return jsonify({'error': f'Failed to load categories: {str(e)}'}), 500

@app.route('/api/categories', methods=['POST'])
@login_required
def create_category_api():
    """Create a new category"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        # Validate required fields
        if not data.get('name'):
            return jsonify({'error': 'Category name is required'}), 400
        
        category_name = data['name'].strip()
        if not category_name:
            return jsonify({'error': 'Category name cannot be empty'}), 400

        from models import Category

        # Check if category name already exists for this user (case-insensitive)
        existing_category = Category.query.filter(
            func.lower(Category.name) == func.lower(category_name),
            Category.user_id == user_id,
            Category.parent_id == data.get('parent_id'),
            Category.is_active == True
        ).first()
        
        if existing_category:
            return jsonify({
                'success': False,
                'error': f'Category "{category_name}" already exists. Please choose a different name.'
            }), 400

        # Validate parent category if specified
        parent_id = data.get('parent_id')
        if parent_id:
            parent_category = Category.query.filter_by(
                id=parent_id,
                user_id=user_id,
                is_active=True
            ).first()
            if not parent_category:
                return jsonify({'error': 'Invalid parent category'}), 400

        # Create new category
        category = Category(
            name=category_name,
            description=data.get('description', '').strip(),
            parent_id=parent_id,
            sort_order=int(data.get('sort_order', 0)),
            user_id=user_id,
            is_active=True,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow()
        )

        db.session.add(category)
        db.session.commit()
        
        logger.info(f"Category created: {category.name} (ID: {category.id}) by user {user_id}")

        return jsonify({
            'success': True, 
            'category_id': category.id,
            'category': category.to_dict()
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating category: {str(e)}")
        return jsonify({'error': f'Failed to create category: {str(e)}'}), 500

# ===== ACCOUNTING API ROUTES =====

@app.route('/api/accounting/chart-of-accounts', methods=['GET'])
@login_required
def get_chart_of_accounts_api():
    """Get chart of accounts"""
    try:
        user_id = session.get('user_id')
        from models import ChartOfAccounts

        accounts = ChartOfAccounts.query.filter_by(user_id=user_id, is_active=True).order_by(ChartOfAccounts.account_code).all()

        accounts_data = []
        for account in accounts:
            accounts_data.append({
                'id': account.id,
                'account_code': account.account_code,
                'account_name': account.account_name,
                'account_type': account.account_type,
                'parent_account_id': account.parent_account_id,
                'balance': float(account.balance) if account.balance else 0.0,
                'is_active': account.is_active
            })

        return jsonify({'success': True, 'accounts': accounts_data})
    except Exception as e:
        logger.error(f"Error getting chart of accounts: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounting/initialize', methods=['POST'])
@login_required
def initialize_accounting():
    """Initialize chart of accounts"""
    try:
        from accounting_service import AccountingService
        user_id = session.get('user_id')
        
        success = AccountingService.initialize_chart_of_accounts(user_id)
        
        if success:
            return jsonify({'success': True, 'message': 'Chart of accounts initialized successfully'})
        else:
            return jsonify({'error': 'Failed to initialize chart of accounts'}), 500
            
    except Exception as e:
        logger.error(f"Error initializing accounting: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounting/journal-entries', methods=['GET'])
@login_required
def get_journal_entries_api():
    """Get journal entries"""
    try:
        user_id = session.get('user_id')
        from models import Journal

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)

        journals = Journal.query.filter_by(user_id=user_id).order_by(Journal.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )

        journals_data = []
        for journal in journals.items:
            journals_data.append({
                'id': journal.id,
                'journal_number': journal.journal_number,
                'description': journal.description,
                'total_debit': float(journal.total_debit) if journal.total_debit else 0.0,
                'total_credit': float(journal.total_credit) if journal.total_credit else 0.0,
                'created_at': journal.created_at.isoformat() if journal.created_at else None
            })

        return jsonify({
            'success': True,
            'journals': journals_data,
            'pagination': {
                'page': page,
                'pages': journals.pages,
                'per_page': per_page,
                'total': journals.total
            }
        })
    except Exception as e:
        logger.error(f"Error getting journal entries: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounting/balance-sheet', methods=['GET'])
@login_required
def get_balance_sheet_api():
    """Get balance sheet data"""
    try:
        user_id = session.get('user_id')
        as_of_date = request.args.get('as_of_date', datetime.now().strftime('%Y-%m-%d'))

        # Mock balance sheet data for now
        balance_sheet_data = {
            'as_of_date': as_of_date,
            'assets': {
                'current_assets': {
                    'cash': 50000.0,
                    'accounts_receivable': 25000.0,
                    'inventory': 75000.0,
                    'total': 150000.0
                },
                'fixed_assets': {
                    'equipment': 100000.0,
                    'accumulated_depreciation': -20000.0,
                    'total': 80000.0
                },
                'total_assets': 230000.0
            },
            'liabilities': {
                'current_liabilities': {
                    'accounts_payable': 30000.0,
                    'short_term_debt': 20000.0,
                    'total': 50000.0
                },
                'long_term_liabilities': {
                    'long_term_debt': 80000.0,
                    'total': 80000.0
                },
                'total_liabilities': 130000.0
            },
            'equity': {
                'owners_equity': 100000.0,
                'total_equity': 100000.0
            }
        }

        return jsonify({'success': True, 'balance_sheet': balance_sheet_data})
    except Exception as e:
        logger.error(f"Error getting balance sheet: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/accounting/trial-balance', methods=['GET'])
@login_required
def get_trial_balance_api():
    """Get trial balance data"""
    try:
        user_id = session.get('user_id')
        as_of_date = request.args.get('as_of_date', datetime.now().strftime('%Y-%m-%d'))

        # Mock trial balance data
        trial_balance_data = {
            'as_of_date': as_of_date,
            'accounts': [
                {'account_name': 'Cash', 'debit': 50000.0, 'credit': 0.0},
                {'account_name': 'Accounts Receivable', 'debit': 25000.0, 'credit': 0.0},
                {'account_name': 'Inventory', 'debit': 75000.0, 'credit': 0.0},
                {'account_name': 'Equipment', 'debit': 100000.0, 'credit': 0.0},
                {'account_name': 'Accounts Payable', 'debit': 0.0, 'credit': 30000.0},
                {'account_name': 'Long-term Debt', 'debit': 0.0, 'credit': 80000.0},
                {'account_name': 'Owners Equity', 'debit': 0.0, 'credit': 100000.0},
                {'account_name': 'Sales Revenue', 'debit': 0.0, 'credit': 40000.0}
            ],
            'total_debits': 250000.0,
            'total_credits': 250000.0,
            'is_balanced': True
        }

        return jsonify({'success': True, 'trial_balance': trial_balance_data})
    except Exception as e:
        logger.error(f"Error getting trial balance: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===== INSTALLMENTS API ROUTES =====

@app.route('/api/installment-sales/dashboard', methods=['GET'])
@login_required
def get_installment_dashboard():
    """Get installment sales dashboard data"""
    try:
        from models import InstallmentSale, InstallmentPayment
        from sqlalchemy import func, and_
        from datetime import date, timedelta
        
        user_id = session.get('user_id')
        
        # Get counts by status
        total_active = InstallmentSale.query.filter_by(user_id=user_id, status='Active').count()
        total_completed = InstallmentSale.query.filter_by(user_id=user_id, status='Completed').count()
        total_overdue = InstallmentSale.query.filter_by(user_id=user_id, status='Overdue').count()
        
        # Calculate outstanding balance
        outstanding_balance = db.session.query(func.sum(InstallmentSale.remaining_amount)).filter(
            InstallmentSale.user_id == user_id,
            InstallmentSale.status.in_(['Active', 'Overdue'])
        ).scalar() or 0
        
        # Get upcoming payments (next 30 days)
        today = date.today()
        next_month = today + timedelta(days=30)
        
        upcoming_payments = db.session.query(
            InstallmentPayment.installment_sale_id,
            InstallmentPayment.amount_due,
            InstallmentPayment.due_date,
            InstallmentSale.customer_name,
            InstallmentSale.item_name
        ).join(InstallmentSale).filter(
            InstallmentSale.user_id == user_id,
            InstallmentPayment.status == 'Pending',
            InstallmentPayment.due_date.between(today, next_month)
        ).order_by(InstallmentPayment.due_date).limit(10).all()
        
        upcoming_payments_list = [
            {
                'installment_sale_id': payment.installment_sale_id,
                'customer_name': payment.customer_name,
                'item_name': payment.item_name,
                'amount_due': float(payment.amount_due),
                'due_date': payment.due_date.isoformat()
            }
            for payment in upcoming_payments
        ]
        
        dashboard_data = {
            'summary': {
                'total_active': total_active,
                'total_completed': total_completed,
                'total_overdue': total_overdue,
                'outstanding_balance': float(outstanding_balance)
            },
            'upcoming_payments': upcoming_payments_list
        }

        return jsonify(dashboard_data)
    except Exception as e:
        logger.error(f"Error getting installment dashboard: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/installment-sales', methods=['GET'])
@login_required
def get_installment_sales():
    """Get installment sales with filtering"""
    try:
        from models import InstallmentSale
        
        user_id = session.get('user_id')
        
        # Get filter parameters
        status = request.args.get('status')
        customer_id = request.args.get('customer_id')
        
        # Build query
        query = InstallmentSale.query.filter_by(user_id=user_id)
        
        if status:
            query = query.filter(InstallmentSale.status == status)
        if customer_id:
            query = query.filter(InstallmentSale.customer_id == customer_id)
        
        # Execute query
        installment_sales = query.order_by(InstallmentSale.created_at.desc()).all()
        
        return jsonify([sale.to_dict() for sale in installment_sales])
    except Exception as e:
        logger.error(f"Error getting installment sales: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/installment-sales', methods=['POST'])
@login_required
def create_installment_sale():
    """Create new installment sale"""
    try:
        from models import InstallmentSale, InstallmentPayment, Sale, SaleItem, Customer, Item
        from datetime import date, timedelta
        import uuid
        
        user_id = session.get('user_id')
        data = request.get_json()
        
        # Validate required fields
        required_fields = ['customer_id', 'item_id', 'quantity', 'total_amount', 'down_payment', 'number_of_installments']
        for field in required_fields:
            if field not in data:
                return jsonify({'error': f'Missing required field: {field}'}), 400
        
        # Create customer if new customer data provided
        if data.get('customer_data') and not data.get('customer_id'):
            customer = Customer(
                name=data['customer_data']['name'],
                phone=data['customer_data']['phone'],
                email=data['customer_data'].get('email'),
                address=data['customer_data'].get('address'),
                user_id=user_id
            )
            db.session.add(customer)
            db.session.flush()
            customer_id = customer.id
        else:
            customer_id = data['customer_id']
        
        # Get customer and item
        customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first()
        item = Item.query.filter_by(id=data['item_id'], user_id=user_id).first()
        
        if not customer or not item:
            return jsonify({'error': 'Customer or item not found'}), 404
        
        # Calculate installment details
        total_amount = float(data['total_amount'])
        down_payment = float(data['down_payment'])
        remaining_amount = total_amount - down_payment
        number_of_installments = int(data['number_of_installments'])
        monthly_payment = remaining_amount / number_of_installments
        
        # Create sale record first
        sale_number = f"INST-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        sale = Sale(
            invoice_number=f"INV-{sale_number}",
            sale_number=sale_number,
            customer_name=customer.name,
            customer_phone=customer.phone,
            customer_id=customer_id,
            sale_type='retail',
            subtotal=total_amount,
            total_amount=total_amount,
            payment_method='installment',
            payment_status='partial',
            payment_amount=down_payment,
            is_installment=True,
            down_payment=down_payment,
            installment_months=number_of_installments,
            monthly_payment=monthly_payment,
            user_id=user_id
        )
        db.session.add(sale)
        db.session.flush()
        
        # Create sale item
        sale_item = SaleItem(
            sale_id=sale.id,
            item_id=data['item_id'],
            quantity=data['quantity'],
            unit_price=total_amount / data['quantity'],
            total_price=total_amount
        )
        db.session.add(sale_item)
        
        # Create installment sale record
        installment_sale = InstallmentSale(
            sale_id=sale.id,
            customer_id=customer_id,
            item_id=data['item_id'],
            quantity=data['quantity'],
            total_amount=total_amount,
            down_payment=down_payment,
            remaining_amount=remaining_amount,
            number_of_installments=number_of_installments,
            monthly_payment=monthly_payment,
            start_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date(),
            next_due_date=datetime.strptime(data['start_date'], '%Y-%m-%d').date() + timedelta(days=30),
            agreement_signed=data.get('agreement_signed', False),
            notes=data.get('notes', ''),
            total_paid=down_payment,
            user_id=user_id
        )
        db.session.add(installment_sale)
        db.session.flush()
        
        # Create payment schedule
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        
        for i in range(1, number_of_installments + 1):
            due_date = start_date + timedelta(days=30 * i)
            
            payment = InstallmentPayment(
                installment_sale_id=installment_sale.id,
                installment_number=i,
                amount_due=monthly_payment,
                due_date=due_date,
                user_id=user_id
            )
            db.session.add(payment)
        
        # Update item stock
        item.stock_quantity -= data['quantity']
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'installment_sale_id': installment_sale.id,
            'sale_number': sale_number
        }), 201
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating installment sale: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/installment-sales/<int:sale_id>/payments', methods=['GET'])
@login_required
def get_installment_payments(sale_id):
    """Get payment schedule for an installment sale"""
    try:
        from models import InstallmentSale, InstallmentPayment
        
        user_id = session.get('user_id')
        
        # Get installment sale
        installment_sale = InstallmentSale.query.filter_by(
            id=sale_id, user_id=user_id
        ).first()
        
        if not installment_sale:
            return jsonify({'error': 'Installment sale not found'}), 404
        
        # Get payment schedule
        payments = InstallmentPayment.query.filter_by(
            installment_sale_id=sale_id
        ).order_by(InstallmentPayment.installment_number).all()
        
        return jsonify({
            'installment_sale': installment_sale.to_dict(),
            'payment_schedule': [payment.to_dict() for payment in payments]
        })
        
    except Exception as e:
        logger.error(f"Error getting installment payments: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/installment-sales/<int:sale_id>/payments', methods=['POST'])
@login_required
def record_installment_payment():
    """Record a payment for an installment sale"""
    try:
        from models import InstallmentSale, InstallmentPayment
        from datetime import date
        
        user_id = session.get('user_id')
        data = request.get_json()
        
        # Get installment sale
        installment_sale = InstallmentSale.query.filter_by(
            id=sale_id, user_id=user_id
        ).first()
        
        if not installment_sale:
            return jsonify({'error': 'Installment sale not found'}), 404
        
        # Get the specific payment
        payment = InstallmentPayment.query.filter_by(
            installment_sale_id=sale_id,
            installment_number=data['installment_number']
        ).first()
        
        if not payment:
            return jsonify({'error': 'Payment record not found'}), 404
        
        # Update payment
        payment.amount_paid = data['amount_paid']
        payment.payment_date = datetime.strptime(data['payment_date'], '%Y-%m-%d').date()
        payment.payment_method = data.get('payment_method', 'cash')
        payment.status = 'Paid' if payment.amount_paid >= payment.amount_due else 'Partial'
        payment.remarks = data.get('remarks', '')
        payment.updated_at = datetime.utcnow()
        
        # Update installment sale
        installment_sale.total_paid += data['amount_paid']
        installment_sale.payments_made += 1
        
        # Update next due date and status
        if installment_sale.payments_made >= installment_sale.number_of_installments:
            installment_sale.status = 'Completed'
            installment_sale.next_due_date = None
        else:
            next_payment = InstallmentPayment.query.filter_by(
                installment_sale_id=sale_id,
                status='Pending'
            ).order_by(InstallmentPayment.installment_number).first()
            
            if next_payment:
                installment_sale.next_due_date = next_payment.due_date
        
        installment_sale.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Payment recorded successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error recording payment: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===== CUSTOMERS API ROUTES =====

@app.route('/api/customers', methods=['GET'])
@login_required
def get_customers_api():
    """Get all customers for current user"""
    try:
        user_id = session.get('user_id')
        from models import Customer

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
                'credit_limit': float(customer.credit_limit) if customer.credit_limit else 0.0,
                'loyalty_points': customer.loyalty_points,
                'preferred_payment_method': customer.preferred_payment_method,
                'created_at': customer.created_at.isoformat() if customer.created_at else None
            })

        return jsonify({'success': True, 'customers': customers_data})
    except Exception as e:
        logger.error(f"Error getting customers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers', methods=['POST'])
@login_required
def create_customer_api():
    """Create a new customer"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')

        from models import Customer, db

        customer = Customer(
            name=data['name'],
            email=data.get('email'),
            phone=data.get('phone'),
            address=data.get('address'),
            customer_type=data.get('customer_type', 'retail'),
            credit_limit=data.get('credit_limit', 0.0),
            preferred_payment_method=data.get('preferred_payment_method'),
            user_id=user_id
        )

        db.session.add(customer)
        db.session.commit()

        return jsonify({'success': True, 'customer_id': customer.id}), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating customer: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers/<int:customer_id>', methods=['PUT'])
@login_required
def update_customer_api(customer_id):
    """Update an existing customer"""
    try:
        from models import Customer
        
        user_id = session.get('user_id')
        customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first()
        
        if not customer:
            return jsonify({'error': 'Customer not found'}), 404
        
        data = request.get_json()
        
        # Update fields
        if 'name' in data:
            customer.name = data['name']
        if 'email' in data:
            customer.email = data['email']
        if 'phone' in data:
            customer.phone = data['phone']
        if 'address' in data:
            customer.address = data['address']
        if 'customer_type' in data:
            customer.customer_type = data['customer_type']
        if 'credit_limit' in data:
            customer.credit_limit = float(data['credit_limit'])
        if 'preferred_payment_method' in data:
            customer.preferred_payment_method = data['preferred_payment_method']
        
        customer.updated_at = datetime.utcnow()
        
        db.session.commit()
        
        return jsonify(customer.to_dict())
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating customer: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===== PREDICTIVE ANALYTICS API ROUTES =====

@app.route('/api/analytics/demand-forecast', methods=['GET'])
def demand_forecast():
    """Get demand forecast for items"""
    try:
        user_id = session.get('user_id')
        item_id = request.args.get('item_id', type=int)
        days_ahead = request.args.get('days_ahead', default=30, type=int)

        analytics_service = PredictiveAnalyticsService(user_id)
        result = analytics_service.demand_forecasting(item_id, days_ahead)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in demand forecast: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/seasonal-trends', methods=['GET'])
def seasonal_trends():
    """Get seasonal trend analysis"""
    try:
        user_id = session.get('user_id')
        item_id = request.args.get('item_id', type=int)

        analytics_service = PredictiveAnalyticsService(user_id)
        result = analytics_service.seasonal_trend_analysis(item_id)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in seasonal trends: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/price-optimization', methods=['GET'])
def price_optimization():
    """Get price optimization recommendations"""
    try:
        user_id = session.get('user_id')
        item_id = request.args.get('item_id', type=int)

        analytics_service = PredictiveAnalyticsService(user_id)
        result = analytics_service.price_optimization_recommendations(item_id)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in price optimization: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/analytics/customer-behavior', methods=['GET'])
def customer_behavior():
    """Get customer behavior analytics"""
    try:
        user_id = session.get('user_id')

        analytics_service = PredictiveAnalyticsService(user_id)
        result = analytics_service.customer_behavior_analytics()

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in customer behavior analytics: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ===== SMART INVENTORY API ROUTES =====

@app.route('/api/smart-inventory/auto-reorder', methods=['GET', 'POST'])
def auto_reorder():
    """Auto reorder system"""
    try:
        user_id = session.get('user_id')
        supplier_integration = request.args.get('supplier_integration', 'false').lower() == 'true'

        smart_inventory = SmartInventoryService(user_id)
        result = smart_inventory.auto_reorder_system(supplier_integration)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in auto reorder: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/smart-inventory/dynamic-pricing', methods=['GET'])
def dynamic_pricing():
    """Dynamic pricing engine"""
    try:
        user_id = session.get('user_id')
        market_data = request.json if request.method == 'POST' else None

        smart_inventory = SmartInventoryService(user_id)
        result = smart_inventory.dynamic_pricing_engine(market_data)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in dynamic pricing: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/smart-inventory/expiry-tracking', methods=['GET'])
def expiry_tracking():
    """Expiry date tracking for perishable goods"""
    try:
        user_id = session.get('user_id')

        smart_inventory = SmartInventoryService(user_id)
        result = smart_inventory.expiry_date_tracking()

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in expiry tracking: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/smart-inventory/abc-analysis', methods=['GET'])
def abc_analysis():
    """ABC analysis for inventory categorization"""
    try:
        user_id = session.get('user_id')

        smart_inventory = SmartInventoryService(user_id)
        result = smart_inventory.abc_analysis()

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error in ABC analysis: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/smart-inventory/health-score', methods=['GET'])
def inventory_health_score():
    """Get inventory health score"""
    try:
        user_id = session.get('user_id')

        smart_inventory = SmartInventoryService(user_id)
        result = smart_inventory.inventory_health_score()

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error calculating health score: {str(e)}")
        return jsonify({"error": str(e)}), 500

# ===== LOCALIZATION API ROUTES =====

@app.route('/api/localization/language', methods=['GET', 'POST'])
def manage_language():
    """Get or set user language preference"""
    localization = LocalizationService()

    if request.method == 'GET':
        return jsonify({
            'current_language': localization.get_user_language(),
            'supported_languages': localization.supported_languages
        })
    else:
        data = request.get_json()
        language = data.get('language')

        if localization.set_user_language(language):
            return jsonify({'success': True, 'language': language})
        else:
            return jsonify({'error': 'Unsupported language'}), 400

@app.route('/api/localization/currency/<amount>')
def format_currency(amount):
    """Format currency amount according to local preferences"""
    try:
        localization = LocalizationService()
        currency = request.args.get('currency', 'TZS')
        formatted = localization.format_currency(float(amount), currency)
        return jsonify({'formatted_amount': formatted})
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@app.route('/api/localization/tax/vat', methods=['POST'])
def calculate_vat():
    """Calculate VAT for Tanzania"""
    try:
        data = request.get_json()
        amount = data.get('amount')
        include_vat = data.get('include_vat', True)

        localization = LocalizationService()
        result = localization.calculate_vat(amount, include_vat)

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 400

# ===== PAYMENT GATEWAY API ROUTES =====

@app.route('/api/payments/mpesa/initiate', methods=['POST'])
def initiate_mpesa_payment():
    """Initiate M-Pesa STK Push payment"""
    try:
        data = request.get_json()
        payment_service = PaymentService()

        result = payment_service.initiate_mpesa_payment(
            phone_number=data['phone_number'],
            amount=data['amount'],
            reference=data['reference'],
            description=data['description']
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/payments/mpesa/status/<checkout_request_id>')
def check_mpesa_status(checkout_request_id):
    """Check M-Pesa payment status"""
    try:
        payment_service = PaymentService()
        result = payment_service.check_mpesa_payment_status(checkout_request_id)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/payments/mobile-money', methods=['POST'])
def process_mobile_money():
    """Process mobile money payments"""
    try:
        data = request.get_json()
        payment_service = PaymentService()

        result = payment_service.process_mobile_money_payment(
            provider=data['provider'],
            phone_number=data['phone_number'],
            amount=data['amount'],
            reference=data['reference']
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/payments/crypto', methods=['POST'])
def process_crypto_payment():
    """Process cryptocurrency payments"""
    try:
        data = request.get_json()
        payment_service = PaymentService()

        result = payment_service.process_cryptocurrency_payment(
            currency=data['currency'],
            amount=data['amount'],
            wallet_address=data['wallet_address']
        )

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/payments/split', methods=['POST'])
def process_split_payment():
    """Process split payments across multiple methods"""
    try:
        data = request.get_json()
        payment_service = PaymentService()

        result = payment_service.process_split_payment(data['payment_methods'])

        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== SUPPLY CHAIN API ROUTES =====

@app.route('/api/supply-chain/suppliers', methods=['GET', 'POST'])
@login_required
def manage_suppliers():
    """Get or create suppliers"""
    try:
        user_id = session.get('user_id')

        if request.method == 'GET':
            from models import Supplier
            suppliers = Supplier.query.filter_by(user_id=user_id, is_active=True).all()
            return jsonify({
                'success': True,
                'suppliers': [s.to_dict() for s in suppliers]
            })
        else:
            from models import Supplier
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['name']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Create supplier
            supplier = Supplier(
                name=data['name'],
                contact_person=data.get('contact_person'),
                email=data.get('email'),
                phone=data.get('phone'),
                address=data.get('address'),
                payment_terms=data.get('payment_terms'),
                user_id=user_id
            )
            
            db.session.add(supplier)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'supplier': supplier.to_dict()
            }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error managing suppliers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/supply-chain/suppliers/<int:supplier_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_supplier(supplier_id):
    """Get, update, or delete a specific supplier"""
    try:
        user_id = session.get('user_id')
        supplier = Supplier.query.filter_by(id=supplier_id, user_id=user_id).first()
        
        if not supplier:
            return jsonify({'error': 'Supplier not found'}), 404
        
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'supplier': supplier.to_dict()
            })
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Update fields
            updatable_fields = ['name', 'contact_person', 'email', 'phone', 'address', 'payment_terms']
            for field in updatable_fields:
                if field in data:
                    setattr(supplier, field, data[field])
            
            supplier.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'supplier': supplier.to_dict()
            })
        
        elif request.method == 'DELETE':
            supplier.is_active = False
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Supplier {supplier.name} deleted successfully'
            })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error managing supplier: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/supply-chain/purchase-orders', methods=['GET', 'POST'])
@login_required
def manage_purchase_orders():
    """Get or create purchase orders"""
    try:
        user_id = session.get('user_id')

        if request.method == 'GET':
            from models import PurchaseOrder
            pos = PurchaseOrder.query.filter_by(user_id=user_id).order_by(PurchaseOrder.created_at.desc()).all()
            return jsonify({
                'success': True,
                'purchase_orders': [po.to_dict() for po in pos]
            })
        else:
            data = request.get_json()
            
            # Validate required fields
            required_fields = ['supplier_id', 'order_date', 'total_amount']
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            
            # Generate PO number
            po_number = f"PO-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
            
            # Create purchase order
            po = PurchaseOrder(
                po_number=po_number,
                supplier_id=data['supplier_id'],
                total_amount=float(data['total_amount']),
                order_date=datetime.strptime(data['order_date'], '%Y-%m-%d').date(),
                expected_date=datetime.strptime(data['expected_date'], '%Y-%m-%d').date() if data.get('expected_date') else None,
                status=data.get('status', 'pending'),
                user_id=user_id
            )
            
            db.session.add(po)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'purchase_order': po.to_dict()
            }), 201
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error managing purchase orders: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/supply-chain/purchase-orders/<int:po_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def manage_purchase_order(po_id):
    """Get, update, or delete a specific purchase order"""
    try:
        user_id = session.get('user_id')
        po = PurchaseOrder.query.filter_by(id=po_id, user_id=user_id).first()
        
        if not po:
            return jsonify({'error': 'Purchase order not found'}), 404
        
        if request.method == 'GET':
            return jsonify({
                'success': True,
                'purchase_order': po.to_dict()
            })
        
        elif request.method == 'PUT':
            data = request.get_json()
            
            # Update fields
            updatable_fields = ['status', 'total_amount', 'expected_date']
            for field in updatable_fields:
                if field in data:
                    if field == 'expected_date' and data[field]:
                        setattr(po, field, datetime.strptime(data[field], '%Y-%m-%d').date())
                    else:
                        setattr(po, field, data[field])
            
            po.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({
                'success': True,
                'purchase_order': po.to_dict()
            })
        
        elif request.method == 'DELETE':
            db.session.delete(po)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Purchase order {po.po_number} deleted successfully'
            })
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error managing purchase order: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/supply-chain/reorder-suggestions')
def get_reorder_suggestions():
    """Get automated reorder suggestions"""
    try:
        user_id = session.get('user_id')
        supply_chain = SupplyChainService(user_id)
        suggestions = supply_chain.automated_reorder_suggestions()
        return jsonify(suggestions)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== ENHANCED SECURITY API ROUTES =====

@app.route('/api/security/setup-2fa', methods=['POST'])
@login_required
def setup_2fa():
    """Set up two-factor authentication"""
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)

        from services.security_service import SecurityService
        security_service = SecurityService(user_id)

        result = security_service.setup_2fa(user.email)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error setting up 2FA: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/verify-2fa', methods=['POST'])
@login_required
def verify_2fa():
    """Verify 2FA token"""
    try:
        data = request.get_json()
        user_id = session.get('user_id')

        from services.security_service import SecurityService
        security_service = SecurityService(user_id)

        is_valid = security_service.verify_2fa_token(data['secret'], data['token'])

        if is_valid:
            # Update user 2FA status
            from models import UserTwoFactor, db

            two_fa = UserTwoFactor.query.filter_by(user_id=user_id).first()
            if not two_fa:
                two_fa = UserTwoFactor(user_id=user_id, secret_key=data['secret'])
                db.session.add(two_fa)

            two_fa.is_enabled = True
            db.session.commit()

        return jsonify({'success': is_valid})

    except Exception as e:
        logger.error(f"Error verifying 2FA: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/security/audit-logs')
@login_required
def get_audit_logs():
    """Get security audit logs"""
    try:
        user_id = session.get('user_id')

        from models import SecurityAudit

        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 50, type=int)

        audits = SecurityAudit.query.filter_by(user_id=user_id).order_by(
            SecurityAudit.timestamp.desc()
        ).paginate(page=page, per_page=per_page, error_out=False)

        return jsonify({
            'audits': [audit.to_dict() for audit in audits.items],
            'pagination': {
                'page': page,
                'pages': audits.pages,
                'per_page': per_page,
                'total': audits.total
            }
        })

    except Exception as e:
        logger.error(f"Error getting audit logs: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===== DATA MANAGEMENT API ROUTES =====

@app.route('/api/data/backup', methods=['POST'])
@login_required
def create_backup():
    """Create data backup"""
    try:
        user_id = session.get('user_id')

        from services.data_management_service import DataManagementService
        data_service = DataManagementService(user_id)

        result = data_service.create_automated_backup()
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error creating backup: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/export/<data_type>/<format_type>')
@login_required
def export_data_format(data_type, format_type):
    """Export data in specified format"""
    try:
        user_id = session.get('user_id')

        from services.data_management_service import DataManagementService
        data_service = DataManagementService(user_id)

        result = data_service.export_data_multiple_formats(data_type, format_type)

        if 'error' in result:
            return jsonify(result), 400

        return send_file(
            io.BytesIO(result['content'].encode() if format_type != 'excel' else result['content']),
            mimetype='application/octet-stream',
            as_attachment=True,
            download_name=result['filename']
        )

    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/data/archive', methods=['POST'])
@login_required
def archive_old_data():
    """Archive old records"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        archive_before = datetime.strptime(data['archive_before_date'], '%Y-%m-%d').date()

        from services.data_management_service import DataManagementService
        data_service = DataManagementService(user_id)

        result = data_service.archive_old_records(archive_before)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error archiving data: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===== TEAM MANAGEMENT API ROUTES =====

@app.route('/api/team/employees', methods=['GET', 'POST'])
@login_required
def manage_employees():
    """Get or create employees"""
    try:
        user_id = session.get('user_id')

        if request.method == 'GET':
            from models import Employee
            employees = Employee.query.filter_by(user_id=user_id, is_active=True).all()
            return jsonify([emp.to_dict() for emp in employees])
        else:
            data = request.get_json()

            from models import Employee, db

            employee = Employee(
                user_id=user_id,
                name=data['name'],
                email=data.get('email'),
                phone=data.get('phone'),
                role=data.get('role'),
                commission_rate=data.get('commission_rate', 0.0),
                hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d').date() if data.get('hire_date') else None,
                is_active=True
            )

            db.session.add(employee)
            db.session.commit()

            return jsonify({'success': True, 'employee_id': employee.id}), 201

    except Exception as e:
        logger.error(f"Error managing employees: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/team/performance/<int:employee_id>')
@login_required
def get_employee_performance(employee_id):
    """Get employee performance metrics"""
    try:
        user_id = session.get('user_id')

        period_start = datetime.strptime(request.args.get('start_date', ''), '%Y-%m-%d')
        period_end = datetime.strptime(request.args.get('end_date', ''), '%Y-%m-%d')

        from services.team_management_service import TeamManagementService
        team_service = TeamManagementService(user_id)

        performance = team_service.track_employee_performance(employee_id, period_start, period_end)
        return jsonify(performance)

    except Exception as e:
        logger.error(f"Error getting performance: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/team/commission/<int:employee_id>')
@login_required
def calculate_employee_commission(employee_id):
    """Calculate employee commission"""
    try:
        user_id = session.get('user_id')

        period_start = datetime.strptime(request.args.get('start_date', ''), '%Y-%m-%d')
        period_end = datetime.strptime(request.args.get('end_date', ''), '%Y-%m-%d')

        from services.team_management_service import TeamManagementService
        team_service = TeamManagementService(user_id)

        commission = team_service.calculate_commission(employee_id, period_start, period_end)
        return jsonify(commission)

    except Exception as e:
        logger.error(f"Error calculating commission: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/team/shifts', methods=['POST'])
@login_required
def schedule_shift():
    """Schedule employee shift"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        from services.team_management_service import TeamManagementService
        team_service = TeamManagementService(user_id)

        result = team_service.manage_shifts(data['employee_id'], data)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error scheduling shift: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===== SMS API ROUTES =====

@app.route('/api/sms/test', methods=['POST'])
@login_required
def test_sms_api():
    """Test SMS API functionality"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        message = data.get('message', 'Test SMS from your Inventory Management System')

        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400

        # Import SMS service
        from notifications.sms_service import send_sms
        
        # Send test SMS
        success = send_sms(phone_number, message)
        
        if success:
            return jsonify({
                'success': True,
                'message': 'Test SMS sent successfully',
                'phone_number': phone_number
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to send SMS. Check your Twilio credentials and phone number format.'
            }), 400

    except Exception as e:
        logger.error(f"Error testing SMS: {str(e)}")
        return jsonify({'error': f'SMS test failed: {str(e)}'}), 500

@app.route('/api/sms/config/check', methods=['GET'])
@login_required
def check_sms_config():
    """Check SMS configuration status"""
    try:
        import os
        
        config_status = {
            'twilio_account_sid': bool(os.environ.get('TWILIO_ACCOUNT_SID')),
            'twilio_auth_token': bool(os.environ.get('TWILIO_AUTH_TOKEN')),
            'twilio_phone_number': bool(os.environ.get('TWILIO_PHONE_NUMBER')),
            'configuration_complete': False
        }
        
        config_status['configuration_complete'] = all([
            config_status['twilio_account_sid'],
            config_status['twilio_auth_token'],
            config_status['twilio_phone_number']
        ])
        
        return jsonify(config_status)

    except Exception as e:
        logger.error(f"Error checking SMS config: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/test-sms', methods=['POST'])
@login_required
def test_notification_sms():
    """Test SMS notification system"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        message = data.get('message', 'Test notification from your Inventory Management System')

        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400

        # Import notification service
        from notifications.sms_service import send_sms
        
        # Send test SMS
        success = send_sms(phone_number, message)
        
        return jsonify({
            'success': success,
            'message': 'Test SMS sent successfully' if success else 'Failed to send SMS',
            'phone_number': phone_number
        })

    except Exception as e:
        logger.error(f"Error in notification SMS test: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/notifications/low-stock-alert', methods=['POST'])
@login_required
def send_low_stock_alert():
    """Manually trigger low stock SMS alert"""
    try:
        user_id = session.get('user_id')
        
        # Import required services
        from models import Item, Setting
        from notifications.notification_manager import check_low_stock_and_notify
        
        # Trigger low stock notification
        result = check_low_stock_and_notify(db, Item, Setting)
        
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error sending low stock alert: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===== MARKETING API ROUTES =====

@app.route('/api/marketing/email-campaign', methods=['POST'])
@login_required
def create_email_campaign():
    """Create email marketing campaign"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        from services.marketing_service import MarketingService
        marketing_service = MarketingService(user_id)

        result = marketing_service.create_email_campaign(data)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error creating email campaign: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/marketing/sms-promotion', methods=['POST'])
@login_required
def send_sms_promotion():
    """Send SMS promotion"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        from services.marketing_service import MarketingService
        marketing_service = MarketingService(user_id)

        result = marketing_service.send_sms_promotion(data)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error sending SMS promotion: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/marketing/feedback', methods=['POST'])
@login_required
def collect_feedback():
    """Collect customer feedback"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        from services.marketing_service import MarketingService
        marketing_service = MarketingService(user_id)

        result = marketing_service.collect_customer_feedback(data)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error collecting feedback: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/marketing/social-media', methods=['POST'])
@login_required
def schedule_social_post():
    """Schedule social media post"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        from services.marketing_service import MarketingService
        marketing_service = MarketingService(user_id)

        result = marketing_service.schedule_social_media_post(data)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error scheduling social post: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ecommerce/store', methods=['POST'])
@login_required
def create_online_store():
    """Create online store"""
    try:
        user_id = session.get('user_id')
        data = request.get_json()

        from services.marketing_service import MarketingService
        marketing_service = MarketingService(user_id)

        result = marketing_service.create_online_store(data)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error creating online store: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/ecommerce/sync-catalog/<int:store_id>', methods=['POST'])
@login_required
def sync_store_catalog(store_id):
    """Sync product catalog with online store"""
    try:
        user_id = session.get('user_id')

        from services.marketing_service import MarketingService
        marketing_service = MarketingService(user_id)

        result = marketing_service.sync_product_catalog(store_id)
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error syncing catalog: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===== DASHBOARD API ROUTES =====

def column_exists(table_name, column_name):
    """Helper function to check if column exists"""
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

@app.route('/api/health/database', methods=['GET'])
@login_required
def database_health_check():
    """Check database health and table status"""
    try:
        health_status = {
            'database_connected': False,
            'tables_exist': {},
            'missing_columns': {},
            'relationships_ok': True,
            'errors': []
        }
        
        # Test database connection
        try:
            db.session.execute(db.text('SELECT 1'))
            health_status['database_connected'] = True
        except Exception as e:
            health_status['errors'].append(f"Database connection failed: {str(e)}")
        
        # Check if all required tables exist
        required_tables = [
            'user', 'item', 'sale', 'sale_item', 'customer', 'category', 
            'financial_transaction', 'stock_movement', 'setting', 'supplier',
            'purchase_order', 'installment_plan', 'chart_of_accounts', 'journal'
        ]
        
        for table in required_tables:
            try:
                result = db.session.execute(db.text(f"SELECT COUNT(*) FROM {table}"))
                health_status['tables_exist'][table] = True
            except Exception as e:
                health_status['tables_exist'][table] = False
                health_status['errors'].append(f"Table {table} issue: {str(e)}")
        
        # Check for missing columns in key tables
        table_columns = {
            'item': ['stock_quantity', 'minimum_stock', 'retail_price', 'wholesale_price', 'user_id'],
            'sale': ['user_id', 'customer_id', 'total_amount', 'payment_status', 'sale_number'],
            'supplier': ['is_active', 'updated_at'],
            'journal': ['journal_number', 'total_debit', 'total_credit']
        }
        
        for table, columns in table_columns.items():
            health_status['missing_columns'][table] = []
            for column in columns:
                if not column_exists(table, column):
                    health_status['missing_columns'][table].append(column)
        
        # Overall health score
        total_checks = len(required_tables) + 1  # tables + connection
        passed_checks = sum(1 for exists in health_status['tables_exist'].values() if exists)
        passed_checks += 1 if health_status['database_connected'] else 0
        
        health_status['health_score'] = (passed_checks / total_checks) * 100
        health_status['status'] = 'healthy' if health_status['health_score'] >= 90 else 'needs_attention'
        
        return jsonify(health_status)
        
    except Exception as e:
        logger.error(f"Error checking database health: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/dashboard/summary', methods=['GET'])
@login_required
def get_dashboard_summary():
    """Get dashboard summary data"""
    try:
        user_id = session.get('user_id')
        from models import Item, Sale, Customer, FinancialTransaction
        from sqlalchemy import func

        # Get basic counts
        total_items = Item.query.filter_by(user_id=user_id, is_active=True).count()
        total_customers = Customer.query.filter_by(user_id=user_id).count()

        # Get stock information
        items = Item.query.filter_by(user_id=user_id, is_active=True).all()
        total_stock = sum(item.stock_quantity or 0 for item in items)
        low_stock_items = [item for item in items if (item.stock_quantity or 0) <= (item.minimum_stock or 0)]

        # Calculate inventory value
        inventory_value = sum((item.retail_price or 0) * (item.stock_quantity or 0) for item in items)

        # Get recent sales
        recent_sales = Sale.query.filter_by(user_id=user_id).order_by(Sale.created_at.desc()).limit(10).all()

        # Financial summary for current month
        today = datetime.now()
        start_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        monthly_income = db.session.query(func.sum(FinancialTransaction.amount)).filter(
            FinancialTransaction.user_id == user_id,
            FinancialTransaction.transaction_type == 'Income',
            FinancialTransaction.created_at >= start_of_month
        ).scalar() or 0

        monthly_expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
            FinancialTransaction.user_id == user_id,
            FinancialTransaction.transaction_type == 'Expense',
            FinancialTransaction.created_at >= start_of_month
        ).scalar() or 0

        monthly_profit = monthly_income - monthly_expenses

        return jsonify({
            'success': True,
            'summary': {
                'total_items': total_items,
                'total_stock': total_stock,
                'low_stock_count': len(low_stock_items),
                'inventory_value': float(inventory_value),
                'total_customers': total_customers,
                'monthly_income': float(monthly_income),
                'monthly_expenses': float(monthly_expenses),
                'monthly_profit': float(monthly_profit)
            },
            'low_stock_items': [
                {
                    'id': item.id,
                    'name': item.name,
                    'sku': item.sku,
                    'category': item.category.name if item.category else 'Uncategorized',
                    'stock_quantity': item.stock_quantity or 0,
                    'minimum_stock': item.minimum_stock or 0,
                    'retail_price': float(item.retail_price or 0)
                } for item in low_stock_items[:10]
            ],
            'recent_sales': [
                {
                    'id': sale.id,
                    'sale_number': sale.sale_number,
                    'total_amount': float(sale.total_amount or 0),
                    'payment_type': sale.payment_type,
                    'payment_status': sale.payment_status,
                    'created_at': sale.created_at.isoformat() if sale.created_at else None,
                    'customer_name': sale.customer.name if sale.customer else 'Walk-in Customer'
                } for sale in recent_sales
            ]
        })
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===== SALES MANAGEMENT API ROUTES =====

@app.route('/api/sales/completed', methods=['GET'])
@login_required
def get_completed_sales():
    """Get completed sales with pagination and filtering"""
    try:
        user_id = session.get('user_id')
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Date filters
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        payment_method = request.args.get('payment_method')
        
        # Build query
        query = Sale.query.filter_by(user_id=user_id)
        
        if start_date:
            try:
                start_date = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Sale.created_at >= start_date)
            except ValueError:
                pass
                
        if end_date:
            try:
                end_date = datetime.strptime(end_date, '%Y-%m-%d')
                query = query.filter(Sale.created_at <= end_date)
            except ValueError:
                pass
        
        if payment_method:
            query = query.filter(Sale.payment_method == payment_method)
        
        # Execute query with pagination
        sales = query.order_by(Sale.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Calculate summary data
        all_sales = Sale.query.filter_by(user_id=user_id).all()
        total_completed_sales = len(all_sales)
        total_revenue = sum(float(sale.total_amount or 0) for sale in all_sales)
        average_transaction = total_revenue / total_completed_sales if total_completed_sales > 0 else 0
        
        # Format response
        sales_data = []
        for sale in sales.items:
            sale_dict = {
                'id': sale.id,
                'sale_number': sale.sale_number,
                'customer_name': sale.customer_name or 'Walk-in Customer',
                'customer_phone': sale.customer_phone,
                'total_amount': float(sale.total_amount or 0),
                'payment_method': sale.payment_method or 'cash',
                'payment_status': sale.payment_status or 'completed',
                'created_at': sale.created_at.isoformat() if sale.created_at else None,
                'items_count': len(sale.sale_items),
                'items': [
                    {
                        'name': item.item.name if item.item else 'Unknown Item',
                        'quantity': item.quantity,
                        'unit_price': float(item.unit_price or 0),
                        'total_price': float(item.total_price or 0)
                    } for item in sale.sale_items
                ]
            }
            sales_data.append(sale_dict)
        
        return jsonify({
            'success': True,
            'sales': sales_data,
            'pagination': {
                'page': page,
                'pages': sales.pages,
                'per_page': per_page,
                'total': sales.total,
                'has_next': sales.has_next,
                'has_prev': sales.has_prev
            },
            'summary': {
                'total_completed_sales': total_completed_sales,
                'total_revenue': total_revenue,
                'average_transaction': average_transaction
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting completed sales: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales/<int:sale_id>', methods=['GET'])
@login_required
def get_sale_details(sale_id):
    """Get detailed information for a specific sale"""
    try:
        user_id = session.get('user_id')
        sale = Sale.query.filter_by(id=sale_id, user_id=user_id).first()
        
        if not sale:
            return jsonify({'error': 'Sale not found'}), 404
        
        sale_dict = sale.to_dict()
        # Add customer details
        if sale.customer:
            sale_dict['customer'] = sale.customer.to_dict()
        # Add sale items with product details
        sale_dict['items'] = []
        for item in sale.sale_items:
            item_dict = item.to_dict()
            if item.item:
                item_dict['product'] = item.item.to_dict()
            sale_dict['items'].append(item_dict)
        
        return jsonify({
            'success': True,
            'sale': sale_dict
        })
        
    except Exception as e:
        logger.error(f"Error getting sale details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales/receipt/<sale_number>', methods=['GET'])
@login_required
def get_receipt(sale_number):
    """Generate and return receipt for a sale"""
    try:
        user_id = session.get('user_id')
        sale = Sale.query.filter_by(sale_number=sale_number, user_id=user_id).first()
        
        if not sale:
            return jsonify({'error': 'Sale not found'}), 404
        
        # Get user details for receipt header
        user = User.query.get(user_id)
        
        # Format receipt data
        receipt_data = {
            'business_name': user.shop_name or f"{user.first_name}'s Shop",
            'business_phone': user.phone,
            'business_email': user.email,
            'sale_number': sale.sale_number,
            'date': sale.created_at.strftime('%Y-%m-%d %H:%M:%S'),
            'customer_name': sale.customer_name or 'Walk-in Customer',
            'customer_phone': sale.customer_phone,
            'items': [],
            'subtotal': float(sale.subtotal),
            'discount_amount': float(sale.discount_amount),
            'total_amount': float(sale.total_amount),
            'payment_method': sale.payment_method,
            'payment_amount': float(sale.payment_amount),
            'change_amount': float(sale.change_amount)
        }
        
        # Add items
        for item in sale.sale_items:
            receipt_data['items'].append({
                'name': item.item.name if item.item else 'Unknown Item',
                'quantity': item.stock_quantity,
                'unit_price': float(item.unit_price),
                'total_price': float(item.total_price)
            })
        
        return jsonify({
            'success': True,
            'receipt': receipt_data
        })
        
    except Exception as e:
        logger.error(f"Error generating receipt: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales/<int:sale_id>', methods=['PUT'])
@login_required
def update_sale(sale_id):
    """Update a sale (limited fields)"""
    try:
        user_id = session.get('user_id')
        sale = Sale.query.filter_by(id=sale_id, user_id=user_id).first()
        
        if not sale:
            return jsonify({'error': 'Sale not found'}), 404
        
        data = request.get_json()
        
        # Only allow updating certain fields
        updatable_fields = ['customer_name', 'customer_phone', 'notes', 'payment_status']
        
        for field in updatable_fields:
            if field in data:
                setattr(sale, field, data[field])
        
        db.session.commit()
        
        return jsonify({
            'success': True,
            'sale': sale.to_dict()
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating sale: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales/<int:sale_id>', methods=['DELETE'])
@login_required
def delete_sale(sale_id):
    """Delete a sale and restore inventory"""
    try:
        user_id = session.get('user_id')
        sale = Sale.query.filter_by(id=sale_id, user_id=user_id).first()
        
        if not sale:
            return jsonify({'error': 'Sale not found'}), 404
        
        # Restore inventory for each item
        for sale_item in sale.sale_items:
            item = sale_item.item
            if item:
                item.stock_quantity += sale_item.quantity
                
                # Create stock movement record
                stock_movement = StockMovement(
                    movement_type='in',
                    quantity=sale_item.quantity,
                    reason=f'Sale deletion - {sale.sale_number}',
                    item_id=item.id,
                    user_id=user_id,
                    created_at=datetime.utcnow()
                )
                db.session.add(stock_movement)
        
        # Delete the sale (cascade will handle sale_items)
        db.session.delete(sale)
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': f'Sale {sale.sale_number} deleted successfully'
        })
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting sale: {str(e)}")
        return jsonify({'error': str(e)}), 500

# ===== BUSINESS INTELLIGENCE API ROUTES =====

@app.route('/api/bi/kpis')
def get_real_time_kpis():
    """Get real-time KPI data"""
    try:
        user_id = session.get('user_id')
        bi_service = BusinessIntelligenceService(user_id)
        kpis = bi_service.get_real_time_kpis()
        return jsonify(kpis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/comparative-analysis')
def get_comparative_analysis():
    """Get comparative analysis (YoY, MoM)"""
    try:
        user_id = session.get('user_id')
        period = request.args.get('period', 'monthly')
        bi_service = BusinessIntelligenceService(user_id)
        analysis = bi_service.get_comparative_analysis(period)
        return jsonify(analysis)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/profit-margins')
def get_profit_margins():
    """Get profit margin analysis"""
    try:
        user_id = session.get('user_id')
        bi_service = BusinessIntelligenceService(user_id)
        margins = bi_service.get_profit_margin_analysis()
        return jsonify(margins)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/cash-flow-forecast')
def get_cash_flow_forecast():
    """Get cash flow forecasting"""
    try:
        user_id = session.get('user_id')
        days_ahead = request.args.get('days_ahead', 30, type=int)
        bi_service = BusinessIntelligenceService(user_id)
        forecast = bi_service.get_cash_flow_forecast(days_ahead)
        return jsonify(forecast)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/bi/dashboard')
def get_bi_dashboard():
    """Get all BI dashboard data in one call"""
    try:
        user_id = session.get('user_id')
        bi_service = BusinessIntelligenceService(user_id)
        dashboard_data = bi_service.get_dashboard_widgets()
        return jsonify(dashboard_data)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/get_cart')
@login_required
def get_cart():
    cart = session.get('cart', [])
    return jsonify({'cart': cart})

@app.route('/api/clear_cart', methods=['POST'])
@login_required
def clear_cart():
    session.pop('cart', None)
    return jsonify({'success': True, 'message': 'Cart cleared'})

@app.route('/api/inventory')
@login_required
def api_inventory():
    """API endpoint to get inventory items for sales interface"""
    try:
        # Get current user ID
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify([])

        search = request.args.get('search', '')
        category_id = request.args.get('category_id', type=int)

        # Build query
        query = Item.query.filter_by(user_id=current_user_id, is_active=True)

        if search:
            query = query.filter(
                or_(
                    Item.name.ilike(f'%{search}%'),
                    Item.sku.ilike(f'%{search}%'),
                    Item.description.ilike(f'%{search}%')
                )
            )

        if category_id:
            query = query.filter_by(category_id=category_id)

        items = query.order_by(Item.name).all()

        # Format items for frontend
        inventory_data = []
        for item in items:
            inventory_data.append({
                'id': item.id,
                'name': item.name,
                'sku': item.sku or '',
                'description': item.description or '',
                'category': item.category.name if item.category else 'Uncategorized',
                'category_id': item.category_id,
                'buying_price': float(item.buying_price or 0),
                'wholesale_price': float(item.wholesale_price or 0),
                'retail_price': float(item.retail_price or 0),
                'price': float(item.price or 0),
                'selling_price_retail': float(item.retail_price or 0),
                'selling_price_wholesale': float(item.wholesale_price or 0),
                'quantity': item.stock_quantity or 0,
                'minimum_stock': item.minimum_stock or 0,
                'unit_type': item.unit_type or 'quantity',
                'sales_type': item.sell_by or 'both',
                'created_at': item.created_at.isoformat() if item.created_at else None,
                'updated_at': item.updated_at.isoformat() if item.updated_at else None
            })

        return jsonify(inventory_data)

    except Exception as e:
        return jsonify({'error': str(e)}), 500

# ===== ITEMS/INVENTORY CRUD API ROUTES =====

@app.route('/api/items', methods=['GET', 'POST'])
@login_required
def api_items():
    """API endpoint for Items CRUD operations"""
    from models import Item, Category, db
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    if request.method == 'GET':
        # Get all items for current user
        items = Item.query.filter_by(user_id=user_id, is_active=True).all()
        items_data = []
        for item in items:
            items_data.append(item.to_dict())
        return jsonify({'success': True, 'items': items_data})
    
    elif request.method == 'POST':
        # Create new item
        try:
            data = request.get_json()
            
            # Generate SKU if not provided
            sku = data.get('sku')
            if not sku:
                # Simple SKU generation
                import re
                clean_name = re.sub(r'[^a-zA-Z0-9]', '', data['name'][:10]).upper()
                sku = f"{clean_name}-{datetime.utcnow().strftime('%Y%m%d')}"
            
            # Check if SKU already exists
            existing_item = Item.query.filter_by(sku=sku, user_id=user_id).first()
            if existing_item:
                return jsonify({'error': f'SKU "{sku}" already exists'}), 400
            
            # Create new item
            item = Item(
                name=data['name'],
                description=data.get('description'),
                sku=sku,
                stock_quantity=int(data.get('stock_quantity', 0)),
                minimum_stock=int(data.get('minimum_stock', 0)),
                buying_price=float(data.get('buying_price', 0)),
                retail_price=float(data.get('retail_price', 0)),
                wholesale_price=float(data.get('wholesale_price', 0)),
                sales_type=data.get('sales_type', 'both'),
                category=data.get('category', 'Uncategorized'),
                subcategory=data.get('subcategory'),
                category_id=data.get('category_id'),
                user_id=user_id,
                is_active=True
            )
            
            db.session.add(item)
            db.session.commit()
            
            return jsonify({'success': True, 'item': item.to_dict()}), 201
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error creating item: {str(e)}')
            return jsonify({'error': str(e)}), 500

@app.route('/api/items/<int:item_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_item_by_id(item_id):
    """API endpoint for single Item CRUD operations"""
    from models import Item, db
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    item = Item.query.filter_by(id=item_id, user_id=user_id).first()
    if not item:
        return jsonify({'error': 'Item not found'}), 404
    
    if request.method == 'GET':
        return jsonify({'success': True, 'item': item.to_dict()})
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            
            # Update item fields
            if 'name' in data:
                item.name = data['name']
            if 'description' in data:
                item.description = data['description']
            if 'stock_quantity' in data:
                item.stock_quantity = int(data['stock_quantity'])
            if 'minimum_stock' in data:
                item.minimum_stock = int(data['minimum_stock'])
            if 'buying_price' in data:
                item.buying_price = float(data['buying_price'])
            if 'retail_price' in data:
                item.retail_price = float(data['retail_price'])
            if 'wholesale_price' in data:
                item.wholesale_price = float(data['wholesale_price'])
            if 'sales_type' in data:
                item.sales_type = data['sales_type']
            if 'category' in data:
                item.category = data['category']
            if 'subcategory' in data:
                item.subcategory = data['subcategory']
            if 'category_id' in data:
                item.category_id = data['category_id']
            
            item.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({'success': True, 'item': item.to_dict()})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error updating item: {str(e)}')
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            # Soft delete - mark as inactive
            item.is_active = False
            item.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Item deleted successfully'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error deleting item: {str(e)}')
            return jsonify({'error': str(e)}), 500

# ===== CUSTOMERS CRUD API ROUTES =====

@app.route('/api/customers/<int:customer_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required 
def api_customer_by_id(customer_id):
    """API endpoint for single Customer CRUD operations"""
    from models import Customer, db
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    customer = Customer.query.filter_by(id=customer_id, user_id=user_id).first()
    if not customer:
        return jsonify({'error': 'Customer not found'}), 404
    
    if request.method == 'GET':
        return jsonify({'success': True, 'customer': customer.to_dict()})
    
    elif request.method == 'PUT':
        try:
            data = request.get_json()
            
            # Update customer fields
            if 'name' in data:
                customer.name = data['name']
            if 'email' in data:
                customer.email = data['email']
            if 'phone' in data:
                customer.phone = data['phone']
            if 'address' in data:
                customer.address = data['address']
            if 'customer_type' in data:
                customer.customer_type = data['customer_type']
            if 'credit_limit' in data:
                customer.credit_limit = float(data['credit_limit'])
            if 'preferred_payment_method' in data:
                customer.preferred_payment_method = data['preferred_payment_method']
            
            customer.updated_at = datetime.utcnow()
            db.session.commit()
            
            return jsonify({'success': True, 'customer': customer.to_dict()})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error updating customer: {str(e)}')
            return jsonify({'error': str(e)}), 500
    
    elif request.method == 'DELETE':
        try:
            db.session.delete(customer)
            db.session.commit()
            
            return jsonify({'success': True, 'message': 'Customer deleted successfully'})
            
        except Exception as e:
            db.session.rollback()
            logger.error(f'Error deleting customer: {str(e)}')
            return jsonify({'error': str(e)}), 500

# ===== SALES CRUD API ROUTES =====

@app.route('/api/sales', methods=['GET'])
@login_required
def api_sales():
    """API endpoint to get all sales for the current user"""
    from models import Sale
    
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Authentication required'}), 401
    
    try:
        # Get pagination parameters
        page = request.args.get('page', 1, type=int)
        per_page = request.args.get('per_page', 20, type=int)
        
        # Get sales with pagination
        sales = Sale.query.filter_by(user_id=user_id).order_by(Sale.created_at.desc()).paginate(
            page=page, per_page=per_page, error_out=False
        )
        
        # Format sales data
        sales_data = []
        for sale in sales.items:
            sale_dict = sale.to_dict()
            # Add sale items
            sale_items = []
            for item in sale.sale_items:
                sale_items.append(item.to_dict())
            sale_dict['items'] = sale_items
            sales_data.append(sale_dict)
        
        return jsonify({
            'success': True,
            'sales': sales_data,
            'pagination': {
                'page': sales.page,
                'pages': sales.pages,
                'per_page': sales.per_page,
                'total': sales.total,
                'has_next': sales.has_next,
                'has_prev': sales.has_prev
            }
        })
        
    except Exception as e:
        logger.error(f'Error getting sales: {str(e)}')
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales/performance/top', methods=['GET'])
@login_required
def api_top_selling_items():
    """API endpoint for top selling items"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401

        # Get top selling items for current user
        from sqlalchemy import func
        
        top_items_query = db.session.query(
            Item.id,
            Item.name,
            Item.category,
            func.sum(SaleItem.quantity).label('units_sold'),
            func.sum(SaleItem.total_price).label('revenue')
        ).join(SaleItem).join(Sale).filter(
            Sale.user_id == user_id
        ).group_by(Item.id, Item.name, Item.category).order_by(
            func.sum(SaleItem.quantity).desc()
        ).limit(10)

        top_items = []
        for item in top_items_query.all():
            top_items.append({
                'id': item.id,
                'name': item.name,
                'category': item.category or 'Uncategorized',
                'units_sold': int(item.units_sold or 0),
                'revenue': float(item.revenue or 0)
            })

        return jsonify({
            'success': True,
            'top_items': top_items
        })
        
    except Exception as e:
        logger.error(f'Error getting top selling items: {str(e)}')
        return jsonify({
            'success': True,
            'top_items': []  # Return empty array on error to prevent frontend crashes
        })

@app.route('/api/sales', methods=['POST'])
@login_required
def api_create_sale():
    """API endpoint to create a new sale"""
    try:
        # Import models here to ensure they are available
        from models import Item, Sale, SaleItem, StockMovement
        
        # Validate user session
        user_id = session.get('user_id')
        if not user_id:
            logger.error("Sale creation failed: No user session found")
            return jsonify({'error': 'Authentication required'}), 401

        data = request.get_json()
        logger.info(f"Sale creation request: {data}")

        if not data or not data.get('items'):
            logger.error("Sale creation failed: No items provided")
            return jsonify({'error': 'No items provided'}), 400

        # Validate that all items belong to the user
        item_ids = [item.get('id') or item.get('item_id') for item in data.get('items', [])]
        if not item_ids:
            logger.error("Sale creation failed: No items provided")
            return jsonify({'error': 'No items provided'}), 400
            
        items_check = Item.query.filter(Item.id.in_(item_ids), Item.user_id == user_id).count()
        if items_check != len(item_ids):
            logger.error(f"Sale creation failed: Items don't belong to user {user_id}")
            return jsonify({'error': 'Invalid items selected'}), 400

        # Generate sale number
        sale_number = f"SALE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        # Create sale record
        sale = Sale(
            sale_number=sale_number,
            invoice_number=sale_number,
            customer_name=data.get('customer', {}).get('name', 'Walk-in Customer'),
            customer_phone=data.get('customer', {}).get('phone'),
            sale_type=data.get('sale_type', 'retail'),
            subtotal=float(data.get('subtotal', data.get('total', 0))),
            discount_type=data.get('discount', {}).get('type', 'none'),
            discount_value=float(data.get('discount', {}).get('value', 0)),
            discount_amount=float(data.get('discount', {}).get('amount', 0)),
            total_amount=float(data.get('total', 0)),
            payment_method=data.get('payment_method', 'cash'),
            payment_amount=float(data.get('payment', {}).get('amount', data.get('total', 0))),
            change_amount=float(data.get('payment', {}).get('change', 0)),
            notes=data.get('notes', ''),
            user_id=user_id,
            payment_status='paid',
            created_at=datetime.utcnow()
        )

        # Handle payment details for mobile money and installments
        payment_details = {}
        if data.get('payment', {}).get('method') == 'mobile_money':
            mobile_info = data.get('payment', {}).get('mobile_info', {})
            payment_details.update(mobile_info)
        elif data.get('payment', {}).get('method') == 'installment':
            installment_info = data.get('payment', {}).get('installment_info', {})
            payment_details.update(installment_info)
            sale.payment_status = 'partial' if installment_info.get('down_payment', 0) > 0 else 'pending'

        if payment_details:
            sale.payment_details = json.dumps(payment_details)

        db.session.add(sale)
        db.session.flush()  # Get the sale ID

        # Create sale items and update inventory
        for item_data in data.get('items', []):
            logger.info(f"Processing item: {item_data}")
            item_id = item_data.get('id') or item_data.get('item_id')
            item = Item.query.filter_by(id=item_id, user_id=user_id).first()
            if not item:
                logger.error(f"Item not found: {item_id} for user {user_id}")
                raise Exception(f"Item not found: {item_id}")

            # Check stock availability (use stock_quantity field as main stock tracker)
            current_stock = item.stock_quantity if item.stock_quantity is not None else 0
                
            logger.info(f"Current stock for {item.name}: {current_stock}, requested: {item_data['quantity']}")
            if current_stock < item_data['quantity']:
                logger.error(f"Insufficient stock for {item.name}: {current_stock} < {item_data['quantity']}")
                raise Exception(f"Insufficient stock for {item.name}. Available: {current_stock}, Requested: {item_data['quantity']}")

            # Create sale item
            sale_item = SaleItem(
                sale_id=sale.id,
                item_id=item.id,
                quantity=item_data['quantity'],
                unit_price=float(item_data['price']),
                unit_cost=float(item.buying_price or 0),
                total_price=float(item_data['quantity'] * item_data['price'])
            )
            db.session.add(sale_item)

            # Update item stock 
            item.stock_quantity = max(0, item.stock_quantity - item_data['quantity'])

            # Create stock movement with user_id
            stock_movement = StockMovement(
                movement_type='out',
                quantity=item_data['quantity'],
                reason=f'Sale {sale_number}',
                item_id=item.id,
                user_id=user_id,
                created_at=datetime.utcnow()
            )
            db.session.add(stock_movement)
            logger.info(f"Updated stock for {item.name}: new quantity = {item.stock_quantity}")

        db.session.commit()
        
        logger.info(f"Sale completed successfully: {sale_number} for user {user_id}")

        return jsonify({
            'success': True,
            'sale_id': sale.id,
            'sale_number': sale_number,
            'total_amount': float(sale.total_amount),
            'message': 'Sale created successfully'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Sale creation failed: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500



@app.route('/api/sales/performance/slow')
@login_required
def api_slow_moving_items():
    """API endpoint for slow moving items"""
    try:
        # Get items with low sales in the last 30 days
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)

        slow_items = db.session.query(
            Item.id,
            Item.name,
            Category.name.label('category'),
            Item.stock_quantity,
            func.coalesce(func.sum(SaleItem.quantity), 0).label('units_sold')
        ).outerjoin(SaleItem).outerjoin(Sale, and_(
            SaleItem.sale_id == Sale.id,
            Sale.user_id == session.get('user_id'),
            Sale.created_at >= thirty_days_ago
        )).outerjoin(Category, Item.category_id == Category.id)\
        .filter(Item.user_id == session.get('user_id'), Item.is_active == True)\
        .group_by(Item.id, Item.name, Category.name, Item.stock_quantity)\
        .having(func.coalesce(func.sum(SaleItem.quantity), 0) <= 5)\
        .order_by(func.coalesce(func.sum(SaleItem.quantity), 0))\
        .limit(10).all()

        result = []
        for item in slow_items:
            result.append({
                'id': item.id,
                'name': item.name,
                'category': item.category or 'Uncategorized',
                'stock_quantity': item.stock_quantity,
                'units_sold': int(item.units_sold)
            })

        return jsonify(result)

    except Exception as e:
        return jsonify([])

@app.route('/sales')
@login_required
def sales():
    """Enhanced sales overview with payment types and installment management"""
    try:
        page = request.args.get('page', 1, type=int)
        user_id = session.get('user_id')
        
        if not user_id:
            logger.error("Sales route: No user_id in session")
            flash('Please log in to access sales data', 'error')
            return redirect(url_for('login'))

        from models import Sale
        from sqlalchemy import desc
        
        # Get paginated sales with error handling
        try:
            sales = Sale.query.filter_by(user_id=user_id).order_by(desc(Sale.created_at)).paginate(
                page=page, per_page=20, error_out=False
            )
        except Exception as e:
            logger.error(f"Error querying sales: {str(e)}")
            # Return empty pagination object if query fails
            sales = type('obj', (object,), {
                'items': [],
                'pages': 1,
                'page': 1,
                'total': 0,
                'has_prev': False,
                'has_next': False
            })()

        # Calculate metrics by payment type with error handling
        try:
            all_sales = Sale.query.filter_by(user_id=user_id).all()
            total_sales = sum(float(sale.total_amount or 0) for sale in all_sales)
            cash_sales = sum(float(sale.total_amount or 0) for sale in all_sales if (sale.payment_type == 'cash' or sale.payment_method == 'cash'))
            installment_sales = sum(float(sale.total_amount or 0) for sale in all_sales if (sale.payment_type == 'installment' or sale.payment_method == 'installment'))
            other_sales = sum(float(sale.total_amount or 0) for sale in all_sales if sale.payment_type not in ['cash', 'installment'] and sale.payment_method not in ['cash', 'installment'])
        except Exception as e:
            logger.error(f"Error calculating sales metrics: {str(e)}")
            total_sales = cash_sales = installment_sales = other_sales = 0

        # Get installment plans summary with error handling
        try:
            from models import InstallmentPlan
            from datetime import datetime
            
            # Check if InstallmentPlan table exists
            active_plans = []
            total_outstanding = 0
            overdue_count = 0
            
            try:
                active_plans = InstallmentPlan.query.join(Sale).filter(
                    Sale.user_id == user_id,
                    InstallmentPlan.status == 'active'
                ).all()
                
                # Calculate outstanding amounts
                total_outstanding = sum(plan.outstanding_amount for plan in active_plans)
                overdue_count = sum(1 for plan in active_plans if plan.next_due_date and plan.next_due_date < datetime.now().date())
            except Exception as plan_error:
                logger.warning(f"InstallmentPlan query failed: {str(plan_error)}")
                # Continue with empty values if InstallmentPlan table doesn't exist
                
        except Exception as e:
            logger.error(f"Error getting installment plans: {str(e)}")
            active_plans = []
            total_outstanding = 0
            overdue_count = 0

        return render_template('sales.html', 
                             sales=sales, 
                             total_sales=total_sales,
                             cash_sales=cash_sales,
                             installment_sales=installment_sales, 
                             other_sales=other_sales,
                             active_plans=active_plans,
                             total_outstanding=total_outstanding,
                             overdue_count=overdue_count)
                             
    except Exception as e:
        logger.error(f"Sales route error: {str(e)}")
        db.session.rollback()
        flash('Error loading sales data. Please try again.', 'error')
        return render_template('sales.html', 
                             sales=type('obj', (object,), {
                                 'items': [],
                                 'pages': 1,
                                 'page': 1,
                                 'total': 0,
                                 'has_prev': False,
                                 'has_next': False
                             })(), 
                             total_sales=0,
                             cash_sales=0,
                             installment_sales=0, 
                             other_sales=0,
                             active_plans=[],
                             total_outstanding=0,
                             overdue_count=0)

@app.route('/new_sale')
@login_required
def new_sale():
    """Create a new sale with payment options"""
    from models import Item, Customer
    items = Item.query.filter_by(user_id=session.get('user_id'), is_active=True).filter(Item.stock_quantity > 0).order_by(Item.name).all()
    customers = Customer.query.filter_by(user_id=session.get('user_id')).order_by(Customer.name).all()
    return render_template('sales.html', items=items, customers=customers)

@app.route('/margin')
@login_required
def margin():
    """Margin analysis page"""
    return render_template('margin.html')

@app.route('/accounting')
@login_required
def accounting():
    """Accounting dashboard page"""
    return render_template('accounting.html')

@app.route('/installments')
@login_required
def installments():
    """Installments management page"""
    return render_template('installments.html')

@app.route('/reports')
@login_required
def reports():
    """Reports page"""
    return render_template('reports.html')

@app.route('/inventory')
@login_required
def inventory():
    """Inventory management page"""
    return render_template('inventory.html')

@app.route('/on_demand')
@login_required
def on_demand():
    """On-demand products page"""
    return render_template('on_demand.html')

@app.route('/admin/users')
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

@app.route('/categories')
@login_required
def categories():
    """Categories management page"""
    return render_template('categories.html')

@app.route('/settings')
@login_required
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/security-management')
@login_required
def security_management():
    """Security and management dashboard"""
    return render_template('security_management.html')

@app.route('/')
def index():
    """Root route - show cover page for new visitors, redirect to dashboard if logged in"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('cover.html')

@app.route('/cover')
def cover():
    """Cover page route"""
    return render_template('cover.html')

@app.route('/dashboard')
@login_required
def dashboard():
    print("here we are")
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/login')
def login():
    """Login page route"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register')
def register():
    """Registration page route"""
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('register.html')

# All routes are now defined directly in app.py for better organization

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    """Handle 404 errors"""
    logger.error(f"404 error: {request.url}")
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"500 error: {str(error)}")
    db.session.rollback()
    return render_template('500.html'), 500

@app.errorhandler(Exception)
def handle_exception(e):
    """Handle general exceptions"""
    # Pass through HTTP errors
    if hasattr(e, 'code'):
        return e

    # Handle BuildError for missing routes more gracefully
    if 'Could not build url for endpoint' in str(e):
        # Only log once per unique error to avoid spam
        error_msg = str(e)
        if not hasattr(app, '_logged_build_errors'):
            app._logged_build_errors = set()

        if error_msg not in app._logged_build_errors:
            logger.error(f"Missing route endpoint: {error_msg}")
            app._logged_build_errors.add(error_msg)

        # Try to redirect to dashboard instead of showing error
        try:
            return redirect(url_for('dashboard'))
        except:
            return "Application Error - Please check route configuration", 500

    # Handle other exceptions
    logger.error(f"Unhandled exception: {str(e)}")
    try:
        db.session.rollback()
    except:
        pass
    return render_template('500.html'), 500

if __name__ == '__main__':
    success = init_database()
    if not success:
        logger.error("Database initialization failed")
        exit(1)
    app.run(debug=True)