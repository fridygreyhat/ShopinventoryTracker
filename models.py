from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import enum
from flask_login import UserMixin


# Import db from extensions to avoid circular imports
from extensions import db

class User(UserMixin, db.Model):
    __tablename__ = 'user'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    phone = db.Column(db.String(20))
    shop_name = db.Column(db.String(128))
    product_categories = db.Column(db.String(512))
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    verification_token = db.Column(db.String(64))
    verification_token_expires = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        """Set password hash using werkzeug's secure method"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)

    def get_username(self):
        """Return username or email as fallback"""
        return self.username if hasattr(self, 'username') and self.username else self.email

    def to_dict(self):
        """Convert user to dictionary with complete information"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'shop_name': self.shop_name,
            'product_categories': self.product_categories,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }
    
    def __repr__(self):
        return f'<User {self.username}>'

class Item(db.Model):
    __tablename__ = 'item'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, index=True)
    description = db.Column(db.Text)
    sku = db.Column(db.String(50), unique=True, index=True)
    
    # Unified quantity and pricing fields
    stock_quantity = db.Column(db.Integer, default=0, nullable=False)
    minimum_stock = db.Column(db.Integer, default=0, nullable=False)
    buying_price = db.Column(db.Float, default=0.0, nullable=False)
    retail_price = db.Column(db.Float, default=0.0, nullable=False)
    wholesale_price = db.Column(db.Float, default=0.0, nullable=False)
    
    # Product classification
    sales_type = db.Column(db.String(20), default='both', nullable=False)
    category = db.Column(db.String(100), default='Uncategorized')
    subcategory = db.Column(db.String(100))
    unit_type = db.Column(db.String(20), default='quantity')
    sell_by = db.Column(db.String(20), default='quantity')
    
    # Foreign keys with proper constraints
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    
    # Status and metadata
    is_active = db.Column(db.Boolean, default=True, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships
    category_rel = db.relationship('Category', backref='items')
    user = db.relationship('User', backref=db.backref('items', lazy=True))

    @staticmethod
    def generate_sku(name, category=""):
        import string
        import random
        base = f"{category[:3].upper()}{name[:3].upper()}"
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"{base}-{random_part}"

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'sku': self.sku,
            'stock_quantity': self.stock_quantity,
            'quantity': self.stock_quantity,  # Backward compatibility
            'minimum_stock': self.minimum_stock,
            'buying_price': float(self.buying_price or 0),
            'retail_price': float(self.retail_price or 0),
            'wholesale_price': float(self.wholesale_price or 0),
            'price': float(self.retail_price or 0),  # Backward compatibility
            'selling_price_retail': float(self.retail_price or 0),  # Frontend expects this
            'selling_price_wholesale': float(self.wholesale_price or 0),  # Frontend expects this
            'sales_type': self.sales_type,
            'category': self.category,
            'subcategory': self.subcategory,
            'category_id': self.category_id,
            'unit_type': self.unit_type,
            'sell_by': self.sell_by,
            'user_id': self.user_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Setting(db.Model):
    __tablename__ = 'setting'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False, index=True)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='general', index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    
    # Relationships  
    user = db.relationship('User', backref='settings', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'category': self.category,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Placeholder classes for other models referenced in app.py
class Subuser(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256))
    parent_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'is_active': self.is_active,
            'permissions': []
        }

class SubuserPermission(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    subuser_id = db.Column(db.Integer, db.ForeignKey('subuser.id'), nullable=False)
    permission = db.Column(db.String(100), nullable=False)
    granted = db.Column(db.Boolean, default=True)

class Sale(db.Model):
    __tablename__ = 'sale'
    
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False, index=True)
    sale_number = db.Column(db.String(50), unique=True, index=True)
    
    # Customer information
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    
    # Sale details
    sale_type = db.Column(db.String(20), default='retail', nullable=False)
    subtotal = db.Column(db.Float, default=0.0, nullable=False)
    discount_type = db.Column(db.String(20), default='none')
    discount_value = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0, nullable=False)
    
    # Payment information
    payment_method = db.Column(db.String(20), default='cash', nullable=False)
    payment_type = db.Column(db.String(20), default='cash', nullable=False)
    payment_status = db.Column(db.String(20), default='completed', nullable=False)
    payment_details = db.Column(db.Text)
    payment_amount = db.Column(db.Float, default=0.0)
    change_amount = db.Column(db.Float, default=0.0)
    
    # Additional information
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    sale_items = db.relationship('SaleItem', backref='sale', lazy=True, cascade='all, delete-orphan')
    customer = db.relationship('Customer', backref='sales', lazy=True)
    user = db.relationship('User', backref='sales', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'sale_number': self.sale_number,
            'customer_name': self.customer_name,
            'customer_id': self.customer_id,
            'sale_type': self.sale_type,
            'subtotal': self.subtotal,
            'discount_amount': self.discount_amount,
            'total_amount': self.total_amount,
            'payment_method': self.payment_method,
            'payment_type': self.payment_type,
            'payment_status': self.payment_status,
            'payment_amount': self.payment_amount,
            'change_amount': self.change_amount,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SaleItem(db.Model):
    __tablename__ = 'sale_item'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False, index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False, index=True)
    quantity = db.Column(db.Float, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    unit_cost = db.Column(db.Float, default=0.0)
    total_price = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    
    # Relationships
    item = db.relationship('Item', backref='sale_items', lazy=True)
    
    # Constraints
    __table_args__ = (
        db.UniqueConstraint('sale_id', 'item_id', name='unique_sale_item'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'item_id': self.item_id,
            'quantity': self.quantity,
            'unit_price': self.unit_price,
            'unit_cost': self.unit_cost,
            'total_price': self.total_price,
            'item_name': self.item.name if self.item else None,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Redundant relationship definition removed - already defined in Sale model

class FinancialTransaction(db.Model):
    __tablename__ = 'financial_transaction'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, index=True)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False, index=True)
    category = db.Column(db.String(100))
    reference_id = db.Column(db.String(100))
    payment_method = db.Column(db.String(50))
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False, index=True)
    
    # Relationships
    user = db.relationship('User', backref='financial_transactions', lazy=True)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'amount': self.amount,
            'transaction_type': self.transaction_type,
            'category': self.category,
            'reference_id': self.reference_id,
            'payment_method': self.payment_method,
            'notes': self.notes,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

# Placeholder classes for other models
class Category(db.Model):
    __tablename__ = 'category'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('category.id'))
    sort_order = db.Column(db.Integer, default=0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('categories', lazy=True))
    parent = db.relationship('Category', remote_side=[id], backref='children')
    # Items relationship handled by foreign key in Item model

    def get_descendants(self):
        """Get all descendant categories"""
        descendants = []
        for child in self.children:
            descendants.append(child)
            descendants.extend(child.get_descendants())
        return descendants

    def get_all_items(self):
        """Get all items in this category and subcategories"""
        items = list(self.items)
        for child in self.children:
            items.extend(child.get_all_items())
        return items

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'parent_id': self.parent_id,
            'sort_order': self.sort_order,
            'user_id': self.user_id,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Customer(db.Model):
    __tablename__ = 'customer'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    customer_type = db.Column(db.String(20), default='retail')  # retail, wholesale
    credit_limit = db.Column(db.Float, default=0.0)
    loyalty_points = db.Column(db.Integer, default=0)
    preferred_payment_method = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = db.relationship('User', backref=db.backref('customers', lazy=True))

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'customer_type': self.customer_type,
            'credit_limit': self.credit_limit,
            'loyalty_points': self.loyalty_points,
            'preferred_payment_method': self.preferred_payment_method,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class OnDemandProduct(db.Model):
    __tablename__ = 'on_demand_product'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    base_price = db.Column(db.Float, default=0.0)
    production_time = db.Column(db.Integer, default=0)  # in days
    category = db.Column(db.String(50))
    materials = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'base_price': self.base_price,
            'production_time': self.production_time,
            'category': self.category,
            'materials': self.materials,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Missing models that are referenced in the app
class StockMovement(db.Model):
    __tablename__ = 'stock_movement'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    movement_type = db.Column(db.String(20), nullable=False)  # 'in' or 'out'
    quantity = db.Column(db.Float, nullable=False)
    reason = db.Column(db.String(200))
    reference_id = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    item = db.relationship('Item', backref='movements', lazy=True)
    user = db.relationship('User', backref='stock_movements', lazy=True)

class ChartOfAccounts(db.Model):
    __tablename__ = 'chart_of_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    account_code = db.Column(db.String(20), unique=True, nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)  # Asset, Liability, Equity, Revenue, Expense
    parent_account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'))
    balance = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='chart_accounts')
    parent_account = db.relationship('ChartOfAccounts', remote_side=[id], backref='child_accounts')
    
    def to_dict(self):
        return {
            'id': self.id,
            'account_code': self.account_code,
            'account_name': self.account_name,
            'account_type': self.account_type,
            'parent_account_id': self.parent_account_id,
            'balance': float(self.balance or 0),
            'is_active': self.is_active,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Journal(db.Model):
    __tablename__ = 'journal'
    
    id = db.Column(db.Integer, primary_key=True)
    journal_number = db.Column(db.String(50), unique=True, nullable=False)
    description = db.Column(db.String(200))
    reference_type = db.Column(db.String(50))
    transaction_group = db.Column(db.String(100))
    entry_date = db.Column(db.Date, nullable=False)
    total_debit = db.Column(db.Float, default=0.0)
    total_credit = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', foreign_keys=[user_id], backref='journals')
    creator = db.relationship('User', foreign_keys=[created_by])
    
    def to_dict(self):
        return {
            'id': self.id,
            'journal_number': self.journal_number,
            'description': self.description,
            'reference_type': self.reference_type,
            'transaction_group': self.transaction_group,
            'entry_date': self.entry_date.isoformat() if self.entry_date else None,
            'total_debit': float(self.total_debit or 0),
            'total_credit': float(self.total_credit or 0),
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class Supplier(db.Model):
    __tablename__ = 'supplier'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    contact_person = db.Column(db.String(100))
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    payment_terms = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='suppliers')
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'contact_person': self.contact_person,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'payment_terms': self.payment_terms,
            'is_active': self.is_active,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class PurchaseOrder(db.Model):
    __tablename__ = 'purchase_order'
    
    id = db.Column(db.Integer, primary_key=True)
    po_number = db.Column(db.String(50), unique=True, nullable=False)
    supplier_id = db.Column(db.Integer, db.ForeignKey('supplier.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')
    total_amount = db.Column(db.Float, default=0.0)
    order_date = db.Column(db.Date, nullable=False)
    expected_date = db.Column(db.Date)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    supplier = db.relationship('Supplier', backref='purchase_orders')
    user = db.relationship('User', backref='purchase_orders')
    
    def to_dict(self):
        return {
            'id': self.id,
            'po_number': self.po_number,
            'supplier_id': self.supplier_id,
            'supplier_name': self.supplier.name if self.supplier else None,
            'status': self.status,
            'total_amount': float(self.total_amount or 0),
            'order_date': self.order_date.isoformat() if self.order_date else None,
            'expected_date': self.expected_date.isoformat() if self.expected_date else None,
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class InstallmentPlan(db.Model):
    __tablename__ = 'installment_plan'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    down_payment = db.Column(db.Float, default=0.0)
    monthly_payment = db.Column(db.Float, nullable=False)
    number_of_payments = db.Column(db.Integer, nullable=False)
    payments_made = db.Column(db.Integer, default=0)
    interest_rate = db.Column(db.Float, default=0.0)
    start_date = db.Column(db.Date, nullable=False)
    next_due_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sale = db.relationship('Sale', backref='installment_plan')
    user = db.relationship('User', backref='installment_plans')
    
    @property
    def outstanding_amount(self):
        """Calculate outstanding amount"""
        paid_amount = self.down_payment + (self.monthly_payment * self.payments_made)
        return max(0, self.total_amount - paid_amount)
    
    def to_dict(self):
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'total_amount': float(self.total_amount or 0),
            'down_payment': float(self.down_payment or 0),
            'monthly_payment': float(self.monthly_payment or 0),
            'number_of_payments': self.number_of_payments,
            'payments_made': self.payments_made,
            'interest_rate': float(self.interest_rate or 0),
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'next_due_date': self.next_due_date.isoformat() if self.next_due_date else None,
            'status': self.status,
            'outstanding_amount': float(self.outstanding_amount),
            'user_id': self.user_id,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

# Enhanced Security Models
class SecurityAudit(db.Model):
    __tablename__ = 'security_audits'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    action = db.Column(db.String(100), nullable=False)
    details = db.Column(db.JSON)
    ip_address = db.Column(db.String(45))
    user_agent = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'action': self.action,
            'details': self.details,
            'ip_address': self.ip_address,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None
        }

class UserTwoFactor(db.Model):
    __tablename__ = 'user_two_factor'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    secret_key = db.Column(db.String(32), nullable=False)
    is_enabled = db.Column(db.Boolean, default=False)
    backup_codes = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# Data Management Models
class PriceHistory(db.Model):
    __tablename__ = 'price_history'

    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    old_price = db.Column(db.Float, nullable=False)
    new_price = db.Column(db.Float, nullable=False)
    change_reason = db.Column(db.String(200))
    changed_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    change_date = db.Column(db.DateTime, default=datetime.utcnow)

class BackupSchedule(db.Model):
    __tablename__ = 'backup_schedules'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    frequency = db.Column(db.String(20), nullable=False)  # daily, weekly, monthly
    next_backup = db.Column(db.DateTime, nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class ArchivedSale(db.Model):
    __tablename__ = 'archived_sales'

    id = db.Column(db.Integer, primary_key=True)
    original_id = db.Column(db.Integer, nullable=False)
    data = db.Column(db.JSON, nullable=False)
    archived_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

class ArchivedTransaction(db.Model):
    __tablename__ = 'archived_transactions'

    id = db.Column(db.Integer, primary_key=True)
    original_id = db.Column(db.Integer, nullable=False)
    data = db.Column(db.JSON, nullable=False)
    archived_date = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

# Team Management Models
class Employee(db.Model):
    __tablename__ = 'employees'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    employee_code = db.Column(db.String(20), unique=True, nullable=False)
    first_name = db.Column(db.String(50), nullable=False)
    last_name = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(120))
    phone = db.Column(db.String(20))
    position = db.Column(db.String(100))
    department = db.Column(db.String(100))
    hire_date = db.Column(db.Date)
    salary = db.Column(db.Float)
    commission_rate = db.Column(db.Float, default=0.0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    permissions = db.relationship('EmployeePermission', backref='employee', lazy=True, cascade='all, delete-orphan')

    def to_dict(self):
        return {
            'id': self.id,
            'employee_code': self.employee_code,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'email': self.email,
            'phone': self.phone,
            'position': self.position,
            'department': self.department,
            'hire_date': self.hire_date.isoformat() if self.hire_date else None,
            'salary': self.salary,
            'commission_rate': self.commission_rate,
            'is_active': self.is_active,
            'permissions': [perm.permission for perm in self.permissions if perm.granted]
        }

class EmployeePermission(db.Model):
    __tablename__ = 'employee_permissions'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    permission = db.Column(db.String(50), nullable=False)
    granted = db.Column(db.Boolean, default=True)
    granted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    granted_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'employee_id': self.employee_id,
            'permission': self.permission,
            'granted': self.granted,
            'granted_at': self.granted_at.isoformat() if self.granted_at else None
        }

class Shift(db.Model):
    __tablename__ = 'shifts'

    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    shift_date = db.Column(db.Date, nullable=False)
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    shift_type = db.Column(db.String(20), default='regular')
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class InventoryTransfer(db.Model):
    __tablename__ = 'inventory_transfers'

    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(50), unique=True, nullable=False)
    from_location_id = db.Column(db.Integer, nullable=False)
    to_location_id = db.Column(db.Integer, nullable=False)
    status = db.Column(db.String(20), default='pending')
    notes = db.Column(db.Text)
    initiated_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    approved_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime)

class InventoryTransferItem(db.Model):
    __tablename__ = 'inventory_transfer_items'

    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('inventory_transfers.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)

# Marketing Models
class EmailCampaign(db.Model):
    __tablename__ = 'email_campaigns'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    subject = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text, nullable=False)
    target_audience = db.Column(db.String(50))
    scheduled_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='draft')
    sent_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SMSCampaign(db.Model):
    __tablename__ = 'sms_campaigns'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    target_audience = db.Column(db.String(50))
    status = db.Column(db.String(20), default='pending')
    sent_count = db.Column(db.Integer, default=0)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class FeedbackRequest(db.Model):
    __tablename__ = 'feedback_requests'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    questions = db.Column(db.JSON, nullable=False)
    target_audience = db.Column(db.String(50))
    expiry_date = db.Column(db.DateTime)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class SocialMediaPost(db.Model):
    __tablename__ = 'social_media_posts'

    id = db.Column(db.Integer, primary_key=True)
    platform = db.Column(db.String(50), nullable=False)
    content = db.Column(db.Text, nullable=False)
    media_urls = db.Column(db.JSON)
    scheduled_date = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='scheduled')
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OnlineStore(db.Model):
    __tablename__ = 'online_stores'

    id = db.Column(db.Integer, primary_key=True)
    store_name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    theme = db.Column(db.String(50), default='default')
    domain = db.Column(db.String(200))
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OnlineStoreProduct(db.Model):
    __tablename__ = 'online_store_products'

    id = db.Column(db.Integer, primary_key=True)
    store_id = db.Column(db.Integer, db.ForeignKey('online_stores.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    is_visible = db.Column(db.Boolean, default=True)
    online_price = db.Column(db.Float)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)