"""
Location management models
"""
from datetime import datetime
from app import db


class Location(db.Model):
    """Business location model"""
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    # Location type
    location_type = db.Column(db.String(50), default='store', nullable=False)  # store, warehouse, online
    
    # Status
    active = db.Column(db.Boolean, default=True, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    
    # User association
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    stock_items = db.relationship('LocationStock', backref='location', lazy=True)
    stock_movements = db.relationship('StockMovement', backref='location', lazy=True)
    
    @property
    def total_stock_value(self):
        """Calculate total stock value at this location"""
        total_value = 0
        for stock in self.stock_items:
            if stock.item and stock.item.cost_price:
                total_value += stock.quantity * stock.item.cost_price
        return total_value
    
    @property
    def total_items(self):
        """Get total number of different items at this location"""
        return len([stock for stock in self.stock_items if stock.quantity > 0])
    
    def __repr__(self):
        return f'<Location {self.name}>'