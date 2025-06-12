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


# API Routes
@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """API endpoint to get all inventory items"""
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
                            f"SKU-{datetime.now().strftime('%Y%m%d%H%M%S')}"))

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
def get_item(item_id):
    """API endpoint to get a specific inventory item"""
    from models import Item

    item = Item.query.get(item_id)

    if not item:
        return jsonify({"error": "Item not found"}), 404

    return jsonify(item.to_dict())


@app.route('/api/inventory/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """API endpoint to update an inventory item"""
    from models import Item

    try:
        item_data = request.json
        item = Item.query.get(item_id)

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
def stock_status_report():
    """API endpoint to get stock status report"""
    from models import Item
    from sqlalchemy import func

    low_stock_threshold = int(request.args.get('low_stock_threshold', 10))

    # Get counts and sums
    item_count = db.session.query(func.count(Item.id)).scalar() or 0
    total_stock = db.session.query(func.sum(Item.quantity)).scalar() or 0

    # Get all items, low stock items, and out of stock items
    all_items = Item.query.all()
    low_stock_items = Item.query.filter(
        Item.quantity <= low_stock_threshold).all()
    out_of_stock_items = Item.query.filter(Item.quantity == 0).all()

    # Calculate inventory value using selling price retail with fallback to price
    total_value_query = db.session.query(
        func.sum(Item.quantity * func.coalesce(Item.selling_price_retail, Item.price, 0))).scalar()
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
def category_breakdown_report():
    """API endpoint to get category breakdown report"""
    from models import Item
    from sqlalchemy import func

    # Group items by category
    categories = {}

    # First get all distinct categories
    category_list = db.session.query(
        func.coalesce(Item.category,
                      'Uncategorized').label('category')).distinct().all()

    # For each category, get the stats
    for cat in category_list:
        category = cat.category

        # Get items count in this category
        count = db.session.query(func.count(Item.id)).filter(
            func.coalesce(Item.category, 'Uncategorized') ==
            category).scalar() or 0

        # Get total quantity
        total_quantity = db.session.query(func.sum(Item.quantity)).filter(
            func.coalesce(Item.category, 'Uncategorized') ==
            category).scalar() or 0

        # Get total value based on retail selling price
        total_value_query = db.session.query(
            func.sum(Item.quantity * Item.selling_price_retail)).filter(
                func.coalesce(Item.category, 'Uncategorized') ==
                category).scalar()
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

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        # Generate a unique invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"

        # Create new sale record
        new_sale = Sale(invoice_number=invoice_number,
                        customer_name=data.get('customer',
                                               {}).get('name',
                                                       'Walk-in Customer'),
                        customer_phone=data.get('customer',
                                                {}).get('phone', ''),
                        sale_type=data.get('sale_type', 'retail'),
                        subtotal=data.get('subtotal', 0),
                        discount_type=data.get('discount',
                                               {}).get('type', 'none'),
                        discount_value=data.get('discount',
                                                {}).get('value', 0),
                        discount_amount=data.get('discount',
                                                 {}).get('amount', 0),
                        total=data.get('total', 0),
                        payment_method=data.get('payment',
                                                {}).get('method', 'cash'),
                        payment_details=json.dumps(
                            data.get('payment', {}).get('mobile_info', {})),
                        payment_amount=data.get('payment',
                                                {}).get('amount', 0),
                        change_amount=data.get('payment', {}).get('change', 0),
                        notes=data.get('notes', ''))

        db.session.add(new_sale)
        db.session.flush()  # Flush to get the sale ID

        # Add sale items
        for item_data in data.get('items', []):
            # Get item from database if it exists
            item = Item.query.filter_by(id=item_data.get('id')).first()

            # Create sale item record
            sale_item = SaleItem(sale_id=new_sale.id,
                                 item_id=item.id if item else None,
                                 product_name=item_data.get(
                                     'name', 'Unknown Product'),
                                 product_sku=item_data.get('sku', ''),
                                 price=item_data.get('price', 0),
                                 quantity=item_data.get('quantity', 1),
                                 total=item_data.get('total', 0))

            db.session.add(sale_item)

            # Update inventory quantity if item exists
            if item:
                item.quantity = max(
                    0, item.quantity - item_data.get('quantity', 1))

        db.session.commit()

        return jsonify({
            'success': True,
            'message': 'Sale created successfully',
            'sale': new_sale.to_dict()
        })

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating sale: {str(e)}")
        return jsonify({'error': str(e)}), 500


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
        subusers = Subuser.query.filter_by(
            parent_user_id=session['user_id']).all()
        return jsonify([subuser.to_dict() for subuser in subusers])
    except Exception as e:
        logger.error(f"Error getting subusers: {str(e)}")
        return jsonify({'error': 'Failed to load subusers'}), 500


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

        # Create new subuser
        subuser = Subuser(name=data['name'],
                          email=data['email'],
                          parent_user_id=session['user_id'],
                          is_active=data.get('is_active', True))
        subuser.set_password(data['password'])

        db.session.add(subuser)
        db.session.flush()  # Get the subuser ID

        logger.info(f"Created subuser with ID: {subuser.id}")

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


# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    """Handle login form"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('index'))

    # Render login template
    firebase_config = {
        'apiKey': app.config['FIREBASE_API_KEY'],
        'projectId': app.config['FIREBASE_PROJECT_ID'],
        'appId': app.config['FIREBASE_APP_ID'],
        'authDomain': f"{app.config['FIREBASE_PROJECT_ID']}.firebaseapp.com",
    }

    return render_template('login.html', firebase_config=firebase_config)


@app.route('/register', methods=['GET', 'POST'])
def register():
    """Handle the registration page"""
    # If user is already logged in, redirect to dashboard
    if 'user_id' in session:
        return redirect(url_for('index'))

    # Render registration template with Firebase config
    firebase_config = {
        'apiKey': app.config['FIREBASE_API_KEY'],
        'projectId': app.config['FIREBASE_PROJECT_ID'],
        'appId': app.config['FIREBASE_APP_ID'],
        'authDomain': f"{app.config['FIREBASE_PROJECT_ID']}.firebaseapp.com",
    }

    return render_template('register.html', firebase_config=firebase_config)


@app.route('/api/auth/session', methods=['POST'])
def create_session():
    """Create a session for authenticated user using Firebase token"""
    try:
        data = request.json

        logger.info("Session creation request received")

        if not data or 'idToken' not in data:
            logger.warning("Missing idToken in session creation request")
            return jsonify({"error": "Firebase ID token is required"}), 400

        # Verify the Firebase token
        logger.info("Verifying Firebase token...")
        user_data = verify_firebase_token(data['idToken'])

        if not user_data:
            logger.warning("Firebase token verification failed")
            return jsonify({"error": "Invalid or expired token"}), 401

        logger.info(
            f"Firebase token verified successfully for email: {user_data.get('email')}"
        )

        # Create or update user in database
        logger.info("Creating or updating user in database...")
        user = create_or_update_user(user_data)

        if not user:
            logger.error("Failed to create or update user record")
            return jsonify({"error": "Failed to create user record"}), 500

        logger.info(
            f"User record updated/created successfully for ID: {user.id}")

        # Update last login time
        user.last_login = datetime.utcnow()
        db.session.commit()

        # Set session data
        logger.info("Setting session data...")
        session['user_id'] = user.id
        session['email'] = user.email
        session['is_admin'] = user.is_admin
        session.permanent = data.get('remember', False)

        # Load user theme preference
        from models import Setting
        theme_key = f"user_{user.id}_theme"
        theme_setting = Setting.query.filter_by(key=theme_key).first()
        if theme_setting:
            session['user_theme'] = theme_setting.value
            logger.info(f"Loaded user theme: {theme_setting.value}")
        else:
            session['user_theme'] = 'tanzanite'  # Default theme
            logger.info("Using default theme: tanzanite")

        logger.info("Session created successfully")
        return jsonify({"success": True, "user": user.to_dict()})

    except Exception as e:
        logger.error(f"Error creating session with Firebase: {str(e)}")
        return jsonify({"error": f"Failed to create session: {str(e)}"}), 500


@app.route('/api/auth/register', methods=['POST'])
def register_user():
    """Register a new user via Firebase API"""
    try:
        data = request.json

        if not data or 'idToken' not in data:
            return jsonify({"error": "Firebase ID token is required"}), 400

        # Additional user data from registration form
        extra_data = {}
        if 'username' in data:
            extra_data['username'] = data['username']
        if 'firstName' in data:
            extra_data['first_name'] = data['firstName']
        if 'lastName' in data:
            extra_data['last_name'] = data['lastName']
        if 'shopName' in data:
            extra_data['shop_name'] = data['shopName']
        if 'productCategories' in data:
            extra_data['product_categories'] = data['productCategories']

        # Verify the Firebase token
        user_data = verify_firebase_token(data['idToken'])
        if not user_data:
            return jsonify({"error": "Invalid or expired token"}), 401

        # Create or update user in database with extra profile data
        user = create_or_update_user(user_data, extra_data)

        if not user:
            return jsonify({"error": "Failed to create user record"}), 500

        # Set session data
        session['user_id'] = user.id
        session['email'] = user.email
        session['is_admin'] = user.is_admin
        session.permanent = data.get('remember', False)

        # Update last login time
        user.last_login = datetime.utcnow()
        db.session.commit()

        return jsonify({"success": True, "user": user.to_dict()})

    except Exception as e:
        logger.error(f"Error registering user: {str(e)}")
        return jsonify({"error": "Failed to register user"}), 500


# This logout route is now unified with the existing one at line 770


@app.route('/account')
def account():
    """Render the user account page"""
    from auth_service import login_required

    @login_required
    def protected_account():
        from models import User
        user = User.query.get(session['user_id'])
        if not user:
            session.clear()
            return redirect(url_for('login'))

        return render_template('account.html', user=user)

    return protected_account()


@app.route('/admin/users')
@login_required
def admin_users():
    """Render the user management page (admin only)"""
    # Check if current user is admin
    current_user = User.query.get(session['user_id'])
    if not current_user or not current_user.is_admin:
        flash('Admin access required', 'danger')
        return redirect(url_for('index'))

    users = User.query.all()
    return render_template('admin_users.html', users=users)


@app.route('/api/auth/users', methods=['GET'])
@login_required
def get_users():
    """API endpoint to get all users (admin only)"""
    # Check if current user is admin
    current_user = User.query.get(session['user_id'])
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    users = User.query.all()
    return jsonify([user.to_dict() for user in users])


@app.route('/api/auth/users/<int:user_id>', methods=['PUT'])
@login_required
def update_user(user_id):
    """API endpoint to update user (admin only)"""
    # Check if current user is admin
    current_user = User.query.get(session['user_id'])
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    try:
        data = request.json
        user = User.query.get_or_404(user_id)

        # Only allow updating specific fields
        if 'is_active' in data:
            user.active = data['is_active']

        if 'is_admin' in data:
            user.is_admin = data['is_admin']

        if 'username' in data:
            # Check for username uniqueness
            existing_user = User.query.filter_by(
                username=data['username']).first()
            if existing_user and existing_user.id != user.id:
                return jsonify({"error": "Username already taken"}), 400
            user.username = data['username']

        if 'firstName' in data:
            user.first_name = data['firstName']

        if 'lastName' in data:
            user.last_name = data['lastName']

        if 'shopName' in data:
            user.shop_name = data['shopName']

        if 'productCategories' in data:
            user.product_categories = data['productCategories']

        user.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify(user.to_dict())

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating user: {str(e)}")
        return jsonify({"error": "Failed to update user"}), 500


@app.route('/api/auth/users/<int:user_id>', methods=['DELETE'])
@login_required
def delete_user(user_id):
    """API endpoint to delete user (admin only)"""
    # Check if current user is admin
    current_user = User.query.get(session['user_id'])
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    # Prevent admin from deleting themselves
    if user_id == current_user.id:
        return jsonify({"error": "Cannot delete your own account"}), 400

    try:
        user = User.query.get_or_404(user_id)
        username = user.username

        db.session.delete(user)
        db.session.commit()

        return jsonify({"message": f"User {username} deleted successfully"})

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting user: {str(e)}")
        return jsonify({"error": "Failed to delete user"}), 500


@app.route('/api/shop/details', methods=['GET'])
@login_required
def get_shop_details():
    """API endpoint to get shop details for the current user"""
    try:
        user_id = session.get('user_id')

        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        user = User.query.get_or_404(user_id)

        # Get shop name from user profile, fallback to username
        shop_name = user.shop_name or f"{user.username}'s Shop"

        return jsonify({
            'shop_name':
            shop_name,
            'owner_name':
            f"{user.first_name} {user.last_name}".strip() or user.username,
            'product_categories':
            user.product_categories or ""
        })

    except Exception as e:
        logger.error(f"Error getting shop details: {str(e)}")
        return jsonify({"error": "Failed to get shop details"}), 500


@app.route('/api/auth/users/stats', methods=['GET'])
@login_required
def get_user_stats():
    """API endpoint to get user statistics (admin only)"""
    # Check if current user is admin
    current_user = User.query.get(session['user_id'])
    if not current_user or not current_user.is_admin:
        return jsonify({"error": "Admin access required"}), 403

    try:
        total_users = User.query.count()
        active_users = User.query.filter_by(active=True).count()
        admin_users = User.query.filter_by(is_admin=True).count()
        unverified_users = User.query.filter_by(email_verified=False).count()

        # Get recent registrations (last 30 days)
        from datetime import timedelta
        thirty_days_ago = datetime.utcnow() - timedelta(days=30)
        recent_registrations = User.query.filter(
            User.created_at >= thirty_days_ago).count()

        return jsonify({
            'total_users': total_users,
            'active_users': active_users,
            'admin_users': admin_users,
            'unverified_users': unverified_users,
            'recent_registrations': recent_registrations
        })

    except Exception as e:
        logger.error(f"Error getting user stats: {str(e)}")
        return jsonify({"error": "Failed to get user statistics"}), 500


@app.route('/api/auth/profile', methods=['PUT'])
def update_profile():
    """API endpoint to update the current user's profile"""
    from auth_service import login_required

    @login_required
    def protected_update_profile():
        from models import User
        try:
            data = request.json
            user_id = session.get('user_id')

            if not user_id:
                return jsonify({"error": "User not authenticated"}), 401

            user = User.query.get_or_404(user_id)

            # Only allow updating specific fields (non-admin fields)
            if 'username' in data:
                user.username = data['username']

            if 'firstName' in data:
                user.first_name = data['firstName']

            if 'lastName' in data:
                user.last_name = data['lastName']

            if 'shopName' in data:
                user.shop_name = data['shopName']

            if 'productCategories' in data:
                user.product_categories = data['productCategories']

            # Update timestamps
            user.updated_at = datetime.utcnow()

            db.session.commit()
            return jsonify({"success": True, "user": user.to_dict()})

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating profile: {str(e)}")
            return jsonify({"error":
                            f"Failed to update profile: {str(e)}"}), 500

    return protected_update_profile()


@app.route('/api/auth/profile', methods=['GET'])
def get_profile():
    """API endpoint to get the current user's profile"""
    from auth_service import login_required

    @login_required
    def protected_get_profile():
        from models import User
        try:
            user_id = session.get('user_id')

            if not user_id:
                return jsonify({"error": "User not authenticated"}), 401

            user = User.query.get_or_404(user_id)
            return jsonify({"success": True, "user": user.to_dict()})

        except Exception as e:
            logger.error(f"Error getting profile: {str(e)}")
            return jsonify({"error": f"Failed to get profile: {str(e)}"}), 500

    return protected_get_profile()


@app.route('/api/auth/sync-profile', methods=['POST'])
def sync_profile():
    """API endpoint to sync user profile with Firebase"""
    from auth_service import login_required, verify_firebase_token, update_user_profile

    @login_required
    def protected_sync_profile():
        from models import User
        try:
            # Get current user
            user_id = session.get('user_id')

            if not user_id:
                return jsonify({"error": "User not authenticated"}), 401

            user = User.query.get_or_404(user_id)

            # Get Firebase ID token from request
            auth_header = request.headers.get('Authorization', '')
            if not auth_header.startswith('Bearer '):
                return jsonify({"error": "Invalid authorization header"}), 401

            token = auth_header.split(' ')[1]

            # Verify token and get user info
            firebase_user = verify_firebase_token(token)

            if not firebase_user:
                return jsonify({"error": "Invalid Firebase token"}), 401

            # Update user profile with Firebase data
            if firebase_user.get('displayName'):
                # Split display name into first and last name if available
                name_parts = firebase_user.get('displayName', '').split(' ', 1)
                if len(name_parts) > 0:
                    user.first_name = name_parts[0]
                if len(name_parts) > 1:
                    user.last_name = name_parts[1]

            # Update email and email verification status
            if firebase_user.get('email'):
                user.email = firebase_user.get('email')

            if 'emailVerified' in firebase_user:
                user.email_verified = firebase_user.get('emailVerified', False)

            # Update Firebase UID if needed
            if firebase_user.get('localId') and not user.firebase_uid:
                user.firebase_uid = firebase_user.get('localId')

            # Set last login time
            user.last_login = datetime.utcnow()

            # Update timestamps
            user.updated_at = datetime.utcnow()

            # Save changes
            db.session.commit()

            return jsonify({
                "success": True,
                "message": "Profile synchronized with Firebase",
                "user": user.to_dict()
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error syncing profile: {str(e)}")
            return jsonify({"error": f"Failed to sync profile: {str(e)}"}), 500

    return protected_sync_profile()


@app.route('/api/auth/change-password', methods=['POST'])
def change_password():
    """API endpoint to change user password"""
    from auth_service import login_required

    @login_required
    def protected_change_password():
        from models import User
        try:
            data = request.json
            user_id = session.get('user_id')

            if not user_id:
                return jsonify({"error": "User not authenticated"}), 401

            if 'current_password' not in data or 'new_password' not in data:
                return jsonify({
                    "error":
                    "Current password and new password are required"
                }), 400

            user = User.query.get_or_404(user_id)

            # Verify current password
            if not user.check_password(data['current_password']):
                return jsonify({"error": "Current password is incorrect"}), 400

            # Validate new password
            if len(data['new_password']) < 6:
                return jsonify(
                    {"error":
                     "Password must be at least 6 characters long"}), 400

            # Update password
            user.set_password(data['new_password'])
            db.session.commit()

            return jsonify({
                "success": True,
                "message": "Password changed successfully"
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error changing password: {str(e)}")
            return jsonify({"error": "Failed to change password"}), 500

    return protected_change_password()


@app.route('/api/auth/send-verification', methods=['POST'])
def send_verification():
    """API endpoint to send email verification"""
    from auth_service import login_required
    from notifications.email_service import send_email

    @login_required
    def protected_send_verification():
        from models import User
        import secrets
        import datetime

        try:
            user_id = session.get('user_id')

            if not user_id:
                return jsonify({"error": "User not authenticated"}), 401

            user = User.query.get_or_404(user_id)

            # Generate verification token
            verification_token = secrets.token_urlsafe(32)
            user.verification_token = verification_token
            user.verification_token_expires = datetime.datetime.utcnow(
            ) + datetime.timedelta(hours=24)
            db.session.commit()

            # Build verification URL
            verification_url = url_for('verify_email',
                                       token=verification_token,
                                       _external=True)

            # Create email content
            shop_name = user.shop_name or "Your Shop"
            html_content = f"""
            <h2>Email Verification</h2>
            <p>Hello {user.first_name or user.username},</p>
            <p>Thank you for registering your account for {shop_name}. Please verify your email address by clicking the link below:</p>
            <p><a href="{verification_url}" style```python
="display: inline-block; background-color: #4B0082; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email Address</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you did not create an account, please ignore this email.</p>
            """

            # Get sender email from settings
            from_email = get_setting_value('email_sender',
                                           "noreply@example.com")

            # Send email
            success = send_email(to_email=user.email,
                                 from_email=from_email,
                                 subject=f"Verify your email for {shop_name}",
                                 html_content=html_content)

            if not success:
                return jsonify({"error":
                                "Failed to send verification email"}), 500

            return jsonify({
                "success": True,
                "message": "Verification email sent"
            })

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error sending verification email: {str(e)}")
            return jsonify({"error": "Failed to send verification email"}), 500

    return protected_send_verification()


@app.route('/verify-email/<token>', methods=['GET'])
def verify_email(token):
    """Route to verify email from token"""
    from models import User
    import datetime

    try:
        if not token:
            flash('Invalid verification link.', 'danger')
            return redirect(url_for('index'))

        user = User.query.filter_by(verification_token=token).first()

        if not user:
            flash('Invalid verification link.', 'danger')
            return redirect(url_for('index'))

        # Check if token is expired
        if user.verification_token_expires and user.verification_token_expires < datetime.datetime.utcnow(
        ):
            flash('Verification link has expired. Please request a new one.',
                  'danger')
            return redirect(url_for('account'))

        # Mark email as verified
        user.email_verified = True
        user.verification_token = None
        user.verification_token_expires = None
        db.session.commit()

        flash('Your email has been successfully verified!', 'success')
        return redirect(url_for('account'))

    except Exception as e:
        db.session.rollback()
        logger.error(f"Error verifying email: {str(e)}")
        flash('An error occurred while verifying your email.', 'danger')
        return redirect(url_for('index'))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)