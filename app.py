import os
import logging
import uuid
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
import io
import csv
import requests

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "shop_inventory_default_secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Firebase configuration
app.config["FIREBASE_API_KEY"] = os.environ.get("FIREBASE_API_KEY")
app.config["FIREBASE_PROJECT_ID"] = os.environ.get("FIREBASE_PROJECT_ID")
app.config["FIREBASE_APP_ID"] = os.environ.get("FIREBASE_APP_ID")

# Database configuration
class Base(DeclarativeBase):
    pass

app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "sqlite:///inventory.db")
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

# Initialize database tables
with app.app_context():
    # Import models here to avoid circular imports
    from models import Item, User, OnDemandProduct, Setting, Sale, SaleItem  # noqa: F401
    
    # When we have schema changes, we need to reset the database
    # Comment out the line below to avoid data loss in production 
    db.drop_all()
    db.create_all()

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
        search_filter = (
            Item.name.ilike(f'%{search_term}%') |
            Item.sku.ilike(f'%{search_term}%') |
            Item.description.ilike(f'%{search_term}%')
        )
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
    
    try:
        item_data = request.json
        
        # Validate required fields
        required_fields = ['name', 'quantity']
        for field in required_fields:
            if field not in item_data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Handle price fields
        buying_price = float(item_data.get("buying_price", 0))
        selling_price_retail = float(item_data.get("selling_price_retail", 0))
        selling_price_wholesale = float(item_data.get("selling_price_wholesale", 0))
        
        # Use retail price as default price for backward compatibility
        price = selling_price_retail
        
        # Create new item
        new_item = Item(
            name=item_data["name"],
            description=item_data.get("description", ""),
            quantity=int(item_data["quantity"]),
            buying_price=buying_price,
            selling_price_retail=selling_price_retail,
            selling_price_wholesale=selling_price_wholesale,
            price=price,
            sales_type=item_data.get("sales_type", "both"),
            category=item_data.get("category", "Uncategorized"),
            sku=item_data.get("sku", f"SKU-{datetime.now().strftime('%Y%m%d%H%M%S')}")
        )
        
        # Add to database
        db.session.add(new_item)
        db.session.commit()
        
        # Check if quantity is below threshold
        quantity = int(item_data["quantity"])
        from models import Setting
        
        # Get threshold
        low_stock_threshold = 10
        try:
            setting = Setting.query.filter_by(key='low_stock_threshold').first()
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
            email_setting = Setting.query.filter_by(key='email_notifications_enabled').first()
            sms_setting = Setting.query.filter_by(key='sms_notifications_enabled').first()
            
            email_enabled = email_setting and email_setting.value.lower() == 'true'
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
                    args=(db, Item, Setting)
                )
                notification_thread.daemon = True
                notification_thread.start()
                
                logger.info(f"Low stock notification triggered for new item {new_item.name}")
            except Exception as e:
                logger.error(f"Error triggering low stock notification: {str(e)}")
        
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
            item_data["selling_price_retail"] = float(item_data["selling_price_retail"])
            # Update the legacy price field to keep compatibility
            item_data["price"] = item_data["selling_price_retail"]
        
        if "selling_price_wholesale" in item_data:
            item_data["selling_price_wholesale"] = float(item_data["selling_price_wholesale"])
        
        if "buying_price" in item_data:
            item_data["buying_price"] = float(item_data["buying_price"])
        
        # Update the item with new data
        for key, value in item_data.items():
            if key not in ['id', 'created_at']:  # Don't allow changing these fields
                setattr(item, key, value)
        
        # Save to database
        db.session.commit()
        
        # Check if quantity was updated and is below threshold
        if 'quantity' in item_data:
            from models import Setting
            
            # Get threshold
            low_stock_threshold = 10
            try:
                setting = Setting.query.filter_by(key='low_stock_threshold').first()
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
                email_setting = Setting.query.filter_by(key='email_notifications_enabled').first()
                sms_setting = Setting.query.filter_by(key='sms_notifications_enabled').first()
                
                email_enabled = email_setting and email_setting.value.lower() == 'true'
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
                        args=(db, Item, Setting)
                    )
                    notification_thread.daemon = True
                    notification_thread.start()
                    
                    logger.info(f"Low stock notification triggered for item {item.name}")
                except Exception as e:
                    logger.error(f"Error triggering low stock notification: {str(e)}")
        
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

@app.route('/api/inventory/categories', methods=['GET'])
def get_categories():
    """API endpoint to get all unique categories"""
    from models import Item
    from sqlalchemy import func
    
    # Query distinct categories 
    categories = db.session.query(
        func.coalesce(Item.category, 'Uncategorized').label('category')
    ).distinct().all()
    
    return jsonify([c.category for c in categories])

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
    low_stock_items = Item.query.filter(Item.quantity <= low_stock_threshold).all()
    out_of_stock_items = Item.query.filter(Item.quantity == 0).all()
    
    # Calculate inventory value using selling price retail
    total_value_query = db.session.query(
        func.sum(Item.quantity * Item.selling_price_retail)
    ).scalar()
    total_value = float(total_value_query) if total_value_query is not None else 0
    
    report = {
        "total_items": item_count,
        "total_stock": total_stock,
        "average_stock_per_item": total_stock / item_count if item_count > 0 else 0,
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
        func.coalesce(Item.category, 'Uncategorized').label('category')
    ).distinct().all()
    
    # For each category, get the stats
    for cat in category_list:
        category = cat.category
        
        # Get items count in this category
        count = db.session.query(func.count(Item.id)).filter(
            func.coalesce(Item.category, 'Uncategorized') == category
        ).scalar() or 0
        
        # Get total quantity
        total_quantity = db.session.query(func.sum(Item.quantity)).filter(
            func.coalesce(Item.category, 'Uncategorized') == category
        ).scalar() or 0
        
        # Get total value based on retail selling price
        total_value_query = db.session.query(
            func.sum(Item.quantity * Item.selling_price_retail)
        ).filter(
            func.coalesce(Item.category, 'Uncategorized') == category
        ).scalar()
        total_value = float(total_value_query) if total_value_query is not None else 0
        
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
    writer.writerow(['ID', 'SKU', 'Name', 'Description', 'Category', 
                    'Quantity', 'Price', 'Created At', 'Updated At'])
    
    # Get all items
    items = Item.query.all()
    
    # Write data rows
    for item in items:
        writer.writerow([
            item.id,
            item.sku or '',
            item.name,
            item.description or '',
            item.category or 'Uncategorized',
            item.quantity,
            item.price,
            item.created_at.isoformat() if item.created_at else '',
            item.updated_at.isoformat() if item.updated_at else ''
        ])
    
    # Create binary stream
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'inventory_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

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
        search_filter = (
            OnDemandProduct.name.ilike(f'%{search_term}%') |
            OnDemandProduct.description.ilike(f'%{search_term}%') |
            OnDemandProduct.materials.ilike(f'%{search_term}%')
        )
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
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create new product
        new_product = OnDemandProduct(
            name=product_data["name"],
            description=product_data.get("description", ""),
            base_price=float(product_data["base_price"]),
            production_time=int(product_data.get("production_time", 0)),
            category=product_data.get("category", "Uncategorized"),
            materials=product_data.get("materials", ""),
            is_active=product_data.get("is_active", True)
        )
        
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
            if key not in ['id', 'created_at']:  # Don't allow changing these fields
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
        
        return jsonify({"message": f"Deleted {product_name}", "product": product_dict})
    
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting on-demand product: {str(e)}")
        return jsonify({"error": "Failed to delete on-demand product"}), 500

@app.route('/api/on-demand/categories', methods=['GET'])
def get_on_demand_categories():
    """API endpoint to get all unique on-demand product categories"""
    from models import OnDemandProduct
    from sqlalchemy import func
    
    # Query distinct categories 
    categories = db.session.query(
        func.coalesce(OnDemandProduct.category, 'Uncategorized').label('category')
    ).distinct().all()
    
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
        existing_setting = Setting.query.filter_by(key=setting_data['key']).first()
        
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
                category=setting_data.get('category', 'general')
            )
            
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
        
        return jsonify({"message": f"Deleted setting '{key}'", "setting": setting_dict})
    
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
            return jsonify({"error": "Invalid start_date format. Use YYYY-MM-DD"}), 400
    
    if end_date_str:
        try:
            end_date = datetime.strptime(end_date_str, '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid end_date format. Use YYYY-MM-DD"}), 400
    
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
        FinancialTransaction.date >= start_date,
        FinancialTransaction.date <= end_date
    )
    
    if transaction_type:
        query = query.filter(FinancialTransaction.transaction_type == transaction_type)
    
    if category:
        query = query.filter(FinancialTransaction.category == category)
    
    # Execute query and order by date (most recent first)
    transactions = query.order_by(FinancialTransaction.date.desc()).all()
    
    # Calculate totals
    total_income = sum(t.amount for t in transactions if t.transaction_type == 'Income')
    total_expenses = sum(t.amount for t in transactions if t.transaction_type == 'Expense')
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
        return jsonify({"error": "transaction_type must be 'Income' or 'Expense'"}), 400
    
    # Parse date if provided, otherwise use current date
    date = datetime.utcnow().date()
    if 'date' in data and data['date']:
        try:
            date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    # Create new transaction
    transaction = FinancialTransaction(
        date=date,
        description=data['description'],
        amount=data['amount'],
        transaction_type=data['transaction_type'],
        category=data['category'],
        reference_id=data.get('reference_id'),
        payment_method=data.get('payment_method'),
        notes=data.get('notes')
    )
    
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
            transaction.date = datetime.strptime(data['date'], '%Y-%m-%d').date()
        except ValueError:
            return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400
    
    if 'description' in data:
        transaction.description = data['description']
    
    if 'amount' in data:
        transaction.amount = data['amount']
    
    if 'transaction_type' in data:
        if data['transaction_type'] not in ['Income', 'Expense']:
            return jsonify({"error": "transaction_type must be 'Income' or 'Expense'"}), 400
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
        return jsonify({"error": f"Failed to update transaction: {str(e)}"}), 500

@app.route('/api/finance/transactions/<int:transaction_id>', methods=['DELETE'])
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
        return jsonify({"error": f"Failed to delete transaction: {str(e)}"}), 500

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
        func.sum(FinancialTransaction.amount).filter(FinancialTransaction.transaction_type == 'Income').label('income'),
        func.sum(FinancialTransaction.amount).filter(FinancialTransaction.transaction_type == 'Expense').label('expenses')
    ).filter(
        extract('year', FinancialTransaction.date) == year
    ).group_by(
        extract('month', FinancialTransaction.date)
    ).order_by(
        extract('month', FinancialTransaction.date)
    ).all()
    
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
def get_transaction_categories():
    """API endpoint to get all transaction categories"""
    from models import TransactionCategory
    
    # Get all categories from the enum
    categories = [cat.value for cat in TransactionCategory]
    
    return jsonify(categories)

# Sales API Routes
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
                end_datetime = end_datetime.replace(hour=23, minute=59, second=59)
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

@app.route('/api/sales', methods=['POST'])
def create_sale():
    """API endpoint to create a new sale transaction"""
    try:
        data = request.json
        
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        # Generate a unique invoice number
        invoice_number = f"INV-{datetime.now().strftime('%Y%m%d')}-{str(uuid.uuid4())[:8].upper()}"
        
        # Create new sale record
        new_sale = Sale(
            invoice_number=invoice_number,
            customer_name=data.get('customer', {}).get('name', 'Walk-in Customer'),
            customer_phone=data.get('customer', {}).get('phone', ''),
            sale_type=data.get('sale_type', 'retail'),
            subtotal=data.get('subtotal', 0),
            discount_type=data.get('discount', {}).get('type', 'none'),
            discount_value=data.get('discount', {}).get('value', 0),
            discount_amount=data.get('discount', {}).get('amount', 0),
            total=data.get('total', 0),
            payment_method=data.get('payment', {}).get('method', 'cash'),
            payment_details=json.dumps(data.get('payment', {}).get('mobile_info', {})),
            payment_amount=data.get('payment', {}).get('amount', 0),
            change_amount=data.get('payment', {}).get('change', 0),
            notes=data.get('notes', '')
        )
        
        db.session.add(new_sale)
        db.session.flush()  # Flush to get the sale ID
        
        # Add sale items
        for item_data in data.get('items', []):
            # Get item from database if it exists
            item = Item.query.filter_by(id=item_data.get('id')).first()
            
            # Create sale item record
            sale_item = SaleItem(
                sale_id=new_sale.id,
                item_id=item.id if item else None,
                product_name=item_data.get('name', 'Unknown Product'),
                product_sku=item_data.get('sku', ''),
                price=item_data.get('price', 0),
                quantity=item_data.get('quantity', 1),
                total=item_data.get('total', 0)
            )
            
            db.session.add(sale_item)
            
            # Update inventory quantity if item exists
            if item:
                item.quantity = max(0, item.quantity - item_data.get('quantity', 1))
        
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
            'success': True,
            'low_stock_count': len(low_stock_items),
            'low_stock_items': [item.to_dict() for item in low_stock_items]
        })
    
    except Exception as e:
        logger.error(f"Error checking low stock: {str(e)}")
        return jsonify({
            'success': False, 
            'errors': [f"Error checking low stock: {str(e)}"]
        }), 500


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
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    
    # Handle registration form submission
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        shop_name = request.form.get('shop_name')
        product_categories = request.form.get('product_categories')
        
        # Basic validation
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
            
        # Check if username or email already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists. Please choose another.', 'danger')
            return render_template('register.html')
            
        if User.query.filter_by(email=email).first():
            flash('Email already exists. Please use another or log in.', 'danger')
            return render_template('register.html')
            
        # Create new user
        new_user = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            shop_name=shop_name,
            product_categories=product_categories,
            email_verified=False,
            active=True
        )
        new_user.set_password(password)
        
        # Save user to database
        db.session.add(new_user)
        db.session.commit()
        
        # Log the user in
        login_user(new_user)
        
        flash('Your account has been created successfully!', 'success')
        return redirect(url_for('index'))
    
    # Render registration template for GET requests
    return render_template('register.html')

@app.route('/api/auth/session', methods=['POST'])
def create_session():
    """Create a session for authenticated user using Firebase token"""
    try:
        data = request.json
        
        if not data or 'idToken' not in data:
            return jsonify({"error": "Firebase ID token is required"}), 400
            
        # Verify the Firebase token
        user_data = verify_firebase_token(data['idToken'])
        if not user_data:
            return jsonify({"error": "Invalid or expired token"}), 401
            
        # Create or update user in database
        user = create_or_update_user(user_data)
        
        if not user:
            return jsonify({"error": "Failed to create user record"}), 500
            
        # Update last login time
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        # Set session data
        session['user_id'] = user.id
        session['email'] = user.email
        session['is_admin'] = user.is_admin
        session.permanent = data.get('remember', False)
        
        return jsonify({"success": True, "user": user.to_dict()})
        
    except Exception as e:
        logger.error(f"Error creating session with Firebase: {str(e)}")
        return jsonify({"error": "Failed to create session"}), 500

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
def admin_users():
    """Render the user management page (admin only)"""
    from auth_service import admin_required
    
    @admin_required
    def protected_admin_users():
        from models import User
        users = User.query.all()
        return render_template('admin_users.html', users=users)
        
    return protected_admin_users()

@app.route('/api/auth/users', methods=['GET'])
def get_users():
    """API endpoint to get all users (admin only)"""
    from auth_service import admin_required
    
    @admin_required
    def protected_get_users():
        from models import User
        users = User.query.all()
        return jsonify([user.to_dict() for user in users])
        
    return protected_get_users()

@app.route('/api/auth/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """API endpoint to update user (admin only)"""
    from auth_service import admin_required
    
    @admin_required
    def protected_update_user():
        from models import User
        try:
            data = request.json
            user = User.query.get_or_404(user_id)
            
            # Only allow updating specific fields
            if 'is_active' in data:
                user.is_active = data['is_active']
                
            if 'is_admin' in data:
                user.is_admin = data['is_admin']
                
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
                
            db.session.commit()
            return jsonify(user.to_dict())
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating user: {str(e)}")
            return jsonify({"error": "Failed to update user"}), 500
            
    return protected_update_user()
    
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
                
            db.session.commit()
            return jsonify(user.to_dict())
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating profile: {str(e)}")
            return jsonify({"error": "Failed to update profile"}), 500
            
    return protected_update_profile()


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
                return jsonify({"error": "Current password and new password are required"}), 400
                
            user = User.query.get_or_404(user_id)
            
            # Verify current password
            if not user.check_password(data['current_password']):
                return jsonify({"error": "Current password is incorrect"}), 400
                
            # Validate new password
            if len(data['new_password']) < 6:
                return jsonify({"error": "Password must be at least 6 characters long"}), 400
                
            # Update password
            user.set_password(data['new_password'])
            db.session.commit()
            
            return jsonify({"success": True, "message": "Password changed successfully"})
            
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
            user.verification_token_expires = datetime.datetime.utcnow() + datetime.timedelta(hours=24)
            db.session.commit()
            
            # Build verification URL
            verification_url = url_for('verify_email', token=verification_token, _external=True)
            
            # Create email content
            shop_name = user.shop_name or "Your Shop"
            html_content = f"""
            <h2>Email Verification</h2>
            <p>Hello {user.first_name or user.username},</p>
            <p>Thank you for registering your account for {shop_name}. Please verify your email address by clicking the link below:</p>
            <p><a href="{verification_url}" style="display: inline-block; background-color: #4B0082; color: white; padding: 10px 20px; text-decoration: none; border-radius: 5px;">Verify Email Address</a></p>
            <p>This link will expire in 24 hours.</p>
            <p>If you did not create an account, please ignore this email.</p>
            """
            
            # Get sender email from settings
            from_email = get_setting_value('email_sender', "noreply@example.com")
            
            # Send email
            success = send_email(
                to_email=user.email,
                from_email=from_email,
                subject=f"Verify your email for {shop_name}",
                html_content=html_content
            )
            
            if not success:
                return jsonify({"error": "Failed to send verification email"}), 500
                
            return jsonify({"success": True, "message": "Verification email sent"})
            
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
        if user.verification_token_expires and user.verification_token_expires < datetime.datetime.utcnow():
            flash('Verification link has expired. Please request a new one.', 'danger')
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
