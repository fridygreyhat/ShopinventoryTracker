"""
Inventory management models
"""
from datetime import datetime
from decimal import Decimal
from app import db


class Category(db.Model):
    """Product category model"""
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=True)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Self-referential relationship for subcategories
    children = db.relationship('Category', backref=db.backref('parent', remote_side=[id]))
    items = db.relationship('Item', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'


class Item(db.Model):
    """Inventory item model"""
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    sku = db.Column(db.String(100), nullable=True)
    barcode = db.Column(db.String(100), nullable=True)
    
    # Pricing
    cost_price = db.Column(db.Numeric(10, 2), nullable=True)
    selling_price_retail = db.Column(db.Numeric(10, 2), nullable=False)
    selling_price_wholesale = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Stock
    quantity = db.Column(db.Integer, default=0, nullable=False)
    reorder_level = db.Column(db.Integer, default=0, nullable=False)
    
    # Categories and organization
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sale_items = db.relationship('SaleItem', backref='item', lazy=True)
    stock_movements = db.relationship('StockMovement', backref='item', lazy=True)
    location_stocks = db.relationship('LocationStock', backref='item', lazy=True)
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.cost_price and self.selling_price_retail and self.cost_price > 0:
            profit = self.selling_price_retail - self.cost_price
            return (profit / self.selling_price_retail) * 100
        return 0
    
    @property
    def total_stock_value(self):
        """Calculate total stock value at cost price"""
        if self.cost_price:
            return self.quantity * self.cost_price
        return Decimal('0.00')
    
    @property
    def retail_stock_value(self):
        """Calculate total stock value at retail price"""
        return self.quantity * self.selling_price_retail
    
    def get_stock_at_location(self, location_id):
        """Get stock quantity at specific location"""
        location_stock = LocationStock.query.filter_by(
            item_id=self.id,
            location_id=location_id
        ).first()
        return location_stock.quantity if location_stock else 0
    
    def is_low_stock(self, threshold=None):
        """Check if item is below reorder level"""
        if threshold is None:
            threshold = self.reorder_level
        return self.quantity <= threshold
    
    def __repr__(self):
        return f'<Item {self.name}>'


class LocationStock(db.Model):
    """Stock levels at different locations"""
    __tablename__ = 'location_stocks'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint on item and location
    __table_args__ = (db.UniqueConstraint('item_id', 'location_id', name='_item_location_uc'),)
    
    def __repr__(self):
        return f'<LocationStock Item:{self.item_id} Location:{self.location_id} Qty:{self.quantity}>'


class StockMovement(db.Model):
    """Track all stock movements"""
    __tablename__ = 'stock_movements'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=True)
    movement_type = db.Column(db.String(50), nullable=False)  # 'sale', 'purchase', 'adjustment', 'transfer'
    quantity = db.Column(db.Integer, nullable=False)  # Positive for in, negative for out
    reference = db.Column(db.String(100), nullable=True)  # Sale ID, Purchase order, etc.
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    def __repr__(self):
        return f'<StockMovement {self.movement_type}: {self.quantity}>'


class StockTransfer(db.Model):
    """Stock transfers between locations"""
    __tablename__ = 'stock_transfers'
    
    id = db.Column(db.Integer, primary_key=True)
    from_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    to_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, completed, cancelled
    notes = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Relationships
    from_location = db.relationship('Location', foreign_keys=[from_location_id], backref='transfers_out')
    to_location = db.relationship('Location', foreign_keys=[to_location_id], backref='transfers_in')
    items = db.relationship('StockTransferItem', backref='transfer', lazy=True, cascade='all, delete-orphan')
    
    @property
    def total_items(self):
        """Get total number of items in transfer"""
        return sum(item.quantity for item in self.items)
    
    def __repr__(self):
        return f'<StockTransfer {self.id}: {self.status}>'


class StockTransferItem(db.Model):
    """Items in a stock transfer"""
    __tablename__ = 'stock_transfer_items'
    
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('stock_transfers.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    
    # Relationships
    item = db.relationship('Item')
    
    def __repr__(self):
        return f'<StockTransferItem {self.quantity}x {self.item.name if self.item else "Unknown"}>'