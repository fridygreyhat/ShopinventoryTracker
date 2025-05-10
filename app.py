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

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "shop_inventory_default_secret")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

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

# Initialize database tables
with app.app_context():
    # Import models here to avoid circular imports
    from models import Item, User, OnDemandProduct, Setting, Sale, SaleItem  # noqa: F401
    db.create_all()

@app.route('/')
def index():
    """Render the dashboard page"""
    return render_template('index.html')

@app.route('/inventory')
def inventory():
    """Render the inventory management page"""
    return render_template('inventory.html')

@app.route('/item/<int:item_id>')
def item_detail(item_id):
    """Render the item detail page"""
    # Get the item from database
    from models import Item
    item = Item.query.get_or_404(item_id)
    
    return render_template('item_detail.html', item=item.to_dict())

@app.route('/reports')
def reports():
    """Render the reports page"""
    return render_template('reports.html')

@app.route('/settings')
def settings():
    """Render the settings page"""
    return render_template('settings.html')

@app.route('/on-demand')
def on_demand():
    """Render the on-demand products page"""
    return render_template('on_demand.html')

@app.route('/sales')
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
    
    # Get low stock items
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
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
