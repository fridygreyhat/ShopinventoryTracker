import json
from datetime import datetime

# This service module provides a more structured way to handle inventory operations
# It's not used in the current implementation but could be useful for expansion

class InventoryService:
    def __init__(self, inventory_file="inventory_data.json"):
        self.inventory_file = inventory_file
        self.inventory_data = self.load_inventory()
    
    def load_inventory(self):
        """Load inventory data from JSON file or initialize if not exists"""
        try:
            with open(self.inventory_file, 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            # Initialize with empty inventory if file doesn't exist or is corrupted
            return {"items": [], "next_id": 1}
    
    def save_inventory(self):
        """Save inventory data to JSON file"""
        with open(self.inventory_file, 'w') as f:
            json.dump(self.inventory_data, f, indent=2)
    
    def get_all_items(self, category=None, search_term=None, min_stock=None, max_stock=None):
        """Get all inventory items with optional filtering"""
        filtered_items = self.inventory_data["items"]
        
        if category:
            filtered_items = [item for item in filtered_items if item.get('category') == category]
        
        if search_term:
            search_term = search_term.lower()
            filtered_items = [item for item in filtered_items 
                             if search_term in item.get('name', '').lower() 
                             or search_term in item.get('sku', '').lower()
                             or search_term in item.get('description', '').lower()]
        
        if min_stock is not None:
            filtered_items = [item for item in filtered_items if item.get('quantity', 0) >= min_stock]
        
        if max_stock is not None:
            filtered_items = [item for item in filtered_items if item.get('quantity', 0) <= max_stock]
        
        return filtered_items
    
    def get_item(self, item_id):
        """Get a specific inventory item by ID"""
        return next((item for item in self.inventory_data["items"] if item["id"] == item_id), None)
    
    def add_item(self, item_data):
        """Add a new inventory item"""
        # Create new item with a unique ID
        new_item = {
            "id": self.inventory_data["next_id"],
            "name": item_data["name"],
            "description": item_data.get("description", ""),
            "quantity": int(item_data["quantity"]),
            "price": float(item_data["price"]),
            "category": item_data.get("category", "Uncategorized"),
            "sku": item_data.get("sku", f"SKU-{self.inventory_data['next_id']}"),
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat()
        }
        
        # Add to inventory and increment next_id
        self.inventory_data["items"].append(new_item)
        self.inventory_data["next_id"] += 1
        
        # Save to file
        self.save_inventory()
        
        return new_item
    
    def update_item(self, item_id, item_data):
        """Update an inventory item"""
        item_index = next((i for i, item in enumerate(self.inventory_data["items"]) 
                         if item["id"] == item_id), None)
        
        if item_index is None:
            return None
        
        # Update the item with new data
        for key, value in item_data.items():
            if key not in ['id', 'created_at']:  # Don't allow changing these fields
                self.inventory_data["items"][item_index][key] = value
        
        # Update timestamp
        self.inventory_data["items"][item_index]["updated_at"] = datetime.now().isoformat()
        
        # Save to file
        self.save_inventory()
        
        return self.inventory_data["items"][item_index]
    
    def delete_item(self, item_id):
        """Delete an inventory item"""
        item_index = next((i for i, item in enumerate(self.inventory_data["items"]) 
                         if item["id"] == item_id), None)
        
        if item_index is None:
            return None
        
        # Remove item from inventory
        deleted_item = self.inventory_data["items"].pop(item_index)
        
        # Save to file
        self.save_inventory()
        
        return deleted_item
    
    def get_categories(self):
        """Get all unique categories"""
        return list(set(item.get('category', 'Uncategorized') for item in self.inventory_data["items"]))
    
    def get_stock_status_report(self, low_stock_threshold=10):
        """Generate stock status report"""
        total_items = len(self.inventory_data["items"])
        total_stock = sum(item.get('quantity', 0) for item in self.inventory_data["items"])
        
        # Count items with low stock
        low_stock_items = [item for item in self.inventory_data["items"] 
                         if item.get('quantity', 0) <= low_stock_threshold]
        out_of_stock_items = [item for item in self.inventory_data["items"] 
                            if item.get('quantity', 0) == 0]
        
        # Calculate inventory value
        total_value = sum(
            item.get('quantity', 0) * item.get('price', 0) 
            for item in self.inventory_data["items"]
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
        
        return report
    
    def get_category_breakdown_report(self):
        """Generate category breakdown report"""
        # Group items by category
        categories = {}
        
        for item in self.inventory_data["items"]:
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
        
        return categories
