"""
Sales and payment models
"""
from datetime import datetime, date
from decimal import Decimal
from app import db


class Sale(db.Model):
    """Sales transaction model"""
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Sale details
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Payment information
    payment_method = db.Column(db.String(50), default='cash', nullable=False)
    payment_status = db.Column(db.String(20), default='paid', nullable=False)
    amount_paid = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    amount_due = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    
    # Additional information
    notes = db.Column(db.Text, nullable=True)
    receipt_number = db.Column(db.String(50), nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')
    installment_plan = db.relationship('InstallmentPlan', backref='sale', uselist=False, cascade='all, delete-orphan')
    
    @property
    def total_quantity(self):
        """Get total quantity of items sold"""
        return sum(item.quantity for item in self.items)
    
    @property
    def profit(self):
        """Calculate total profit from sale"""
        total_profit = Decimal('0.00')
        for item in self.items:
            if item.item and item.item.cost_price:
                item_profit = (item.unit_price - item.item.cost_price) * item.quantity
                total_profit += item_profit
        return total_profit
    
    @property
    def profit_margin(self):
        """Calculate profit margin percentage"""
        if self.subtotal > 0:
            return (self.profit / self.subtotal) * 100
        return 0
    
    def is_installment_sale(self):
        """Check if this is an installment sale"""
        return self.installment_plan is not None
    
    def __repr__(self):
        return f'<Sale {self.id}: {self.total_amount}>'


class SaleItem(db.Model):
    """Items in a sale"""
    __tablename__ = 'sale_items'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    
    # Item details at time of sale
    item_name = db.Column(db.String(200), nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    
    # Discounts
    discount_percent = db.Column(db.Numeric(5, 2), default=0, nullable=False)
    discount_amount = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    
    @property
    def profit(self):
        """Calculate profit for this sale item"""
        if self.item and self.item.cost_price:
            return (self.unit_price - self.item.cost_price) * self.quantity
        return Decimal('0.00')
    
    def __repr__(self):
        return f'<SaleItem {self.quantity}x {self.item_name}>'


class InstallmentPlan(db.Model):
    """Installment payment plans"""
    __tablename__ = 'installment_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.id'), nullable=False)
    
    # Plan details
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    down_payment = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    remaining_amount = db.Column(db.Numeric(10, 2), nullable=False)
    installment_amount = db.Column(db.Numeric(10, 2), nullable=False)
    number_of_installments = db.Column(db.Integer, nullable=False)
    
    # Interest and fees
    interest_rate = db.Column(db.Numeric(5, 2), default=0, nullable=False)
    late_fee = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    
    # Status
    status = db.Column(db.String(20), default='active', nullable=False)  # active, completed, defaulted
    
    # Timestamps
    start_date = db.Column(db.Date, default=date.today, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    payments = db.relationship('InstallmentPayment', backref='installment_plan', lazy=True, cascade='all, delete-orphan')
    
    @property
    def total_paid(self):
        """Calculate total amount paid so far"""
        paid_amount = sum(payment.amount for payment in self.payments if payment.status == 'paid')
        return self.down_payment + paid_amount
    
    @property
    def balance_remaining(self):
        """Calculate remaining balance"""
        return self.total_amount - self.total_paid
    
    @property
    def is_completed(self):
        """Check if installment plan is fully paid"""
        return self.balance_remaining <= 0
    
    @property
    def overdue_payments(self):
        """Get overdue payments"""
        today = date.today()
        return [p for p in self.payments if p.due_date < today and p.status == 'pending']
    
    def __repr__(self):
        return f'<InstallmentPlan {self.id}: {self.total_amount}>'


class InstallmentPayment(db.Model):
    """Individual installment payments"""
    __tablename__ = 'installment_payments'
    
    id = db.Column(db.Integer, primary_key=True)
    installment_plan_id = db.Column(db.Integer, db.ForeignKey('installment_plans.id'), nullable=False)
    
    # Payment details
    payment_number = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    
    # Payment status
    status = db.Column(db.String(20), default='pending', nullable=False)  # pending, paid, overdue
    paid_date = db.Column(db.Date, nullable=True)
    paid_amount = db.Column(db.Numeric(10, 2), nullable=True)
    
    # Late fees
    late_fee_applied = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    
    # Payment method
    payment_method = db.Column(db.String(50), nullable=True)
    reference_number = db.Column(db.String(100), nullable=True)
    notes = db.Column(db.Text, nullable=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    @property
    def is_overdue(self):
        """Check if payment is overdue"""
        return self.due_date < date.today() and self.status == 'pending'
    
    @property
    def days_overdue(self):
        """Calculate days overdue"""
        if self.is_overdue:
            return (date.today() - self.due_date).days
        return 0
    
    def mark_as_paid(self, amount_paid, payment_method=None, reference=None):
        """Mark payment as paid"""
        self.status = 'paid'
        self.paid_date = date.today()
        self.paid_amount = amount_paid
        if payment_method:
            self.payment_method = payment_method
        if reference:
            self.reference_number = reference
        self.updated_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<InstallmentPayment {self.payment_number}: {self.amount}>'