from datetime import datetime
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    sales = db.relationship('Sale', backref='user', lazy=True)
    financial_transactions = db.relationship('FinancialTransaction', backref='user', lazy=True)
    locations = db.relationship('Location', backref='owner', lazy=True)
    
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
        return f'<JournalEntry {self.account.account_name}: D{self.debit_amount} C{self.credit_amount}>'

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
        return f'<GeneralLedger {self.account.account_name}>'

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
