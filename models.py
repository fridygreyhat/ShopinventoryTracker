from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sales = db.relationship('Sale', backref='user', lazy=True)
    financial_transactions = db.relationship('FinancialTransaction', backref='user', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    items = db.relationship('Item', backref='category', lazy=True)
    
    def __repr__(self):
        return f'<Category {self.name}>'

class Item(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    price = db.Column(db.Numeric(10, 2), nullable=False)
    cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    minimum_stock = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sale_items = db.relationship('SaleItem', backref='item', lazy=True)
    stock_movements = db.relationship('StockMovement', backref='item', lazy=True)
    
    @property
    def is_low_stock(self):
        return self.stock_quantity <= self.minimum_stock
    
    @property
    def profit_margin(self):
        if self.cost > 0:
            return ((self.price - self.cost) / self.price) * 100
        return 0
    
    def __repr__(self):
        return f'<Item {self.name}>'

class Sale(db.Model):
    __tablename__ = 'sales'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_number = db.Column(db.String(50), unique=True, nullable=False)
    subtotal = db.Column(db.Numeric(10, 2), nullable=False)
    tax_rate = db.Column(db.Numeric(5, 4), nullable=False, default=0)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    payment_method = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='completed')
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    sale_items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')
    
    def __repr__(self):
        return f'<Sale {self.sale_number}>'

class SaleItem(db.Model):
    __tablename__ = 'sale_items'
    
    id = db.Column(db.Integer, primary_key=True)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Numeric(10, 2), nullable=False)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    
    def __repr__(self):
        return f'<SaleItem {self.item.name} x{self.quantity}>'

class StockMovement(db.Model):
    __tablename__ = 'stock_movements'
    
    id = db.Column(db.Integer, primary_key=True)
    movement_type = db.Column(db.String(20), nullable=False)  # 'in', 'out', 'adjustment'
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.String(200), nullable=False)
    notes = db.Column(db.Text)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<StockMovement {self.movement_type} {self.quantity}>'

class FinancialTransaction(db.Model):
    __tablename__ = 'financial_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    transaction_number = db.Column(db.String(50), unique=True, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'income', 'expense'
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    tax_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    description = db.Column(db.String(500), nullable=False)
    notes = db.Column(db.Text)
    reference_number = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<FinancialTransaction {self.transaction_number}>'
