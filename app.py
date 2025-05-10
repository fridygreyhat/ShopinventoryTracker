import os
import logging
import json
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session
import io
import csv

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET", "shop_inventory_default_secret")

# In-memory storage for inventory
# We'll use a simple JSON file for persistence
INVENTORY_FILE = "inventory_data.json"

def load_inventory():
    """Load inventory data from JSON file or initialize if not exists"""
    try:
        with open(INVENTORY_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Initialize with empty inventory if file doesn't exist or is corrupted
        return {"items": [], "next_id": 1}

def save_inventory(inventory_data):
    """Save inventory data to JSON file"""
    with open(INVENTORY_FILE, 'w') as f:
        json.dump(inventory_data, f, indent=2)

# Load initial inventory
inventory_data = load_inventory()

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
    # Get the item from inventory
    item = next((item for item in inventory_data["items"] if item["id"] == item_id), None)
    
    if not item:
        flash("Item not found", "danger")
        return redirect(url_for('inventory'))
        
    return render_template('item_detail.html', item=item)

@app.route('/reports')
def reports():
    """Render the reports page"""
    return render_template('reports.html')

# API Routes
@app.route('/api/inventory', methods=['GET'])
def get_inventory():
    """API endpoint to get all inventory items"""
    # Optional filtering
    category = request.args.get('category')
    search_term = request.args.get('search', '').lower()
    min_stock = request.args.get('min_stock')
    max_stock = request.args.get('max_stock')
    
    # Apply filters if provided
    filtered_items = inventory_data["items"]
    
    if category:
        filtered_items = [item for item in filtered_items if item.get('category') == category]
    
    if search_term:
        filtered_items = [item for item in filtered_items 
                         if search_term in item.get('name', '').lower() 
                         or search_term in item.get('sku', '').lower()
                         or search_term in item.get('description', '').lower()]
    
    if min_stock:
        try:
            min_stock = int(min_stock)
            filtered_items = [item for item in filtered_items if item.get('quantity', 0) >= min_stock]
        except ValueError:
            pass
    
    if max_stock:
        try:
            max_stock = int(max_stock)
            filtered_items = [item for item in filtered_items if item.get('quantity', 0) <= max_stock]
        except ValueError:
            pass
    
    return jsonify(filtered_items)

@app.route('/api/inventory', methods=['POST'])
def add_item():
    """API endpoint to add a new inventory item"""
    try:
        item_data = request.json
        
        # Validate required fields
        required_fields = ['name', 'quantity', 'price']
        for field in required_fields:
            if field not in item_data:
                return jsonify({"error": f"Missing required field: {field}"}), 400
        
        # Create new item with a unique ID
        new_item = {
            "id": inventory_data["next_id"],
            "name": item_data["name"],
            "description": item_data.get("description", ""),
            "quantity": int(item_data["quantity"]),
            "price": float(item_data["price"]),
            "category": item_data.get("category", "Uncategorized"),
            "sku": item_data.get("sku", f"SKU-{inventory_data['next_id']}"),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Add to inventory and increment next_id
        inventory_data["items"].append(new_item)
        inventory_data["next_id"] += 1
        
        # Save to file
        save_inventory(inventory_data)
        
        return jsonify(new_item), 201
    
    except Exception as e:
        logger.error(f"Error adding item: {str(e)}")
        return jsonify({"error": "Failed to add item"}), 500

@app.route('/api/inventory/<int:item_id>', methods=['GET'])
def get_item(item_id):
    """API endpoint to get a specific inventory item"""
    item = next((item for item in inventory_data["items"] if item["id"] == item_id), None)
    
    if not item:
        return jsonify({"error": "Item not found"}), 404
        
    return jsonify(item)

@app.route('/api/inventory/<int:item_id>', methods=['PUT'])
def update_item(item_id):
    """API endpoint to update an inventory item"""
    try:
        item_data = request.json
        item_index = next((i for i, item in enumerate(inventory_data["items"]) 
                         if item["id"] == item_id), None)
        
        if item_index is None:
            return jsonify({"error": "Item not found"}), 404
        
        # Update the item with new data
        for key, value in item_data.items():
            if key not in ['id', 'created_at']:  # Don't allow changing these fields
                inventory_data["items"][item_index][key] = value
        
        # Update timestamp
        inventory_data["items"][item_index]["updated_at"] = datetime.now().isoformat()
        
        # Save to file
        save_inventory(inventory_data)
        
        return jsonify(inventory_data["items"][item_index])
    
    except Exception as e:
        logger.error(f"Error updating item: {str(e)}")
        return jsonify({"error": "Failed to update item"}), 500

@app.route('/api/inventory/<int:item_id>', methods=['DELETE'])
def delete_item(item_id):
    """API endpoint to delete an inventory item"""
    try:
        item_index = next((i for i, item in enumerate(inventory_data["items"]) 
                         if item["id"] == item_id), None)
        
        if item_index is None:
            return jsonify({"error": "Item not found"}), 404
        
        # Remove item from inventory
        deleted_item = inventory_data["items"].pop(item_index)
        
        # Save to file
        save_inventory(inventory_data)
        
        return jsonify({"message": f"Deleted {deleted_item['name']}", "item": deleted_item})
    
    except Exception as e:
        logger.error(f"Error deleting item: {str(e)}")
        return jsonify({"error": "Failed to delete item"}), 500

@app.route('/api/inventory/categories', methods=['GET'])
def get_categories():
    """API endpoint to get all unique categories"""
    categories = set(item.get('category', 'Uncategorized') for item in inventory_data["items"])
    return jsonify(list(categories))

@app.route('/api/reports/stock-status', methods=['GET'])
def stock_status_report():
    """API endpoint to get stock status report"""
    low_stock_threshold = int(request.args.get('low_stock_threshold', 10))
    
    total_items = len(inventory_data["items"])
    total_stock = sum(item.get('quantity', 0) for item in inventory_data["items"])
    
    # Count items with low stock
    low_stock_items = [item for item in inventory_data["items"] 
                     if item.get('quantity', 0) <= low_stock_threshold]
    out_of_stock_items = [item for item in inventory_data["items"] 
                        if item.get('quantity', 0) == 0]
    
    # Calculate inventory value
    total_value = sum(
        item.get('quantity', 0) * item.get('price', 0) 
        for item in inventory_data["items"]
    )
    
    report = {
        "total_items": total_items,
        "total_stock": total_stock,
        "average_stock_per_item": total_stock / total_items if total_items > 0 else 0,
        "low_stock_items_count": len(low_stock_items),
        "out_of_stock_items_count": len(out_of_stock_items),
        "low_stock_items": low_stock_items,
        "out_of_stock_items": out_of_stock_items,
        "total_inventory_value": total_value
    }
    
    return jsonify(report)

@app.route('/api/reports/category-breakdown', methods=['GET'])
def category_breakdown_report():
    """API endpoint to get category breakdown report"""
    # Group items by category
    categories = {}
    
    for item in inventory_data["items"]:
        category = item.get('category', 'Uncategorized')
        if category not in categories:
            categories[category] = {
                "count": 0,
                "total_quantity": 0,
                "total_value": 0
            }
        
        categories[category]["count"] += 1
        categories[category]["total_quantity"] += item.get('quantity', 0)
        categories[category]["total_value"] += item.get('quantity', 0) * item.get('price', 0)
    
    return jsonify(categories)

@app.route('/api/export/csv', methods=['GET'])
def export_csv():
    """API endpoint to export inventory as CSV"""
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Write header row
    writer.writerow(['ID', 'SKU', 'Name', 'Description', 'Category', 
                    'Quantity', 'Price', 'Created At', 'Updated At'])
    
    # Write data rows
    for item in inventory_data["items"]:
        writer.writerow([
            item.get('id', ''),
            item.get('sku', ''),
            item.get('name', ''),
            item.get('description', ''),
            item.get('category', 'Uncategorized'),
            item.get('quantity', 0),
            item.get('price', 0),
            item.get('created_at', ''),
            item.get('updated_at', '')
        ])
    
    # Create binary stream
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'inventory_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    )

@app.route('/logout')
def logout():
    """Logout route to clear session data"""
    # Clear session data
    session.clear()
    flash('You have been logged out', 'success')
    return redirect(url_for('index'))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
