"""
Customer management models
"""
from datetime import datetime
from app import db


class Customer(db.Model):
    """Customer model"""
    __tablename__ = 'customers'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    email = db.Column(db.String(320), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    address = db.Column(db.Text, nullable=True)
    
    # Business information
    company_name = db.Column(db.String(200), nullable=True)
    tax_id = db.Column(db.String(50), nullable=True)
    
    # Customer type and preferences
    customer_type = db.Column(db.String(20), default='retail', nullable=False)  # retail, wholesale
    preferred_payment_method = db.Column(db.String(50), nullable=True)
    credit_limit = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    
    # Status
    active = db.Column(db.Boolean, default=True, nullable=False)
    notes = db.Column(db.Text, nullable=True)
    
    # User association
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sales = db.relationship('Sale', backref='customer', lazy=True)
    installment_plans = db.relationship('InstallmentPlan', backref='customer', lazy=True)
    
    @property
    def total_purchases(self):
        """Calculate total purchase amount"""
        return sum(sale.total_amount for sale in self.sales)
    
    @property
    def outstanding_balance(self):
        """Calculate outstanding installment balance"""
        total_balance = 0
        for plan in self.installment_plans:
            if plan.status == 'active':
                total_balance += plan.balance_remaining
        return total_balance
    
    @property
    def last_purchase_date(self):
        """Get date of last purchase"""
        if self.sales:
            return max(sale.created_at for sale in self.sales)
        return None
    
    def __repr__(self):
        return f'<Customer {self.name}>'