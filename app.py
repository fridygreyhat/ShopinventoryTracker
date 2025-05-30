import os
import logging
import uuid
import json
from datetime import datetime, timedelta
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
import io
import csv
import requests
from dotenv import load_dotenv

load_dotenv()
# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET",
                                "shop_inventory_default_secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Firebase configuration
app.config["FIREBASE_API_KEY"] = os.environ.get("FIREBASE_API_KEY")
app.config["FIREBASE_PROJECT_ID"] = os.environ.get("FIREBASE_PROJECT_ID")
app.config["FIREBASE_APP_ID"] = os.environ.get("FIREBASE_APP_ID")
print(os.environ.get("FIREBASE_API_KEY"))


# Database configuration
class Base(DeclarativeBase):
    pass


app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get(
    "DATABASE_URL", "sqlite:///inventory.db")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(model_class=Base)
db.init_app(app)


# Helper function to get settings
def get_setting_value(key, default=None):
    """
    Get setting value from database

    Args:
        key (str): Setting key
        default: Default value if setting not found

    Returns:
        any: Setting value or default
    """
    from models import Setting
    setting = Setting.query.filter_by(key=key).first()
    return setting.value if setting else default


# Import auth service
from auth_service import login_required, verify_firebase_token, create_or_update_user


# Template helper function
@app.context_processor
def inject_current_user():
    """Inject current user into all templates"""

    def get_current_user():
        if 'user_id' in session:
            try:
                user = User.query.get(session['user_id'])
                return user
            except Exception as e:
                # Handle database schema issues gracefully
                logger.warning(f"Error getting current user: {str(e)}")
                # Clear the invalid session
                session.clear()
                return None
        return None

    return dict(get_current_user=get_current_user)


# Initialize database tables
with app.app_context():
    # Import models to ensure they are registered with SQLAlchemy
    from models import Item, User, Subuser, SubuserPermission, Setting, Sale, SaleItem, FinancialTransaction, Category, Subcategory
    import json

    # When we have schema changes, we need to reset the database
    # Comment out the line below to avoid data loss in production
    # db.drop_all()  # Commented out to prevent data loss

    # First, create all tables
    db.create_all()

    # Then, handle migrations for existing databases
    # Helper function to check if column exists
    def column_exists(table_name, column_name):
        try:
            result = db.session.execute(
                db.text(f"PRAGMA table_info({table_name})"))
            columns = [row[1] for row in result.fetchall()]
            return column_name in columns
        except Exception:
            return False

    # Helper function to add column safely
    def add_column_safely(table_name,
                          column_name,
                          column_definition,
                          default_value=None):
        try:
            if not column_exists(table_name, column_name):
                logger.info(
                    f"Adding {column_name} column to {table_name} table")
                db.session.execute(
                    db.text(
                        f"ALTER TABLE {table_name} ADD COLUMN {column_name} {column_definition}"
                    ))

                if default_value:
                    db.session.execute(
                        db.text(
                            f"UPDATE {table_name} SET {column_name} = {default_value}"
                        ))

                db.session.commit()
                logger.info(
                    f"Successfully added {column_name} column to {table_name}")
                return True
            else:
                logger.info(
                    f"{column_name} column already exists in {table_name}")
                return False
        except Exception as e:
            logger.error(
                f"Error adding {column_name} column to {table_name}: {str(e)}")
            db.session.rollback()
            return False

    # Check if tables exist and add missing columns
    try:
        # Check if user table exists
        result = db.session.execute(
            db.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='user';"
            ))
        if result.fetchone():
            # Add is_active column if missing
            add_column_safely('user', 'is_active', 'BOOLEAN DEFAULT 1', '1')
            # Add phone column if missing
            add_column_safely('user', 'phone', 'VARCHAR(20)')

        # Check if item table exists
        result = db.session.execute(
            db.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='item';"
            ))
        if result.fetchone():
            # Add missing item columns
            add_column_safely('item', 'subcategory', 'VARCHAR(100)')
            add_column_safely('item', 'unit_type',
                              'VARCHAR(20) DEFAULT "quantity"', '"quantity"')
            add_column_safely('item', 'sell_by',
                              'VARCHAR(20) DEFAULT "quantity"', '"quantity"')
            add_column_safely('item', 'category_id', 'INTEGER')
            add_column_safely('item', 'user_id', 'INTEGER')

            # Set user_id for existing items (assign to first admin user if exists)
            try:
                first_admin = User.query.filter_by(is_admin=True).first()
                if first_admin:
                    db.session.execute(
                        db.text("UPDATE item SET user_id = :user_id WHERE user_id IS NULL"),
                        {"user_id": first_admin.id}
                    )
                    db.session.commit()
                    logger.info(f"Assigned existing items to admin user: {first_admin.username}")
            except Exception as e:
                logger.error(f"Error assigning existing items to admin: {str(e)}")
                db.session.rollback()

        # Check if financial_transaction table exists and add missing columns
        result = db.session.execute(
            db.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='financial_transaction';"
            ))
        if result.fetchone():
            # Add missing financial transaction columns
            add_column_safely('financial_transaction', 'tax_rate', 'FLOAT DEFAULT 0.0', '0.0')
            add_column_safely('financial_transaction', 'tax_amount', 'FLOAT DEFAULT 0.0', '0.0')
            add_column_safely('financial_transaction', 'cost_of_goods_sold', 'FLOAT DEFAULT 0.0', '0.0')
            add_column_safely('financial_transaction', 'gross_amount', 'FLOAT DEFAULT 0.0', '0.0')

        # Check if subuser table exists and add missing columns
        result = db.session.execute(
            db.text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='subuser';"
            ))
        if result.fetchone():
            # Add missing subuser columns
            add_column_safely('subuser', 'staff_id', 'VARCHAR(20)')
            add_column_safely('subuser', 'department', 'VARCHAR(50)')
            add_column_safely('subuser', 'position', 'VARCHAR(100)')
            add_column_safely('subuser', 'hire_date', 'DATE')
            add_column_safely('subuser', 'phone', 'VARCHAR(20)')
            add_column_safely('subuser', 'last_login', 'DATETIME')
            add_column_safely('subuser', 'login_attempts', 'INTEGER DEFAULT 0', '0')
            add_column_safely('subuser', 'account_locked', 'BOOLEAN DEFAULT 0', '0')

            # Generate staff_ids for existing subusers
            try:
                subusers_without_staff_id = Subuser.query.filter(
                    (Subuser.staff_id == None) | (Subuser.staff_id == '')
                ).all()

                for subuser in subusers_without_staff_id:
                    if not subuser.staff_id:
                        subuser.staff_id = Subuser.generate_staff_id(subuser.parent_user_id)

                db.session.commit()
                logger.info(f"Generated staff IDs for {len(subusers_without_staff_id)} existing subusers")
            except Exception as e:
                logger.error(f"Error generating staff IDs for existing subusers: {str(e)}")
                db.session.rollback()

    except Exception as e:
        logger.error(f"Error during database migration: {str(e)}")
        db.session.rollback()


@app.route('/')
@login_required
def index():
    """Render the dashboard page"""
    return render_template('index.html')


@app.route('/inventory')
@login_required
def inventory():
    """Render the inventory management page"""
    return render_template('inventory.html')


@app.route('/margin')
@login_required
def margin():
    """Render the margin analysis page"""
    return render_template('margin.html')


@app.route('/item/<int:item_id>')
@login_required
def item_detail(item_id):
    """Render the item detail page"""
    # Get the item from database
    from models import Item
    item = Item.query.get_or_404(item_id)

    return render_template('item_detail.html', item=item.to_dict())


@app.route('/reports')
@login_required
def reports():
    """Render the reports page"""
    return render_template('reports.html')


@app.route('/settings')
@login_required
def settings():
    """Render the settings page"""
    return render_template('settings.html')


@app.route('/on-demand')
@login_required
def on_demand():
    """Render the on-demand products page"""
    return render_template('on_demand.html')


@app.route('/sales')
@login_required
def sales():
    """Render the sales management page"""
    return render_template('sales.html')


@app.route('/categories')
@login_required
def categories():
    """Render the categories management page"""
    return render_template('categories.html')


@app.route('/analytics')
@login_required
def analytics():
    """Render the predictive analytics page"""
    return render_template('analytics.html')


# API Routes
@app.route('/api/inventory', methods=['GET'])
@login_required
def get_inventory():
    """API endpoint to get all inventory items for the current user"""
    from models import Item

    try:
        logger.info("Getting inventory items...")

        # Get current user ID from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Start query filtered by user
        query = Item.query.filter(Item.user_id == user_id)

        # Optional filtering
        category = request.args.get('category')
        search_term = request.args.get('search', '').lower()
        min_stock = request.args.get('min_stock')
        max_stock = request.args.get('max_stock')

        logger.info(f"Filters - category: {category}, search: {search_term}, min_stock: {min_stock}, max_stock: {max_stock}")

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
                query = query.filter(Item.quantity >= min_stock)
            except ValueError:
                pass

        if max_stock:
            try:
                max_stock = int(max_stock)
                query = query.filter(Item.quantity <= max_stock)
            except ValueError:
                pass

        # Execute query and convert to dictionary
        items = query.all()
        logger.info(f"Found {len(items)} items for user {user_id}")

        items_dict = [item.to_dict() for item in items]
        logger.info(f"Returning {len(items_dict)} items as JSON")

        return jsonify(items_dict)

    except Exception as e:
        logger.error(f"Error getting inventory items: {str(e)}")
        return jsonify({"error": "Failed to get inventory items"}), 500


@app.route('/api/inventory', methods=['POST'])
def add_item():
    """API endpoint to add a new inventory item"""
    from models import Item
    import string
    import random

    try:
        item_data = request.json

        # Validate required fields
        required_fields = ['name', 'quantity']
        for field in required_fields:
            if field not in item_data:
                return jsonify({"error":
                                f"Missing required field: {field}"}), 400

        # Generate SKU if not provided
        if 'sku' not in item_data or not item_data['sku']:
            item_data['sku'] = Item.generate_sku(item_data["name"],
                                                 item_data.get("category", ""))

        # Handle price fields
        buying_price = float(item_data.get("buying_price", 0))
        selling_price_retail = float(item_data.get("selling_price_retail", 0))
        selling_price_wholesale = float(
            item_data.get("selling_price_wholesale", 0))

        # Use retail price as default price for backward compatibility
        price = selling_price_retail

        # Get current user ID
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Create new item
        new_item = Item(name=item_data["name"],
                        description=item_data.get("description", ""),
                        quantity=int(item_data["quantity"]),
                        buying_price=buying_price,
                        selling_price_retail=selling_price_retail,
                        selling_price_wholesale=selling_price_wholesale,
                        price=price,
                        sales_type=item_data.get("sales_type", "both"),
                        category=item_data.get("category", "Uncategorized"),
                        sku=item_data.get(
                            "sku",
                            f"SKU-{datetime.now().strftime('%Y%m%d%H%M%S')}"),
                        user_id=user_id)

        # Add to database
        db.session.add(new_item)
        db.session.commit()

        # Check if quantity is below threshold
        quantity = int(item_data["quantity"])
        from models import Setting

        # Get threshold
        low_stock_threshold = 10
        try:
            setting = Setting.query.filter_by(
                key='low_stock_threshold').first()
            if setting and setting.value:
                try:
                    low_stock_threshold = int(setting.value)
                except (ValueError, TypeError):
                    pass
        except Exception as e:
            logger.error(f"Error getting low stock threshold: {str(e)}")

        # Check if notifications are enabled
        notifications_enabled = False
        try:
            email_setting = Setting.query.filter_by(
                key='email_notifications_enabled').first()
            sms_setting = Setting.query.filter_by(
                key='sms_notifications_enabled').first()

            email_enabled = email_setting and email_setting.value.lower(
            ) == 'true'
            sms_enabled = sms_setting and sms_setting.value.lower() == 'true'

            notifications_enabled = email_enabled or sms_enabled
        except Exception as e:
            logger.error(f"Error checking notification settings: {str(e)}")

        # If item quantity is below threshold and notifications are enabled
        if quantity <= low_stock_threshold and notifications_enabled:
            try:
                # Import here to avoid circular imports
                from notifications.notification_manager import check_low_stock_and_notify

                # Run in a separate thread to avoid blocking
                import threading
                notification_thread = threading.Thread(
                    target=check_low_stock_and_notify,
                    args=(db, Item, Setting))
                notification_thread.daemon = True
                notification_thread.start()

                logger.info(
                    f"Low stock notification triggered for new item {new_item.name}"
                )
            except Exception as e:
                logger.error(
                    f"Error triggering low stock notification: {str(e)}")

        return jsonify(new_item.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error adding item: {str(e)}")
        return jsonify({"error": "Failed to add item"}), 500


@app.route('/api/inventory/<int:item_id>', methods=['GET'])
@login_required
def get_item(item_id):
    """API endpoint to get a specific inventory item"""
    from models import Item

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    item = Item.query.filter(Item.id == item_id, Item.user_id == user_id).first()

    if not item:
        return jsonify({"error": "Item not found"}), 404

    return jsonify(item.to_dict())


@app.route('/api/inventory/<int:item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    """API endpoint to update an inventory item"""
    from models import Item

    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        item_data = request.json
        item = Item.query.filter(Item.id == item_id, Item.user_id == user_id).first()

        if item is None:
            return jsonify({"error": "Item not found"}), 404

        # Handle price fields if present
        if "selling_price_retail" in item_data:
            item_data["selling_price_retail"] = float(
                item_data["selling_price_retail"])
            # Update the legacy price field to keep compatibility
            item_data["price"] = item_data["selling_price_retail"]

        if "selling_price_wholesale" in item_data:
            item_data["selling_price_wholesale"] = float(
                item_data["selling_price_wholesale"])

        if "buying_price" in item_data:
            item_data["buying_price"] = float(item_data["buying_price"])

        # Update the item with new data
        for key, value in item_data.items():
            if key not in ['id',
                           'created_at']:  # Don't allow changing these fields
                setattr(item, key, value)

        # Save to database
        db.session.commit()

        # Check if quantity was updated and is below threshold
        if 'quantity' in item_data:
            from models import Setting

            # Get threshold
            low_stock_threshold = 10
            try:
                setting = Setting.query.filter_by(
                    key='low_stock_threshold').first()
                if setting and setting.value:
                    try:
                        low_stock_threshold = int(setting.value)
                    except (ValueError, TypeError):
                        pass
            except Exception as e:
                logger.error(f"Error getting low stock threshold: {str(e)}")

            # Check if notifications are enabled
            notifications_enabled = False
            try:
                email_setting = Setting.query.filter_by(
                    key='email_notifications_enabled').first()
                sms_setting = Setting.query.filter_by(
                    key='sms_notifications_enabled').first()

                email_enabled = email_setting and email_setting.value.lower(
                ) == 'true'
                sms_enabled = sms_setting and sms_setting.value.lower() == 'true'

                notifications_enabled = email_enabled or sms_enabled
            except Exception as e:
                logger.error(f"Error checking notification settings: {str(e)}")

            # If item quantity is now below threshold and notifications are enabled
            if item.quantity <= low_stock_threshold and notifications_enabled:
                try:
                    # Import here to avoid circular imports
                    from notifications.notification_manager import check_low_stock_and_notify

                    # Run in a separate thread to avoid blocking
                    import threading
                    notification_thread = threading.Thread(
                        target=check_low_stock_and_notify,
                        args=(db, Item, Setting))
                    notification_thread.daemon = True
                    notification_thread.start()

                    logger.info(
                        f"Low stock notification triggered for item {item.name}"
                    )
                except Exception as e:
                    logger.error(
                        f"Error triggering low stock notification: {str(e)}")

        return jsonify(item.to_dict())

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating item: {str(e)}")
        return jsonify({"error": "Failed to update item"}), 500


@app.route('/api/inventory/<int:item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    """API endpoint to delete an inventory item"""
    from models import Item

    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        item = Item.query.filter(Item.id == item_id, Item.user_id == user_id).first()

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
def bulk_import_inventory():
    """API endpoint to handle bulk import of inventory items from CSV"""
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Only CSV files are supported"}), 400

    try:
        # Read CSV file
        stream = io.StringIO(file.stream.read().decode("UTF8"), newline=None)
        csv_data = csv.DictReader(stream)

        imported_count = 0
        errors = []

        for row in csv_data:
            try:
                # Generate SKU if not provided
                if not row.get('sku'):
                    row['sku'] = Item.generate_sku(row.get('name', ''),
                                                   row.get('category', ''))

                # Create new item
                new_item = Item(name=row.get('name'),
                                sku=row.get('sku'),
                                description=row.get('description', ''),
                                category=row.get('category', 'Uncategorized'),
                                quantity=int(row.get('quantity', 0)),
                                buying_price=float(row.get('buying_price', 0)),
                                selling_price_retail=float(
                                    row.get('selling_price_retail', 0)),
                                selling_price_wholesale=float(
                                    row.get('selling_price_wholesale', 0)),
                                sales_type=row.get('sales_type', 'both'))

                db.session.add(new_item)
                imported_count += 1

            except Exception as e:
                errors.append(f"Error in row {imported_count + 1}: {str(e)}")

        db.session.commit()

        return jsonify({
            "success": True,
            "imported_count": imported_count,
            "errors": errors
        })

    except Exception as e:
        db.session.rollback()
        return jsonify({"error": f"Import failed: {str(e)}"}), 500


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
            query = query.filter(Item.quantity >= min_stock)
        except ValueError:
            pass

    if max_stock:
        try:
            max_stock = int(max_stock)
            query = query.filter(Item.quantity <= max_stock)
        except ValueError:
            pass

    # Execute query and convert to dictionary
    items = [item.to_dict() for item in query.all()]
    return jsonify(items)


@app.route('/api/reports/stock-status', methods=['GET'])
@login_required
def stock_status_report():
    """API endpoint to get stock status report"""
    from models import Item
    from sqlalchemy import func

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    low_stock_threshold = int(request.args.get('low_stock_threshold', 10))

    # Get counts and sums for current user only
    item_count = db.session.query(func.count(Item.id)).filter(Item.user_id == user_id).scalar() or 0
    total_stock = db.session.query(func.sum(Item.quantity)).filter(Item.user_id == user_id).scalar() or 0

    # Get all items, low stock items, and out of stock items for current user
    all_items = Item.query.filter(Item.user_id == user_id).all()
    low_stock_items = Item.query.filter(
        Item.quantity <= low_stock_threshold, Item.user_id == user_id).all()
    out_of_stock_items = Item.query.filter(Item.quantity == 0, Item.user_id == user_id).all()

    # Calculate inventory value using selling price retail with fallback to price (for current user only)
    total_value_query = db.session.query(
        func.sum(Item.quantity * func.coalesce(Item.selling_price_retail, Item.price, 0))).filter(Item.user_id == user_id).scalar()
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

    user_id = session.get('user_id')
    if not user_id:
        return jsonify({"error": "Authentication required"}), 401

    # Group items by category for current user
    categories = {}

    # First get all distinct categories for current user
    category_list = db.session.query(
        func.coalesce(Item.category,
                      'Uncategorized').label('category')).filter(Item.user_id == user_id).distinct().all()

    # For each category, get the stats
    for cat in category_list:
        category = cat.category

        # Get items count in this category for current user
        count = db.session.query(func.count(Item.id)).filter(
            func.coalesce(Item.category, 'Uncategorized') == category,
            Item.user_id == user_id).scalar() or 0

        # Get total quantity for current user
        total_quantity = db.session.query(func.sum(Item.quantity)).filter(
            func.coalesce(Item.category, 'Uncategorized') == category,
            Item.user_id == user_id).scalar() or 0

        # Get total value based on retail selling price for current user
        total_value_query = db.session.query(
            func.sum(Item.quantity * Item.selling_price_retail)).filter(
                func.coalesce(Item.category, 'Uncategorized') == category,
                Item.user_id == user_id).scalar()
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
            item.category or 'Uncategorized', item.quantity, item.price,
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
def get_on_demand_products():
    """API endpoint to get all on-demand products"""
    from models import OnDemandProduct

    # Start query
    query = OnDemandProduct.query

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

        # Create new product
        new_product = OnDemandProduct(
            name=product_data["name"],
            description=product_data.get("description", ""),
            base_price=float(product_data["base_price"]),
            production_time=int(product_data.get("production_time", 0)),
            category=product_data.get("category", "Uncategorized"),
            materials=product_data.get("materials", ""),
            is_active=product_data.get("is_active", True))

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
def get_settings():
    """API endpoint to get all settings or settings by category"""
    from models import Setting

    category = request.args.get('category')

    # Start query
    query = Setting.query

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


@app.route('/logout')
def logout():
    """Logout route to clear session data"""
    # Clear session data
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('login'))


# Financial Statement Routes
@app.route('/finance')
@login_required
def finance():
    """Render the financial statement page"""
    return render_template('finance.html')


# Financial API Routes
@app.route('/api/finance/transactions', methods=['GET'])
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

    # Build query
    query = FinancialTransaction.query.filter(
        FinancialTransaction.date >= start_date, FinancialTransaction.date
        <= end_date)

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
def add_transaction():
    """API endpoint to add a new financial transaction"""
    from models import FinancialTransaction

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
        notes=data.get('notes'))

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
def update_transaction(transaction_id):
    """API endpoint to update a financial transaction"""
    from models import FinancialTransaction

    transaction = FinancialTransaction.query.get(transaction_id)
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

    transaction = FinancialTransaction.query.get(transaction_id)
    if not transaction:
        return jsonify({"error": "Transaction not found"}), 404

    try:
        db.session.delete(transaction)
        db.session.commit()
        return jsonify({"message": "Transaction deleted successfully"}), 200
    except Exception as e:
        db.session.rollback()
        return jsonify({"error":
                        f"Failed to delete transaction: {str(e)}"}), 500


@app.route('/api/finance/summaries/monthly', methods=['GET'])
def get_monthly_summary():
    """API endpoint to get monthly financial summaries"""
    from models import FinancialTransaction
    from datetime import datetime
    from sqlalchemy import func, extract

    # Get year parameter, default to current year
    year = request.args.get('year', datetime.utcnow().year, type=int)

    # Query to get monthly sums for income and expenses
    monthly_data = db.session.query(
        extract('month', FinancialTransaction.date).label('month'),
        func.sum(FinancialTransaction.amount).filter(
            FinancialTransaction.transaction_type == 'Income').label('income'),
        func.sum(FinancialTransaction.amount).filter(
            FinancialTransaction.transaction_type ==
            'Expense').label('expenses')).filter(
                extract('year', FinancialTransaction.date) == year).group_by(
                    extract('month', FinancialTransaction.date)).order_by(
                        extract('month', FinancialTransaction.date)).all()

    # Format the results
    results = []
    for month_num, income, expenses in monthly_data:
        income = income or 0
        expenses = expenses or 0
        profit = income - expenses

        month_name = datetime(year, int(month_num), 1).strftime('%B')

        results.append({
            'month': int(month_num),
            'month_name': month_name,
            'income': income,
            'expenses': expenses,
            'profit': profit
        })

    # Fill in missing months with zeros
    month_dict = {item['month']: item for item in results}
    all_months = []

    for month in range(1, 13):
        if month in month_dict:
            all_months.append(month_dict[month])
        else:
            month_name = datetime(year, month, 1).strftime('%B')
            all_months.append({
                'month': month,
                'month_name': month_name,
                'income': 0,
                'expenses': 0,
                'profit': 0
            })

    # Calculate yearly totals
    yearly_income = sum(item['income'] for item in all_months)
    yearly_expenses = sum(item['expenses'] for item in all_months)
    yearly_profit = yearly_income - yearly_expenses

    return jsonify({
        'year': year,
        'monthly_data': all_months,
        'yearly_summary': {
            'total_income': yearly_income,
            'total_expenses': yearly_expenses,
            'net_profit': yearly_profit
        }
    })


@app.route('/api/finance/categories', methods=['GET'])
def get_finance_categories():
    """API endpoint to get all transaction categories"""
    from models import TransactionCategory

    # Get all categories from the enum
    categories = [cat.value for cat in TransactionCategory]

    return jsonify(categories)


# Sales API Routes
@app.route('/api/sales/performance/top', methods=['GET'])
def get_top_selling_items():
    """API endpoint to get top selling items"""
    try:
        from sqlalchemy import func
        from models import Item, Sale, SaleItem

        # Get sales data from last 30 days
        days = request.args.get('days', 30, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Query to get top selling items
        top_items = db.session.query(
            Item,
            func.sum(SaleItem.quantity).label('total_quantity'),
            func.sum(SaleItem.total).label('total_revenue')).join(
                SaleItem).join(Sale).filter(
                    Sale.created_at >= cutoff_date).group_by(Item.id).order_by(
                        func.sum(SaleItem.quantity).desc()).limit(5).all()

        # Format response
        result = []
        for item, quantity, revenue in top_items:
            result.append({
                'id': item.id,
                'name': item.name,
                'category': item.category,
                'units_sold': int(quantity),
                'revenue': float(revenue)
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting top selling items: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sales/performance/slow', methods=['GET'])
def get_slow_moving_items():
    """API endpoint to get slow moving items"""
    try:
        from models import Item, Sale, SaleItem

        # Get items with no sales in last 30 days
        days = request.args.get('days', 30, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Subquery to get items that have had sales
        sold_items = db.session.query(SaleItem.item_id).join(Sale).filter(
            Sale.created_at >= cutoff_date).distinct().subquery()

        # Query to get items with no recent sales
        slow_items = Item.query.filter(
            ~Item.id.in_(sold_items), Item.quantity
            > 0).order_by(Item.quantity.desc()).limit(5).all()

        # Format response
        result = []
        for item in slow_items:
            # Calculate days in stock based on last sale or creation date
            last_sale = db.session.query(
                Sale.created_at).join(SaleItem).filter(
                    SaleItem.item_id == item.id).order_by(
                        Sale.created_at.desc()).first()

            reference_date = last_sale[0] if last_sale else item.created_at
            days_in_stock = (datetime.utcnow() - reference_date).days

            result.append({
                'id': item.id,
                'name': item.name,
                'category': item.category,
                'days_in_stock': days_in_stock,
                'quantity': item.quantity
            })

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting slow moving items: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales', methods=['POST'])
def create_sale():
    """API endpoint to create a new sale"""
    try:
        data = request.get_json()
        logger.info(f"Received sales data: {data}")

        if not data:
            logger.error("No data provided in sales request")
            return jsonify({'error': 'No data provided'}), 400

        # Validate required fields
        if not data.get('items') or len(data.get('items', [])) == 0:
            logger.error("No items provided in sales request")
            return jsonify({'error': 'No items provided'}), 400

        # Generate a unique invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        logger.info(f"Generated invoice number: {invoice_number}")

        # Extract customer data
        customer_data = data.get('customer', {})
        payment_data = data.get('payment', {})
        discount_data = data.get('discount', {})

        # Handle split payments
        split_payments = payment_data.get('split_payments', [])
        payment_method = payment_data.get('method', 'cash')

        # If split payments exist, use 'split' as payment method and store details
        if split_payments and len(split_payments) > 0:
            payment_method = 'split'
            payment_details = {
                'split_payments': split_payments,
                'total_methods': len(split_payments)
            }
        else:
            payment_details = payment_data.get('mobile_info', {})

        # Create new sale record
        new_sale = Sale(
            invoice_number=invoice_number,
            customer_name=customer_data.get('name', 'Walk-in Customer'),
            customer_phone=customer_data.get('phone', ''),
            sale_type=data.get('sale_type', 'retail'),
            subtotal=float(data.get('subtotal', 0)),
            discount_type=discount_data.get('type', 'none'),
            discount_value=float(discount_data.get('value', 0)),
            discount_amount=float(discount_data.get('amount', 0)),
            total=float(data.get('total', 0)),
            payment_method=payment_method,
            payment_details=json.dumps(payment_details),
            payment_amount=float(payment_data.get('amount', 0)),
            change_amount=float(payment_data.get('change', 0)),
            notes=data.get('notes', ''))

        db.session.add(new_sale)
        db.session.flush()  # Flush to get the sale ID
        logger.info(f"Created sale record with ID: {new_sale.id}")

        # Add sale items and update inventory
        items_processed = 0
        for item_data in data.get('items', []):
            try:
                # Get item from database if it exists
                item_id = item_data.get('id')
                item = Item.query.filter_by(id=item_id).first() if item_id else None

                if not item:
                    logger.warning(f"Item with ID {item_id} not found in database")
                    continue

                # Validate quantity
                quantity_sold = float(item_data.get('quantity', 1))
                if quantity_sold <= 0:
                    logger.warning(f"Invalid quantity {quantity_sold} for item {item.name}")
                    continue

                # Check if enough stock is available
                if item.quantity < quantity_sold:
                    logger.warning(f"Insufficient stock for item {item.name}. Available: {item.quantity}, Requested: {quantity_sold}")
                    # Continue anyway but log the issue

                # Create sale item record
                sale_item = SaleItem(
                    sale_id=new_sale.id,
                    item_id=item.id,
                    product_name=item_data.get('name', item.name),
                    product_sku=item_data.get('sku', item.sku),
                    price=float(item_data.get('price', 0)),
                    quantity=quantity_sold,
                    total=float(item_data.get('total', 0)))

                db.session.add(sale_item)

                # Update inventory quantity
                item.quantity = max(0, item.quantity - quantity_sold)
                logger.info(f"Updated stock for {item.name}: new quantity = {item.quantity}")

                items_processed += 1

            except Exception as item_error:
                logger.error(f"Error processing item {item_data}: {str(item_error)}")
                continue

        if items_processed == 0:
            db.session.rollback()
            logger.error("No items were successfully processed")
            return jsonify({'error': 'No valid items could be processed'}), 400

        # Commit the transaction
        db.session.commit()
        logger.info(f"Sale completed successfully. Processed {items_processed} items.")

        # Create financial transaction record for income
        try:
            from models import FinancialTransaction
            financial_transaction = FinancialTransaction(
                description=f"Sale - Invoice {invoice_number}",
                amount=float(data.get('total', 0)),
                transaction_type='Income',
                category='Sales',
                payment_method=payment_data.get('method', 'cash'),
                reference_id=invoice_number,
                date=datetime.utcnow().date()
            )
            db.session.add(financial_transaction)
            db.session.commit()
            logger.info("Financial transaction record created")
        except Exception as finance_error:
            logger.error(f"Error creating financial transaction: {str(finance_error)}")
            # Don't fail the sale if financial record creation fails

        response_data = {
            'success': True,
            'message': 'Sale created successfully',
            'sale': new_sale.to_dict(),
            'invoice_number': invoice_number,
            'items_processed': items_processed
        }

        logger.info(f"Returning success response: {response_data}")
        return jsonify(response_data)

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating sale: {str(e)}")
        return jsonify({'error': f'Failed to create sale: {str(e)}'}), 500


@app.route('/api/sales', methods=['GET'])
def get_sales():
    """API endpoint to get sales data with optional filtering"""
    try:
        # Get query parameters for filtering
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        customer = request.args.get('customer')
        payment_method = request.args.get('payment_method')

        # Build query
        query = Sale.query

        # Apply filters if provided
        if start_date:
            try:
                start_datetime = datetime.strptime(start_date, '%Y-%m-%d')
                query = query.filter(Sale.created_at >= start_datetime)
            except ValueError:
                pass

        if end_date:
            try:
                end_datetime = datetime.strptime(end_date, '%Y-%m-%d')
                # Add one day to include the entire end date
                end_datetime = end_datetime.replace(hour=23,
                                                    minute=59,
                                                    second=59)
                query = query.filter(Sale.created_at <= end_datetime)
            except ValueError:
                pass

        if customer:
            query = query.filter(Sale.customer_name.ilike(f'%{customer}%'))

        if payment_method:
            query = query.filter(Sale.payment_method == payment_method)

        # Order by created_at descending (most recent first)
        sales = query.order_by(Sale.created_at.desc()).all()

        # Convert to dictionary for JSON response
        return jsonify([sale.to_dict() for sale in sales])

    except Exception as e:
        logger.error(f"Error getting sales data: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/sales/<int:sale_id>', methods=['GET'])
def get_sale(sale_id):
    """API endpoint to get a specific sale by ID"""
    try:
        sale = Sale.query.get_or_404(sale_id)
        sale_data = sale.to_dict()

        # Add items to the sale data
        sale_items = SaleItem.query.filter_by(sale_id=sale_id).all()
        sale_data['items'] = [item.to_dict() for item in sale_items]

        return jsonify(sale_data)

    except Exception as e:
        logger.error(f"Error getting sale {sale_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Subusers API Routes


@app.route('/api/subusers', methods=['GET'])
@login_required
def get_subusers():
    """Get all subusers for the current user"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            logger.error("No user_id in session")
            return jsonify({'error': 'Authentication required'}), 401

        logger.info(f"Loading subusers for user_id: {user_id}")
        subusers = Subuser.query.filter_by(parent_user_id=user_id).all()

        result = [subuser.to_dict() for subuser in subusers]
        logger.info(f"Found {len(result)} subusers for user {user_id}")

        return jsonify(result)
    except Exception as e:
        logger.error(f"Error getting subusers: {str(e)}")
        return jsonify({'error': f'Failed to load subusers: {str(e)}'}), 500


@app.route('/api/subusers', methods=['POST'])
@login_required
def create_subuser():
    """Create a new subuser"""
    try:
        data = request.get_json()
        logger.info(f"Creating subuser with data: {data}")

        # Validate required fields
        if not data.get('name') or not data.get('email') or not data.get(
                'password'):
            return jsonify({'error':
                            'Name, email, and password are required'}), 400

        # Check if email already exists
        existing_user = User.query.filter_by(email=data['email']).first()
        existing_subuser = Subuser.query.filter_by(email=data['email']).first()

        if existing_user or existing_subuser:
            return jsonify({'error': 'Email already exists'}), 400

        # Generate unique staff ID
        staff_id = Subuser.generate_staff_id(session['user_id'])

        # Create new subuser
        subuser = Subuser(
            name=data['name'],
            email=data['email'],
            staff_id=staff_id,
            parent_user_id=session['user_id'],
            department=data.get('department', ''),
            position=data.get('position', ''),
            phone=data.get('phone', ''),
            hire_date=datetime.strptime(data['hire_date'], '%Y-%m-%d').date() if data.get('hire_date') else None,
            is_active=data.get('is_active', True)
        )
        subuser.set_password(data['password'])

        db.session.add(subuser)
        db.session.flush()  # Get the subuser ID

        logger.info(f"Created subuser with ID: {subuser.id} and Staff ID: {staff_id}")

        # Add permissions
        permissions = data.get('permissions', [])
        logger.info(f"Adding permissions: {permissions}")

        for permission in permissions:
            perm = SubuserPermission(subuser_id=subuser.id,
                                     permission=permission,
                                     granted=True)
            db.session.add(perm)

        db.session.commit()
        logger.info(f"Successfully created subuser: {subuser.name}")

        # Return the created subuser with permissions
        created_subuser = subuser.to_dict()
        logger.info(f"Returning subuser data: {created_subuser}")

        return jsonify({'success': True, 'subuser': created_subuser}), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating subuser: {str(e)}")
        return jsonify({'error': f'Failed to create subuser: {str(e)}'}), 500


@app.route('/api/subusers/<int:subuser_id>', methods=['PUT'])
@login_required
def update_subuser(subuser_id):
    """Update a subuser"""
    try:
        subuser = Subuser.query.filter_by(
            id=subuser_id, parent_user_id=session['user_id']).first()

        if not subuser:
            return jsonify({'error': 'Subuser not found'}), 404

        data = request.get_json()

        # Update basic info
        if 'name' in data:
            subuser.name = data['name']
        if 'email' in data:
            # Check email uniqueness
            existing = Subuser.query.filter(Subuser.email == data['email'],
                                            Subuser.id != subuser_id).first()
            if existing:
                return jsonify({'error': 'Email already exists'}), 400
            subuser.email = data['email']
        if 'password' in data and data['password']:
            subuser.set_password(data['password'])
        if 'is_active' in data:
            subuser.is_active = data['is_active']
        if 'department' in data:
            subuser.department = data['department']
        if 'position' in data:
            subuser.position = data['position']
        if 'phone' in data:
            subuser.phone = data['phone']
        if 'hire_date' in data and data['hire_date']:
            try:
                subuser.hire_date = datetime.strptime(data['hire_date'], '%Y-%m-%d').date()
            except ValueError:
                pass  # Skip invalid date formats
        if 'account_locked' in data:
            subuser.account_locked = data['account_locked']

        # Update permissions
        if 'permissions' in data:
            # Remove all existing permissions
            SubuserPermission.query.filter_by(subuser_id=subuser.id).delete()

            # Add new permissions
            for permission in data['permissions']:
                perm = SubuserPermission(subuser_id=subuser.id,
                                         permission=permission,
                                         granted=True)
                db.session.add(perm)

        subuser.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({'success': True, 'subuser': subuser.to_dict()})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating subuser: {str(e)}")
        return jsonify({'error': 'Failed to update subuser'}), 500


@app.route('/api/subusers/<int:subuser_id>', methods=['DELETE'])
@login_required
def delete_subuser(subuser_id):
    """Delete a subuser"""
    try:
        subuser = Subuser.query.filter_by(
            id=subuser_id, parent_user_id=session['user_id']).first()

        if not subuser:
            return jsonify({'error': 'Subuser not found'}), 404

        db.session.delete(subuser)
        db.session.commit()

        return jsonify({'success': True})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting subuser: {str(e)}")
        return jsonify({'error': 'Failed to delete subuser'}), 500


@app.route('/api/subusers/permissions', methods=['GET'])
@login_required
def get_available_permissions():
    """Get all available permissions for subusers"""
    try:
        # Define available permissions and their descriptions
        permissions_data = {
            'view_inventory': 'View Inventory',
            'edit_inventory': 'Edit Inventory Items',
            'delete_inventory': 'Delete Inventory Items',
            'view_sales': 'View Sales Data',
            'create_sales': 'Create Sales Records',
            'view_reports': 'View Reports',
            'export_data': 'Export Data',
            'manage_categories': 'Manage Categories',
            'view_financial': 'View Financial Data',
            'edit_financial': 'Edit Financial Records',
            'manage_settings': 'Manage Settings',
            'manage_users': 'Manage Users'
        }

        descriptions = {
            'view_inventory': 'Can view inventory items and stock levels',
            'edit_inventory': 'Can add, edit, and update inventory items',
            'delete_inventory': 'Can delete inventory items',
            'view_sales': 'Can view sales transactions and history',
            'create_sales': 'Can create new sales transactions',
            'view_reports': 'Can view and generate reports',
            'export_data': 'Can export data to various formats',
            'manage_categories': 'Can create and manage product categories',
            'view_financial': 'Can view financial data and statements',
            'edit_financial': 'Can edit and manage financial records',
            'manage_settings': 'Can modify system settings',
            'manage_users': 'Can manage team members and permissions'
        }

        result = {
            'success': True,
            'permissions': list(permissions_data.keys()),
            'descriptions': descriptions
        }

        logger.info(f"Returning permissions data: {result}")
        return jsonify(result)

    except Exception as e:
        logger.error(f"Error getting permissions: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'Failed to load permissions',
            'permissions': [],
            'descriptions': {}
        }), 500


# Categories API Routes
@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    """API endpoint to get all categories with subcategories"""
    try:
        categories = Category.query.filter_by(is_active=True).order_by(
            Category.name).all()
        return jsonify([category.to_dict() for category in categories])
    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/categories', methods=['POST'])
@login_required
def create_category():
    """API endpoint to create a new category"""
    try:
        data = request.json

        if not data or 'name' not in data:
            return jsonify({'error': 'Category name is required'}), 400

        # Check if category already exists
        existing_category = Category.query.filter_by(name=data['name']).first()
        if existing_category:
            return jsonify({'error': 'Category already exists'}), 400

        # Create new category
        new_category = Category(name=data['name'],
                                description=data.get('description', ''),
                                icon=data.get('icon', 'fas fa-box'),
                                color=data.get('color', '#007bff'))

        db.session.add(new_category)
        db.session.commit()

        return jsonify(new_category.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating category: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/categories/<int:category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    """API endpoint to update a category"""
    try:
        category = Category.query.get_or_404(category_id)
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update category fields
        if 'name' in data:
            # Check if new name conflicts with existing categories
            existing_category = Category.query.filter_by(
                name=data['name']).filter(Category.id != category_id).first()
            if existing_category:
                return jsonify({'error': 'Category name already exists'}), 400
            category.name = data['name']

        if 'description' in data:
            category.description = data['description']

        if 'icon' in data:
            category.icon = data['icon']

        if 'color' in data:
            category.color = data['color']

        if 'is_active' in data:
            category.is_active = data['is_active']

        category.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(category.to_dict())

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating category: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/categories/<int:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    """API endpoint to delete a category"""
    try:
        category = Category.query.get_or_404(category_id)

        # Check if category has items
        item_count = Item.query.filter_by(category=category.name).count()
        if item_count > 0:
            return jsonify({
                'error':
                f'Cannot delete category with {item_count} items. Move or delete items first.'
            }), 400

        # Soft delete - mark as inactive
        category.is_active = False
        category.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(
            {'message': f'Category "{category.name}" deleted successfully'})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting category: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/categories/<int:category_id>/subcategories', methods=['GET'])
@login_required
def get_subcategories(category_id):
    """API endpoint to get subcategories for a category"""
    try:
        category = Category.query.get_or_404(category_id)
        subcategories = Subcategory.query.filter_by(
            category_id=category_id,
            is_active=True).order_by(Subcategory.name).all()
        return jsonify(
            [subcategory.to_dict() for subcategory in subcategories])
    except Exception as e:
        logger.error(f"Error getting subcategories: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/categories/<int:category_id>/subcategories', methods=['POST'])
@login_required
def create_subcategory(category_id):
    """API endpoint to create a new subcategory"""
    try:
        category = Category.query.get_or_404(category_id)
        data = request.json

        if not data or 'name' not in data:
            return jsonify({'error': 'Subcategory name is required'}), 400

        # Check if subcategory already exists in this category
        existing_subcategory = Subcategory.query.filter_by(
            name=data['name'], category_id=category_id).first()
        if existing_subcategory:
            return jsonify(
                {'error': 'Subcategory already exists in this category'}), 400

        # Create new subcategory
        new_subcategory = Subcategory(name=data['name'],
                                      description=data.get('description', ''),
                                      category_id=category_id)

        db.session.add(new_subcategory)
        db.session.commit()

        return jsonify(new_subcategory.to_dict()), 201

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating subcategory: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/subcategories/<int:subcategory_id>', methods=['GET'])
@login_required
def get_subcategory(subcategory_id):
    """API endpoint to get a single subcategory"""
    try:
        subcategory = Subcategory.query.get_or_404(subcategory_id)
        return jsonify(subcategory.to_dict())
    except Exception as e:
        logger.error(f"Error getting subcategory: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/subcategories/<int:subcategory_id>', methods=['PUT'])
@login_required
def update_subcategory(subcategory_id):
    """API endpoint to update a subcategory"""
    try:
        subcategory = Subcategory.query.get_or_404(subcategory_id)
        data = request.json

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Update subcategory fields
        if 'name' in data:
            # Check if new name conflicts within the same category
            existing_subcategory = Subcategory.query.filter_by(
                name=data['name'], category_id=subcategory.category_id).filter(
                    Subcategory.id != subcategory_id).first()

            if existing_subcategory:
                return jsonify({
                    'error':
                    'Subcategory name already exists in this category'
                }), 400
            subcategory.name = data['name']

        if 'description' in data:
            subcategory.description = data['description']

        if 'is_active' in data:
            subcategory.is_active = data['is_active']

        subcategory.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify(subcategory.to_dict())

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating subcategory: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/subcategories/<int:subcategory_id>', methods=['DELETE'])
@login_required
def delete_subcategory(subcategory_id):
    """API endpoint to delete a subcategory"""
    try:
        subcategory = Subcategory.query.get_or_404(subcategory_id)

        # Check if subcategory has items
        item_count = Item.query.filter_by(subcategory=subcategory.name).count()
        if item_count > 0:
            return jsonify({
                'error':
                f'Cannot delete subcategory with {item_count} items. Move or delete items first.'
            }), 400

        # Soft delete - mark as inactive
        subcategory.is_active = False
        subcategory.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'message':
            f'Subcategory "{subcategory.name}" deleted successfully'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting subcategory: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/categories/<int:category_id>/items', methods=['GET'])
@login_required
def get_category_items(category_id):
    """API endpoint to get items in a category"""
    try:
        category = Category.query.get_or_404(category_id)
        items = Item.query.filter_by(category=category.name).all()
        return jsonify([item.to_dict() for item in items])
    except Exception as e:
        logger.error(f"Error getting category items: {str(e)}")
        return jsonify({'error': str(e)}), 500


# Notification API Routes
@app.route('/api/notifications/test', methods=['POST'])
def test_notifications():
    """API endpoint to test notifications for low stock items"""
    try:
        from notifications.notification_manager import check_low_stock_and_notify
        from models import Item, Setting

        # Call the notification manager to check low stock and send notifications
        result = check_low_stock_and_notify(db, Item, Setting)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error testing notifications: {str(e)}")
        return jsonify({
            'success': False,
            'errors': [f"Error testing notifications: {str(e)}"]
        }), 500


@app.route('/api/notifications/test-sms', methods=['POST'])
def test_sms():
    """API endpoint to test SMS notifications"""
    try:
        data = request.get_json()
        phone_number = data.get('phone_number')
        message = data.get('message', 'Test SMS from Inventory System')

        if not phone_number:
            return jsonify({'error': 'Phone number is required'}), 400

        from notifications.sms_service import send_sms
        result = send_sms(phone_number, message)

        return jsonify({'success': result})

    except Exception as e:
        logger.error(f"Error sending test SMS: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/api/notifications/check-stock', methods=['GET'])
def check_low_stock():
    """API endpoint to check for low stock items without sending notifications"""
    try:
        # Get threshold from query parameter or use default
        threshold = request.args.get('threshold', 10, type=int)

        # Get low stock items
        low_stock_items = Item.query.filter(Item.quantity <= threshold).all()

        # Return results
        return jsonify({
            'success':
            True,
            'low_stock_count':
            len(low_stock_items),
            'low_stock_items': [item.to_dict() for item in low_stock_items]
        })

    except Exception as e:
        logger.error(f"Error checking low stock: {str(e)}")
        return jsonify({
            'success': False,
            'errors': [f"Error checking low stock: {str(e)}"]
        }), 500


# Theme management
@app.route('/api/settings/appearance', methods=['POST'])
def update_appearance_settings():
    """API endpoint to update appearance settings"""
    from models import Setting

    try:
        data = request.json

        # Extract theme data
        theme = data.get('theme', 'tanzanite')
        items_per_page = data.get('itemsPerPage', '25')
        date_format = data.get('dateFormat', 'YYYY-MM-DD')

        # Update theme in session - this will apply immediately
        session['user_theme'] = theme

        # Save settings to database
        user_id = session.get('user_id')
        if user_id:
            # Save theme setting for this user
            theme_key = f"user_{user_id}_theme"
            theme_setting = Setting.query.filter_by(key=theme_key).first()

            if theme_setting:
                theme_setting.value = theme
                theme_setting.category = 'appearance'
            else:
                theme_setting = Setting(
                    key=theme_key,
                    value=theme,
                    description=f"Theme preference for user {user_id}",
                    category='appearance')
                db.session.add(theme_setting)

            # Save items per page setting
            items_key = f"user_{user_id}_items_per_page"
            items_setting = Setting.query.filter_by(key=items_key).first()

            if items_setting:
                items_setting.value = items_per_page
                items_setting.category = 'appearance'
            else:
                items_setting = Setting(
                    key=items_key,
                    value=items_per_page,
                    description=f"Items per page preference for user {user_id}",
                    category='appearance')
                db.session.add(items_setting)

            # Save date format setting
            date_key = f"user_{user_id}_date_format"
            date_setting = Setting.query.filter_by(key=date_key).first()

            if date_setting:
                date_setting.value = date_format
                date_setting.category = 'appearance'
            else:
                date_setting = Setting(
                    key=date_key,
                    value=date_format,
                    description=f"Date format preference for user {user_id}",
                    category='appearance')
                db.session.add(date_setting)

            db.session.commit()

        return jsonify({
            "success": True,
            "message": "Appearance settings updated successfully"
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating appearance settings: {str(e)}")
        return jsonify({"error": "Failed to update appearance settings"}), 500


# Predictive Analytics API Routes
@app.route('/api/analytics/demand-forecast/<int:item_id>', methods=['GET'])
@login_required
def forecast_item_demand(item_id):
    """API endpoint to forecast demand for a specific item"""
    try:
        from predictive_analytics import PredictiveStockManager
        from models import Item, Sale, SaleItem

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Verify item belongs to user
        item = Item.query.filter(Item.id == item_id, Item.user_id == user_id).first()
        if not item:
            return jsonify({"error": "Item not found"}), 404

        # Get forecast parameters
        forecast_days = request.args.get('days', 30, type=int)

        # Initialize predictive manager
        predictor = PredictiveStockManager(db, Item, Sale, SaleItem)

        # Get demand forecast
        forecast = predictor.forecast_demand(item_id, forecast_days)

        return jsonify(forecast)

    except Exception as e:
        logger.error(f"Error forecasting demand for item {item_id}: {str(e)}")
        return jsonify({"error": "Failed to forecast demand"}), 500


@app.route('/api/analytics/reorder-points/<int:item_id>', methods=['GET'])
@login_required
def get_reorder_point(item_id):
    """API endpoint to get reorder point recommendations for an item"""
    try:
        from predictive_analytics import PredictiveStockManager
        from models import Item, Sale, SaleItem

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Verify item belongs to user
        item = Item.query.filter(Item.id == item_id, Item.user_id == user_id).first()
        if not item:
            return jsonify({"error": "Item not found"}), 404

        # Get parameters
        lead_time_days = request.args.get('lead_time', 7, type=int)
        service_level = request.args.get('service_level', 0.95, type=float)

        # Initialize predictive manager
        predictor = PredictiveStockManager(db, Item, Sale, SaleItem)

        # Calculate reorder point
        reorder_data = predictor.calculate_reorder_point(item_id, lead_time_days, service_level)

        return jsonify(reorder_data)

    except Exception as e:
        logger.error(f"Error calculating reorder point for item {item_id}: {str(e)}")
        return jsonify({"error": "Failed to calculate reorder point"}), 500


@app.route('/api/analytics/purchase-recommendations', methods=['GET'])
@login_required
def get_purchase_recommendations():
    """API endpoint to get smart purchase recommendations"""
    try:
        from predictive_analytics import PredictiveStockManager
        from models import Item, Sale, SaleItem

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Initialize predictive manager
        predictor = PredictiveStockManager(db, Item, Sale, SaleItem)

        # Get purchase recommendations
        recommendations = predictor.get_purchase_recommendations(user_id)

        return jsonify({
            'success': True,
            'recommendations': recommendations,
            'total_recommendations': len(recommendations)
        })

    except Exception as e:
        logger.error(f"Error getting purchase recommendations: {str(e)}")
        return jsonify({"error": "Failed to get purchase recommendations"}), 500


@app.route('/api/analytics/abc-analysis', methods=['GET'])
@login_required
def get_abc_analysis():
    """API endpoint to perform ABC analysis on inventory"""
    try:
        from predictive_analytics import analyze_abc_classification
        from models import Item, Sale, SaleItem

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Perform ABC analysis
        abc_data = analyze_abc_classification(db, Item, Sale, SaleItem, user_id)

        return jsonify(abc_data)

    except Exception as e:
        logger.error(f"Error performing ABC analysis: {str(e)}")
        return jsonify({"error": "Failed to perform ABC analysis"}), 500


@app.route('/api/reports/profit-margin', methods=['GET'])
@login_required
def get_profit_margin_analysis():
    """API endpoint to get profit margin analysis by product/category"""
    try:
        from models import Item, Sale, SaleItem
        from sqlalchemy import func

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Get profit margin data
        margin_data = db.session.query(
            Item.id,
            Item.name,
            Item.category,
            Item.buying_price,
            Item.selling_price_retail,
            func.sum(SaleItem.quantity).label('units_sold'),
            func.sum(SaleItem.total).label('total_revenue'),
            func.sum(SaleItem.quantity * Item.buying_price).label('total_cost')
        ).outerjoin(
            SaleItem, Item.id == SaleItem.item_id
        ).filter(
            Item.user_id == user_id
        ).group_by(Item.id).all()

        # Calculate margins
        margin_analysis = []
        for item in margin_data:
            if item.selling_price_retail and item.buying_price:
                margin_amount = item.selling_price_retail - item.buying_price
                margin_percentage = (margin_amount / item.selling_price_retail) * 100

                total_revenue = item.total_revenue or 0
                total_cost = item.total_cost or 0
                total_profit = total_revenue - total_cost

                margin_analysis.append({
                    'item_id': item.id,
                    'item_name': item.name,
                    'category': item.category,
                    'buying_price': item.buying_price,
                    'selling_price': item.selling_price_retail,
                    'margin_amount': round(margin_amount, 2),
                    'margin_percentage': round(margin_percentage, 2),
                    'units_sold': item.units_sold or 0,
                    'total_revenue': round(total_revenue, 2),
                    'total_cost': round(total_cost, 2),
                    'total_profit': round(total_profit, 2)
                })

        # Sort by margin percentage
        margin_analysis.sort(key=lambda x: x['margin_percentage'], reverse=True)

        # Category summary
        category_margins = {}
        for item in margin_analysis:
            category = item['category'] or 'Uncategorized'
            if category not in category_margins:
                category_margins[category] = {
                    'total_revenue': 0,
                    'total_cost': 0,
                    'total_profit': 0,
                    'item_count': 0
                }

            category_margins[category]['total_revenue'] += item['total_revenue']
            category_margins[category]['total_cost'] += item['total_cost']
            category_margins[category]['total_profit'] += item['total_profit']
            category_margins[category]['item_count'] += 1

        # Calculate category margin percentages
        for category, data in category_margins.items():
            if data['total_revenue'] > 0:
                data['margin_percentage'] = round((data['total_profit'] / data['total_revenue']) * 100, 2)
            else:
                data['margin_percentage'] = 0

        return jsonify({
            'success': True,
            'item_margins': margin_analysis,
            'category_margins': category_margins
        })

    except Exception as e:
        logger.error(f"Error getting profit margin analysis: {str(e)}")
        return jsonify({"error": "Failed to get profit margin analysis"}), 500


@app.route('/api/reports/inventory-turnover', methods=['GET'])
@login_required
def get_inventory_turnover():
    """API endpoint to calculate inventory turnover ratios"""
    try:
        from models import Item, Sale, SaleItem
        from sqlalchemy import func

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        # Get period from query params (default to 365 days)
        days = request.args.get('days', 365, type=int)
        cutoff_date = datetime.utcnow() - timedelta(days=days)

        # Calculate turnover for each item
        turnover_data = db.session.query(
            Item.id,
            Item.name,
            Item.category,
            Item.quantity,
            Item.buying_price,
            func.sum(SaleItem.quantity).label('units_sold'),
            func.avg(Item.quantity).label('avg_inventory')
        ).outerjoin(
            SaleItem, Item.id == SaleItem.item_id
        ).outerjoin(
            Sale, SaleItem.sale_id == Sale.id
        ).filter(
            Item.user_id == user_id,
            Sale.created_at >= cutoff_date
        ).group_by(Item.id).all()

        turnover_analysis = []
        for item in turnover_data:
            units_sold = item.units_sold or 0
            current_inventory = item.quantity or 0
            avg_inventory = max(current_inventory, 1)  # Avoid division by zero

            # Calculate turnover ratio
            turnover_ratio = units_sold / avg_inventory if avg_inventory > 0 else 0

            # Calculate days of inventory
            days_of_inventory = days / turnover_ratio if turnover_ratio > 0 else float('inf')

            # Classify turnover speed
            if turnover_ratio >= 12:
                turnover_speed = 'Fast'
            elif turnover_ratio >= 6:
                turnover_speed = 'Medium'
            elif turnover_ratio >= 3:
                turnover_speed = 'Slow'
            else:
                turnover_speed = 'Very Slow'

            turnover_analysis.append({
                'item_id': item.id,
                'item_name': item.name,
                'category': item.category,
                'current_inventory': current_inventory,
                'units_sold': units_sold,
                'turnover_ratio': round(turnover_ratio, 2),
                'days_of_inventory': round(days_of_inventory, 1) if days_of_inventory != float('inf') else 'N/A',
                'turnover_speed': turnover_speed,
                'inventory_value': current_inventory * (item.buying_price or 0)
            })

        # Sort by turnover ratio
        turnover_analysis.sort(key=lambda x: x['turnover_ratio'], reverse=True)

        return jsonify({
            'success': True,
            'period_days': days,
            'turnover_analysis': turnover_analysis
        })

    except Exception as e:
        logger.error(f"Error calculating inventory turnover: {str(e)}")
        return jsonify({"error": "Failed to calculate inventory turnover"}), 500


# Automation Management API Routes
@app.route('/api/automation/purchase-orders', methods=['POST'])
@login_required
def generate_purchase_orders():
    """Generate automatic purchase orders"""
    try:
        from automation_manager import AutomationManager

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        automation = AutomationManager()
        result = automation.generate_auto_purchase_orders(user_id)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error generating purchase orders: {str(e)}")
        return jsonify({"error": "Failed to generate purchase orders"}), 500


@app.route('/api/automation/price-updates', methods=['POST'])
@login_required
def update_supplier_prices():
    """Update prices from suppliers"""
    try:
        from automation_manager import AutomationManager

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        automation = AutomationManager()
        result = automation.update_prices_from_suppliers(user_id)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error updating supplier prices: {str(e)}")
        return jsonify({"error": "Failed to update prices"}), 500


@app.route('/api/automation/scheduled-reports', methods=['POST'])
@login_required
def generate_scheduled_report():
    """Generate and send scheduled report"""
    try:
        from automation_manager import AutomationManager

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "Authentication required"}), 401

        data = request.json
        report_type = data.get('report_type', 'daily')

        automation = AutomationManager()
        result = automation.generate_scheduled_reports(user_id, report_type)

        return jsonify(result)

    except Exception as e:
        logger.error(f"Error generating scheduled report: {str(e)}")
        return jsonify({"error": "Failed to generate report"}), 500


@app.route('/api/notifications/whatsapp', methods=['POST'])
@login_required
def send_whatsapp_notification():
    """Send WhatsApp notification"""
    try:
        from notifications.sms_service import send_whatsapp_message

        data = request.json
        phone_number = data.get('phone_number')
        message = data.get('message')
        template_name = data.get('template_name')

        if not phone_number or not message:
            return jsonify({"error": "Phone number and message are required"}), 400

        success = send_whatsapp_message(phone_number, message, template_name)

        return jsonify({
            "success": success,
            "message": "WhatsApp message sent successfully" if success else "Failed to send WhatsApp message"
        })

    except Exception as e:
        logger.error(f"Error sending WhatsApp notification: {str(e)}")
        return jsonify({"error": "Failed to send WhatsApp notification"}), 500


# Customer Management API Routes
@app.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    """API endpoint to get all customers"""
    try:
        # For now, extract customers from sales data since we don't have separate customer table yet
        from models import Sale
        from sqlalchemy import func, distinct

        # Get unique customers from sales
        customers = db.session.query(
            Sale.customer_name,
            Sale.customer_phone,
            func.count(Sale.id).label('total_purchases'),
            func.sum(Sale.total).label('total_spent'),
            func.max(Sale.created_at).label('last_purchase_date'),
            func.min(Sale.created_at).label('first_purchase_date')
        ).filter(
            Sale.customer_name != 'Walk-in Customer'
        ).group_by(
            Sale.customer_name, Sale.customer_phone
        ).order_by(
            func.sum(Sale.total).desc()
        ).all()

        customer_list = []
        for customer in customers:
            # Calculate customer metrics
            total_spent = customer.total_spent or 0
            total_purchases = customer.total_purchases or 0
            avg_order_value = total_spent / total_purchases if total_purchases > 0 else 0

            # Calculate customer lifetime (days)
            if customer.first_purchase_date and customer.last_purchase_date:
                lifetime_days = (customer.last_purchase_date - customer.first_purchase_date).days + 1
            else:
                lifetime_days = 1

            # Purchase frequency (purchases per month)
            purchase_frequency = (total_purchases * 30) / lifetime_days if lifetime_days > 0 else 0

            customer_list.append({
                'name': customer.customer_name,
                'phone': customer.customer_phone,
                'total_purchases': total_purchases,
                'total_spent': round(total_spent, 2),
                'average_order_value': round(avg_order_value, 2),
                'purchase_frequency': round(purchase_frequency, 2),
                'last_purchase_date': customer.last_purchase_date.isoformat() if customer.last_purchase_date else None,
                'first_purchase_date': customer.first_purchase_date.isoformat() if customer.first_purchase_date else None,
                'lifetime_days': lifetime_days
            })

        return jsonify({
            'success': True,
            'customers': customer_list,
            'total_customers': len(customer_list)
        })

    except Exception as e:
        logger.error(f"Error getting customers: {str(e)}")
        return jsonify({"error": "Failed to get customers"}), 500


@app.route('/api/customers/<customer_name>/analytics', methods=['GET'])
@login_required
def get_customer_analytics(customer_name):
    """API endpoint to get detailed analytics for a specific customer"""
    try:
        from customer_management import calculate_customer_metrics

        # Get customer analytics
        analytics = calculate_customer_metrics(db, customer_name)

        return jsonify({
            'success': True,
            'customer_name': customer_name,
            'analytics': analytics
        })

    except Exception as e:
        logger.error(f"Error getting customer analytics for {customer_name}: {str(e)}")
        return jsonify({"error": "Failed to get customer analytics"}), 500


# Debug endpoint to check database
@app.route('/api/debug/database', methods=['GET'])
@login_required
def debug_database():
    """Debug endpoint to check database status"""
    try:
        from models import Item

        # Count total items
        total_items = Item.query.count()

        # Get sample items
        sample_items = Item.query.limit(5).all()

        # Calculate total stock
        total_stock = db.session.query(db.func.sum(Item.quantity)).scalar() or 0

        # Calculate inventory value
        total_value = db.session.query(
            db.func.sum(Item.quantity * db.func.coalesce(Item.selling_price_retail, Item.price, 0))
        ).scalar() or 0

        return jsonify({
            'success': True,
            'database_status': 'connected',
            'total_items': total_items,
            'total_stock': total_stock,
            'total_value': float(total_value),
            'sample_items': [item.to_dict() for item in sample_items]
        })

    except Exception as e:
        logger.error(f"Database debug error: {str(e)}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


# Subuser Authentication Routes
# Subuser Authentication Routes
@app.route('/api/auth/subuser/login', methods=['POST'])
def subuser_login():
    """API endpoint for subuser login"""
    try:
        data = request.json

        if not data or not data.get('email') or not data.get('password'):
            return jsonify({'error': 'Email and password are required'}), 400

        # Find subuser by email
        subuser = Subuser.query.filter_by(email=data['email']).first()

        if not subuser:
            return jsonify({'error': 'Invalid credentials'}), 401

        # Check if account is locked
        if subuser.account_locked:
            return jsonify({'error': 'Account is locked. Contact administrator.'}), 403

        # Check if account is active
        if not subuser.is_active:
            return jsonify({'error': 'Account is deactivated. Contact administrator.'}), 403

        # Verify password
        if not subuser.check_password(data['password']):
            # Increment login attempts
            subuser.login_attempts = (subuser.login_attempts or 0) + 1

            # Lock account after 5 failed attempts
            if subuser.login_attempts >= 5:
                subuser.account_locked = True
                logger.warning(f"Account locked for subuser {subuser.email} after {subuser.login_attempts} failed attempts")

            db.session.commit()
            return jsonify({'error': 'Invalid credentials'}), 401

        # Reset login attempts on successful login
        subuser.login_attempts = 0
        subuser.last_login = datetime.utcnow()
        db.session.commit()

        # Set session data for subuser
        session['subuser_id'] = subuser.id
        session['staff_id'] = subuser.staff_id
        session['parent_user_id'] = subuser.parent_user_id
        session['email'] = subuser.email
        session['is_subuser'] = True
        session['user_type'] = 'subuser'
        session.permanent = data.get('remember', False)

        logger.info(f"Subuser {subuser.email} (Staff ID: {subuser.staff_id}) logged in successfully")

        return jsonify({
            'success': True,
            'subuser': subuser.to_dict(),
            'message': f'Welcome back, {subuser.name}!'
        })

    except Exception as e:
        logger.error(f"Error during subuser login: {str(e)}")
        return jsonify({'error': 'Login failed'}), 500

@app.route('/api/auth/subuser/logout', methods=['POST'])
def subuser_logout():
    """API endpoint for subuser logout"""
    try:
        # Clear subuser session data
        subuser_keys = ['subuser_id', 'staff_id', 'parent_user_id', 'is_subuser', 'user_type']
        for key in subuser_keys:
            session.pop(key, None)

        return jsonify({'success': True, 'message': 'Logged out successfully'})

    except Exception as e:
        logger.error(f"Error during subuser logout: {str(e)}")
        return jsonify({'error': 'Logout failed'}), 500

@app.route('/api/auth/subuser/profile', methods=['GET'])
def get_subuser_profile():
    """API endpoint to get current subuser profile"""
    try:
        subuser_id = session.get('subuser_id')

        if not subuser_id:
            return jsonify({'error': 'Not authenticated as subuser'}), 401

        subuser = Subuser.query.get(subuser_id)
        if not subuser:
            return jsonify({'error': 'Subuser not found'}), 404

        return jsonify({
            'success': True,
            'subuser': subuser.to_dict(),
            'permissions': [perm.permission for perm in subuser.permissions if perm.granted]
        })

    except Exception as e:
        logger.error(f"Error getting subuser profile: {str(e)}")
        return jsonify({'error': 'Failed to get profile'}), 500

@app.route('/api/auth/subuser/update-profile', methods=['PUT'])
def update_subuser_profile():
    """API endpoint for subuser to update their own profile"""
    try:
        subuser_id = session.get('subuser_id')

        if not subuser_id:
            return jsonify({'error': 'Not authenticated as subuser'}), 401

        subuser = Subuser.query.get(subuser_id)
        if not subuser:
            return jsonify({'error': 'Subuser not found'}), 404

        data = request.json

        # Allow subuser to update limited fields
        if 'name' in data:
            subuser.name = data['name']
        if 'phone' in data:
            subuser.phone = data['phone']
        # Note: Email and other sensitive fields should only be updated by admin

        subuser.updated_at = datetime.utcnow()
        db.session.commit()

        return jsonify({
            'success': True,
            'subuser': subuser.to_dict(),
            'message': 'Profile updated successfully'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating subuser profile: {str(e)}")
        return jsonify({'error': 'Failed to update profile'}), 500

@app.route('/api/auth/subuser/change-password', methods=['POST'])
def subuser_change_password():
    """API endpoint for subuser to change their password"""
    try:
        subuser_id = session.get('subuser_id')

        if not subuser_id:
            return jsonify({'error': 'Not authenticated as subuser'}), 401

        data = request.json

        if not data.get('current_password') or not data.get('new_password'):
            return jsonify({'error': 'Current password and new password are required'}), 400

        subuser = Subuser.query.get(subuser_id)
        if not subuser:
            return jsonify({'error': 'Subuser not found'}), 404

        # Verify current password
        if not subuser.check_password(data['current_password']):
            return jsonify({'error': 'Current password is incorrect'}), 400

        # Validate new password
        if len(data['new_password']) < 6:
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400

        # Update password
        subuser.set_password(data['new_password'])
        subuser.updated_at = datetime.utcnow()
        db.session.commit()

        logger.info(f"Subuser {subuser.email} (Staff ID: {subuser.staff_id}) changed password")

        return jsonify({
            'success': True,
            'message': 'Password changed successfully'
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error changing subuser password: {str(e)}")
        return jsonify({'error': 'Failed to change password'}), 500

@app.route('/api/categories/<int:category_id>/subcategories', methods=['GET'])
@login_required
def get_subcategories(category_id):
    """API endpoint to get subcategories for a category"""
    try:
        category = Category.query.get_or_404(category_id)
        subcategories = Subcategory.query.filter_by(
            category_id=category_id,
            is_active=True).order_by(Subcategory.name).all()
        return jsonify(
            [subcategory.to_dict() for subcategory in subcategories])
    except Exception as e:
        logger.error(f"Error getting subcategories: {str(e)}")
        return jsonify({'error': str(e)}), 500