"""
Automation and on-demand product models
"""
from datetime import datetime
from decimal import Decimal
from app import db


class OnDemandProduct(db.Model):
    """On-demand product model"""
    __tablename__ = 'on_demand_products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)
    category = db.Column(db.String(100), nullable=True)
    
    # Pricing
    base_price = db.Column(db.Numeric(10, 2), nullable=False)
    markup_percentage = db.Column(db.Numeric(5, 2), default=20, nullable=False)
    selling_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Supplier information
    supplier_name = db.Column(db.String(200), nullable=True)
    supplier_contact = db.Column(db.String(200), nullable=True)
    supplier_lead_time = db.Column(db.Integer, default=7, nullable=False)  # days
    
    # Product details
    minimum_order_quantity = db.Column(db.Integer, default=1, nullable=False)
    maximum_order_quantity = db.Column(db.Integer, nullable=True)
    
    # Status
    active = db.Column(db.Boolean, default=True, nullable=False)
    auto_order = db.Column(db.Boolean, default=False, nullable=False)
    
    # User association
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    orders = db.relationship('OnDemandOrder', backref='product', lazy=True)
    
    @property
    def profit_margin(self):
        """Calculate profit margin"""
        if self.base_price and self.selling_price:
            profit = self.selling_price - self.base_price
            return (profit / self.selling_price) * 100
        return 0
    
    @property
    def total_orders(self):
        """Get total number of orders"""
        return len(self.orders)
    
    @property
    def pending_orders(self):
        """Get number of pending orders"""
        return len([order for order in self.orders if order.status == 'pending'])
    
    def __repr__(self):
        return f'<OnDemandProduct {self.name}>'


class OnDemandOrder(db.Model):
    """On-demand order model"""
    __tablename__ = 'on_demand_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, db.ForeignKey('on_demand_products.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Order details
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Customer information (if not registered customer)
    customer_name = db.Column(db.String(200), nullable=True)
    customer_phone = db.Column(db.String(20), nullable=True)
    customer_email = db.Column(db.String(320), nullable=True)
    
    # Order status
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, ordered, received, delivered, cancelled
    
    # Supplier order details
    supplier_order_date = db.Column(db.Date, nullable=True)
    expected_delivery_date = db.Column(db.Date, nullable=True)
    actual_delivery_date = db.Column(db.Date, nullable=True)
    supplier_reference = db.Column(db.String(100), nullable=True)
    
    # Payment
    payment_status = db.Column(db.String(20), default='pending', nullable=False)  # pending, paid, refunded
    payment_method = db.Column(db.String(50), nullable=True)
    
    # Notes
    notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def customer_display_name(self):
        """Get customer name for display"""
        if self.customer:
            return self.customer.name
        return self.customer_name or 'Unknown Customer'
    
    @property
    def is_overdue(self):
        """Check if order is overdue"""
        if self.expected_delivery_date and self.status not in ['delivered', 'cancelled']:
            return datetime.now().date() > self.expected_delivery_date
        return False
    
    def update_status(self, new_status, notes=None):
        """Update order status"""
        self.status = new_status
        if notes:
            self.notes = notes
        self.updated_at = datetime.utcnow()
        
        # Update delivery date if delivered
        if new_status == 'delivered':
            self.actual_delivery_date = datetime.now().date()
    
    def __repr__(self):
        return f'<OnDemandOrder {self.id}: {self.quantity}x {self.product.name if self.product else "Unknown"}>'