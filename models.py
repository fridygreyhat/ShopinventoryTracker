from datetime import datetime, timedelta
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db

class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(320), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    shop_name = db.Column(db.String(128), nullable=True)
    product_categories = db.Column(db.String(512), nullable=True)
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    role = db.Column(db.String(50), default='user', nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # User Preferences
    language = db.Column(db.String(10), default='en', nullable=False)
    currency_format = db.Column(db.String(10), default='TSh', nullable=False)
    date_format = db.Column(db.String(20), default='DD/MM/YYYY', nullable=False)
    timezone = db.Column(db.String(50), default='Africa/Dar_es_Salaam', nullable=False)
    
    # Notification Settings
    email_notifications = db.Column(db.Boolean, default=True, nullable=False)
    sms_notifications = db.Column(db.Boolean, default=False, nullable=False)
    low_stock_alerts = db.Column(db.Boolean, default=True, nullable=False)
    sales_reports = db.Column(db.Boolean, default=True, nullable=False)
    
    # Business Settings
    business_type = db.Column(db.String(100), default='retail', nullable=False)
    default_tax_rate = db.Column(db.Numeric(5, 2), default=0, nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=10, nullable=False)
    
    # Password Reset
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    # Email Verification
    email_verification_token = db.Column(db.String(255), nullable=True)
    email_verification_token_expires = db.Column(db.DateTime, nullable=True)
    
    # Permissions
    permissions = db.Column(db.Text, nullable=True)  # JSON string of permissions
    last_login = db.Column(db.DateTime, nullable=True)
    login_attempts = db.Column(db.Integer, default=0, nullable=False)
    locked_until = db.Column(db.DateTime, nullable=True)
    
    # Subuser Management
    parent_user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    is_subuser = db.Column(db.Boolean, default=False, nullable=False)
    subuser_permissions = db.Column(db.Text, nullable=True)  # JSON string of specific subuser permissions
    
    # Relationships
    sales = db.relationship('Sale', backref='user', lazy=True)
    financial_transactions = db.relationship('FinancialTransaction', backref='user', lazy=True)
    locations = db.relationship('Location', backref='owner', lazy=True)
    
    # Subuser relationships
    subusers = db.relationship('User', 
                              foreign_keys=[parent_user_id],
                              backref=db.backref('parent_user', remote_side='User.id'),
                              lazy='dynamic')

    
    @property
    def is_active(self):
        return self.active
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"
    
    def has_permission(self, permission):
        """Check if user has a specific permission"""
        if self.is_admin:
            return True
        
        import json
        if self.permissions:
            try:
                user_perms = json.loads(self.permissions)
                return permission in user_perms
            except json.JSONDecodeError:
                return False
        return False
    
    def add_permission(self, permission):
        """Add a permission to the user"""
        import json
        if self.permissions:
            try:
                user_perms = json.loads(self.permissions)
            except json.JSONDecodeError:
                user_perms = []
        else:
            user_perms = []
        
        if permission not in user_perms:
            user_perms.append(permission)
            self.permissions = json.dumps(user_perms)
    
    def remove_permission(self, permission):
        """Remove a permission from the user"""
        import json
        if self.permissions:
            try:
                user_perms = json.loads(self.permissions)
                if permission in user_perms:
                    user_perms.remove(permission)
                    self.permissions = json.dumps(user_perms)
            except json.JSONDecodeError:
                pass
    
    def get_effective_user(self):
        """Get the effective user for data access (parent user for subusers)"""
        if self.is_subuser and self.parent_user:
            return self.parent_user
        return self
    
    def can_manage_subusers(self):
        """Check if user can manage subusers"""
        return not self.is_subuser and (self.is_admin or self.has_permission('manage_subusers'))
    
    def get_subuser_permissions(self):
        """Get subuser specific permissions"""
        if not self.is_subuser:
            return []
        
        import json
        if self.subuser_permissions:
            try:
                return json.loads(self.subuser_permissions)
            except json.JSONDecodeError:
                return []
        return []
    
    def set_subuser_permissions(self, permissions):
        """Set subuser specific permissions"""
        import json
        self.subuser_permissions = json.dumps(permissions)
    
    def has_subuser_permission(self, permission):
        """Check if subuser has specific permission"""
        if not self.is_subuser:
            return True
        
        if self.is_admin:
            return True
            
        subuser_perms = self.get_subuser_permissions()
        return permission in subuser_perms
    
    def generate_email_verification_token(self):
        """Generate email verification token"""
        import secrets
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_token_expires = datetime.utcnow() + timedelta(hours=24)
        return self.email_verification_token
    
    def verify_email_token(self, token):
        """Verify email verification token"""
        if (self.email_verification_token == token and 
            self.email_verification_token_expires and 
            datetime.utcnow() < self.email_verification_token_expires):
            self.email_verified = True
            self.email_verification_token = None
            self.email_verification_token_expires = None
            return True
        return False
    
    def get_all_subusers(self):
        """Get all subusers for this user"""
        if self.is_subuser:
            return []
        return self.subusers.all()
    
    def create_subuser(self, username, email, password, first_name, last_name, permissions=None):
        """Create a new subuser"""
        if not self.can_manage_subusers():
            raise ValueError("User cannot manage subusers")
        
        # Check if username/email already exists
        if User.query.filter_by(username=username).first():
            raise ValueError("Username already exists")
        if User.query.filter_by(email=email).first():
            raise ValueError("Email already exists")
        
        subuser = User(
            username=username,
            email=email,
            first_name=first_name,
            last_name=last_name,
            parent_user_id=self.id,
            is_subuser=True,
            shop_name=self.shop_name,
            business_type=self.business_type
        )
        subuser.set_password(password)
        
        if permissions:
            subuser.set_subuser_permissions(permissions)
        
        return subuser
    
    def get_permissions(self):
        """Get all user permissions"""
        import json
        if self.is_admin:
            return ['admin', 'manage_users', 'manage_inventory', 'manage_sales', 'manage_finances', 'view_reports']
        
        if self.permissions:
            try:
                return json.loads(self.permissions)
            except json.JSONDecodeError:
                return []
        return []
    
    @property
    def is_locked(self):
        """Check if user account is locked"""
        if self.locked_until:
            return datetime.utcnow() < self.locked_until
        return False
    
    def lock_account(self, minutes=30):
        """Lock user account for specified minutes"""
        self.locked_until = datetime.utcnow() + timedelta(minutes=minutes)
        self.login_attempts = 0
    
    def unlock_account(self):
        """Unlock user account"""
        self.locked_until = None
        self.login_attempts = 0
    
    def record_login_attempt(self, success=False):
        """Record login attempt"""
        if success:
            self.login_attempts = 0
            self.last_login = datetime.utcnow()
        else:
            self.login_attempts += 1
            if self.login_attempts >= 5:  # Lock after 5 failed attempts
                self.lock_account(30)  # Lock for 30 minutes
    
    def __repr__(self):
        return f'<User {self.username}>'

class Category(db.Model):
    __tablename__ = 'categories'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    parent_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    sort_order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Self-referential relationship for subcategories
    subcategories = db.relationship('Category', backref=db.backref('parent', remote_side=[id]), lazy=True)
    
    # Relationships
    items = db.relationship('Item', backref='category', lazy=True)
    
    # Unique constraint for name within the same parent
    __table_args__ = (db.UniqueConstraint('name', 'parent_id', name='unique_category_name_per_parent'),)
    
    @property
    def full_name(self):
        """Return the full hierarchical name"""
        if self.parent:
            return f"{self.parent.full_name} > {self.name}"
        return self.name
    
    @property
    def level(self):
        """Return the depth level of this category"""
        if self.parent:
            return self.parent.level + 1
        return 0
    
    @property
    def is_root(self):
        """Check if this is a root category"""
        return self.parent_id is None
    
    @property
    def has_children(self):
        """Check if this category has subcategories"""
        return len(self.subcategories) > 0
    
    def get_all_items(self):
        """Get all items in this category and its subcategories"""
        items = list(self.items)
        for subcategory in self.subcategories:
            items.extend(subcategory.get_all_items())
        return items
    
    def get_descendants(self):
        """Get all descendant categories"""
        descendants = []
        for subcategory in self.subcategories:
            descendants.append(subcategory)
            descendants.extend(subcategory.get_descendants())
        return descendants
    
    def __repr__(self):
        return f'<Category {self.full_name}>'

class Item(db.Model):
    __tablename__ = 'items'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String(50), unique=True, nullable=False)
    buying_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    wholesale_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    retail_price = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    price = db.Column(db.Numeric(10, 2), nullable=False)  # Default selling price
    cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)  # Legacy field
    stock_quantity = db.Column(db.Integer, nullable=False, default=0)
    minimum_stock = db.Column(db.Integer, nullable=False, default=0)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sale_items = db.relationship('SaleItem', lazy=True)
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
    payment_type = db.Column(db.String(20), nullable=False, default='cash')  # 'cash', 'installment', 'other'
    payment_method = db.Column(db.String(50), nullable=False)
    payment_status = db.Column(db.String(20), nullable=False, default='paid')  # 'paid', 'partial', 'pending'
    status = db.Column(db.String(20), nullable=False, default='completed')
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
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
    unit_cost = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    total_price = db.Column(db.Numeric(10, 2), nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    
    # Relationship to Item
    item = db.relationship('Item')
    
    def __repr__(self):
        return f'<SaleItem {self.item.name if self.item else "Unknown"} x{self.quantity}>'

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

class Location(db.Model):
    __tablename__ = 'locations'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text)
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    manager_name = db.Column(db.String(100))
    location_type = db.Column(db.String(50), nullable=False, default='store')  # 'store', 'warehouse', 'outlet'
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    location_stock = db.relationship('LocationStock', backref='location', lazy=True, cascade='all, delete-orphan')
    stock_transfers_from = db.relationship('StockTransfer', foreign_keys='StockTransfer.from_location_id', backref='from_location', lazy=True)
    stock_transfers_to = db.relationship('StockTransfer', foreign_keys='StockTransfer.to_location_id', backref='to_location', lazy=True)
    
    def __repr__(self):
        return f'<Location {self.name}>'

class LocationStock(db.Model):
    __tablename__ = 'location_stock'
    
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False, default=0)
    reserved_quantity = db.Column(db.Integer, nullable=False, default=0)
    min_stock_level = db.Column(db.Integer, nullable=False, default=0)
    max_stock_level = db.Column(db.Integer, nullable=False, default=0)
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Unique constraint to prevent duplicate item-location combinations
    __table_args__ = (db.UniqueConstraint('item_id', 'location_id', name='unique_item_location'),)
    
    @property
    def is_low_stock(self):
        return self.quantity <= self.min_stock_level
    
    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity
    
    def __repr__(self):
        return f'<LocationStock Item:{self.item_id} at Location:{self.location_id}>'

class StockTransfer(db.Model):
    __tablename__ = 'stock_transfers'
    
    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(50), unique=True, nullable=False)
    from_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    to_location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'in_transit', 'completed', 'cancelled'
    notes = db.Column(db.Text)
    initiated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    
    # Relationships
    transfer_items = db.relationship('StockTransferItem', backref='transfer', lazy=True, cascade='all, delete-orphan')
    initiated_by_user = db.relationship('User', backref='initiated_transfers')
    
    def __repr__(self):
        return f'<StockTransfer {self.transfer_number}>'

class StockTransferItem(db.Model):
    __tablename__ = 'stock_transfer_items'
    
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('stock_transfers.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('items.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    
    # Relationship to Item
    item = db.relationship('Item')
    
    def __repr__(self):
        return f'<StockTransferItem {self.item.name if self.item else "Unknown"} x{self.quantity}>'

# Financial Accounting Models

class ChartOfAccounts(db.Model):
    __tablename__ = 'chart_of_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    account_code = db.Column(db.String(20), nullable=False)
    account_name = db.Column(db.String(200), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)  # Asset, Liability, Equity, Revenue, Expense
    parent_account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Self-referential relationship for account hierarchy
    children = db.relationship('ChartOfAccounts', backref=db.backref('parent', remote_side=[id]))
    
    # Relationships
    journal_entries = db.relationship('JournalEntry', backref='account', lazy=True)
    ledger_entries = db.relationship('GeneralLedger', backref='account', lazy=True)
    
    def __repr__(self):
        return f'<Account {self.account_code}: {self.account_name}>'

class Journal(db.Model):
    __tablename__ = 'journals'
    
    id = db.Column(db.Integer, primary_key=True)
    journal_number = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date, default=datetime.utcnow, nullable=False)
    description = db.Column(db.Text, nullable=False)
    reference_type = db.Column(db.String(50))  # 'sale', 'purchase', 'transfer', 'manual'
    reference_id = db.Column(db.String(100))
    total_debit = db.Column(db.Numeric(15, 2), nullable=False)
    total_credit = db.Column(db.Numeric(15, 2), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    entries = db.relationship('JournalEntry', backref='journal', lazy=True, cascade='all, delete-orphan')
    
    @staticmethod
    def generate_journal_number():
        """Generate unique journal number"""
        import time
        return f"JE{int(time.time())}"
    
    def __repr__(self):
        return f'<Journal {self.journal_number}>'

class JournalEntry(db.Model):
    __tablename__ = 'journal_entries'
    
    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journals.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'), nullable=False)
    debit_amount = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    credit_amount = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    description = db.Column(db.Text)
    
    def __repr__(self):
        return f'<JournalEntry Account {self.account_id}: D{self.debit_amount} C{self.credit_amount}>'

class GeneralLedger(db.Model):
    __tablename__ = 'general_ledger'
    
    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journals.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'), nullable=False)
    debit_amount = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    credit_amount = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    journal = db.relationship('Journal', backref='ledger_entries')
    
    def __repr__(self):
        return f'<GeneralLedger Account {self.account_id}: D{self.debit_amount} C{self.credit_amount}>'

class CashFlow(db.Model):
    __tablename__ = 'cash_flow'
    
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    cash_in = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    cash_out = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    net_cash_flow = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    accumulated_cash = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    source = db.Column(db.String(200))
    category = db.Column(db.String(100))  # 'operations', 'investing', 'financing'
    reference_id = db.Column(db.String(100))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<CashFlow {self.date}: Net {self.net_cash_flow}>'

class BalanceSheet(db.Model):
    __tablename__ = 'balance_sheets'
    
    id = db.Column(db.Integer, primary_key=True)
    as_of_date = db.Column(db.Date, nullable=False)
    total_assets = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    total_liabilities = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    total_equity = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    cash_and_equivalents = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    inventory_value = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<BalanceSheet {self.as_of_date}>'

class BankAccount(db.Model):
    __tablename__ = 'bank_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(200), nullable=False)
    account_number = db.Column(db.String(50))
    bank_name = db.Column(db.String(200))
    account_type = db.Column(db.String(50))  # 'checking', 'savings', 'credit'
    current_balance = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    transfers_from = db.relationship('BankTransfer', foreign_keys='BankTransfer.from_account_id', backref='from_account')
    transfers_to = db.relationship('BankTransfer', foreign_keys='BankTransfer.to_account_id', backref='to_account')
    
    def __repr__(self):
        return f'<BankAccount {self.account_name}>'

class BankTransfer(db.Model):
    __tablename__ = 'bank_transfers'
    
    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(50), unique=True, nullable=False)
    from_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=False)
    to_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=False)
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    transfer_fee = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    description = db.Column(db.Text)
    status = db.Column(db.String(20), default='completed')  # 'pending', 'completed', 'failed'
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @staticmethod
    def generate_transfer_number():
        """Generate unique transfer number"""
        import time
        return f"TRF{int(time.time())}"
    
    def __repr__(self):
        return f'<BankTransfer {self.transfer_number}: {self.amount}>'

class BankReconciliation(db.Model):
    __tablename__ = 'bank_reconciliations'
    
    id = db.Column(db.Integer, primary_key=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=False)
    statement_date = db.Column(db.Date, nullable=False)
    statement_balance = db.Column(db.Numeric(15, 2), nullable=False)
    book_balance = db.Column(db.Numeric(15, 2), nullable=False)
    reconciled_balance = db.Column(db.Numeric(15, 2), nullable=False)
    outstanding_deposits = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    outstanding_checks = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    is_reconciled = db.Column(db.Boolean, default=False, nullable=False)
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    bank_account = db.relationship('BankAccount', backref='reconciliations')
    
    def __repr__(self):
        return f'<BankReconciliation {self.statement_date}>'

class BranchEquity(db.Model):
    __tablename__ = 'branch_equity'
    
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('locations.id'), nullable=False)
    equity_date = db.Column(db.Date, nullable=False)
    contributed_capital = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    retained_earnings = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    total_equity = db.Column(db.Numeric(15, 2), default=0, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship
    location = db.relationship('Location', backref='equity_records')
    
    def __repr__(self):
        return f'<BranchEquity {self.location.name}: {self.total_equity}>'


# Customer Management Models
class Customer(db.Model):
    """Customer profile model"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True)
    phone = db.Column(db.String(20))
    address = db.Column(db.Text)
    date_of_birth = db.Column(db.Date)
    customer_type = db.Column(db.String(20), default='retail')  # 'retail', 'wholesale', 'vip'
    
    # Loyalty program
    loyalty_points = db.Column(db.Integer, default=0)
    loyalty_tier = db.Column(db.String(20), default='bronze')  # 'bronze', 'silver', 'gold', 'platinum'
    
    # Credit management
    credit_limit = db.Column(db.Float, default=0.0)
    current_credit = db.Column(db.Float, default=0.0)
    
    # Preferences
    preferred_payment_method = db.Column(db.String(50))
    marketing_consent = db.Column(db.Boolean, default=True)
    
    # User association
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_purchase_date = db.Column(db.DateTime)
    
    # Relationships
    purchases = db.relationship('Sale', backref='customer_profile', lazy=True, foreign_keys='Sale.customer_id')
    
    def __repr__(self):
        return f'<Customer {self.name}>'
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'email': self.email,
            'phone': self.phone,
            'address': self.address,
            'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
            'customer_type': self.customer_type,
            'loyalty_points': self.loyalty_points,
            'loyalty_tier': self.loyalty_tier,
            'credit_limit': self.credit_limit,
            'current_credit': self.current_credit,
            'preferred_payment_method': self.preferred_payment_method,
            'marketing_consent': self.marketing_consent,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_purchase_date': self.last_purchase_date.isoformat() if self.last_purchase_date else None
        }


class CustomerPurchaseHistory(db.Model):
    """Detailed customer purchase history"""
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    purchase_amount = db.Column(db.Float, nullable=False)
    loyalty_points_earned = db.Column(db.Integer, default=0)
    loyalty_points_used = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('Customer', backref='purchase_history')
    sale = db.relationship('Sale', backref='customer_purchase')


class LoyaltyTransaction(db.Model):
    """Loyalty points transactions"""
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'earned', 'redeemed', 'expired'
    points = db.Column(db.Integer, nullable=False)
    description = db.Column(db.String(255))
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    customer = db.relationship('Customer', backref='loyalty_transactions')


# Installment Payment Models
class InstallmentPlan(db.Model):
    __tablename__ = 'installment_plans'
    
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sales.id'), nullable=False)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    total_amount = db.Column(db.Numeric(10, 2), nullable=False)
    down_payment = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    remaining_amount = db.Column(db.Numeric(10, 2), nullable=False)
    number_of_installments = db.Column(db.Integer, nullable=False)
    installment_amount = db.Column(db.Numeric(10, 2), nullable=False)
    frequency = db.Column(db.String(20), nullable=False, default='monthly')  # 'weekly', 'monthly'
    start_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='active')  # 'active', 'completed', 'defaulted'
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    installments = db.relationship('Installment', backref='plan', lazy=True, cascade='all, delete-orphan')
    customer = db.relationship('Customer', backref='installment_plans')
    
    @property
    def paid_amount(self):
        return sum(float(installment.paid_amount) for installment in self.installments if installment.status == 'paid')
    
    @property
    def outstanding_amount(self):
        return float(self.total_amount) - self.paid_amount
    
    @property
    def next_due_date(self):
        unpaid_installments = [i for i in self.installments if i.status == 'pending']
        if unpaid_installments:
            return min(i.due_date for i in unpaid_installments)
        return None
    
    def __repr__(self):
        return f'<InstallmentPlan {self.id} - {self.customer.name if self.customer else "Unknown"}>'


class Installment(db.Model):
    __tablename__ = 'installments'
    
    id = db.Column(db.Integer, primary_key=True)
    plan_id = db.Column(db.Integer, db.ForeignKey('installment_plans.id'), nullable=False)
    installment_number = db.Column(db.Integer, nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    due_date = db.Column(db.Date, nullable=False)
    paid_date = db.Column(db.Date, nullable=True)
    paid_amount = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    status = db.Column(db.String(20), nullable=False, default='pending')  # 'pending', 'paid', 'overdue'
    late_fee = db.Column(db.Numeric(10, 2), nullable=False, default=0)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    @property
    def is_overdue(self):
        from datetime import date
        return self.status == 'pending' and self.due_date < date.today()
    
    @property
    def days_overdue(self):
        if self.is_overdue:
            from datetime import date
            return (date.today() - self.due_date).days
        return 0
    
    def __repr__(self):
        return f'<Installment {self.installment_number} - ${self.amount}>'


class OnDemandProduct(db.Model):
    """On-demand products that can be ordered when not in stock"""
    __tablename__ = 'on_demand_products'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('categories.id'), nullable=True)
    
    # Pricing
    estimated_cost = db.Column(db.Float, nullable=False, default=0.0)
    selling_price = db.Column(db.Float, nullable=False, default=0.0)
    
    # Supplier information
    supplier_name = db.Column(db.String(100))
    supplier_contact = db.Column(db.String(100))
    estimated_delivery_days = db.Column(db.Integer, default=7)
    
    # Order tracking
    minimum_order_quantity = db.Column(db.Integer, default=1)
    is_active = db.Column(db.Boolean, default=True)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    category = db.relationship('Category', backref='on_demand_products')
    
    def __repr__(self):
        return f'<OnDemandProduct {self.name}>'


class OnDemandOrder(db.Model):
    """Orders for on-demand products"""
    __tablename__ = 'on_demand_orders'
    
    id = db.Column(db.Integer, primary_key=True)
    order_number = db.Column(db.String(50), unique=True, nullable=False)
    
    # Product and quantity
    product_id = db.Column(db.Integer, db.ForeignKey('on_demand_products.id'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    unit_price = db.Column(db.Float, nullable=False)
    total_amount = db.Column(db.Float, nullable=False)
    
    # Customer information
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=True)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    customer_email = db.Column(db.String(120))
    
    # Order status and tracking
    status = db.Column(db.String(20), default='pending')  # pending, ordered, received, delivered, cancelled
    payment_status = db.Column(db.String(20), default='pending')  # pending, paid, partial
    payment_method = db.Column(db.String(50))
    
    # Important dates
    order_date = db.Column(db.DateTime, default=datetime.utcnow)
    expected_delivery_date = db.Column(db.Date)
    actual_delivery_date = db.Column(db.Date)
    
    # Additional information
    notes = db.Column(db.Text)
    advance_payment = db.Column(db.Float, default=0.0)
    remaining_payment = db.Column(db.Float, default=0.0)
    
    # Relationships
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    product = db.relationship('OnDemandProduct', backref='orders')
    customer = db.relationship('Customer', backref='on_demand_orders')
    
    def __repr__(self):
        return f'<OnDemandOrder {self.order_number}>'
