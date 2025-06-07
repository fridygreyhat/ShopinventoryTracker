from datetime import datetime
import json
from enum import Enum
import random
import string
from app import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin

class Item(db.Model):
    """Item model for inventory items"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    sku = db.Column(db.String(50), unique=True)
    unit_type = db.Column(db.String(20), default='quantity')  # 'quantity' or 'weight'
    description = db.Column(db.Text)
    category = db.Column(db.String(50))  # Legacy string category for backward compatibility
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=True)  # New FK to Category
    subcategory = db.Column(db.String(50))
    sell_by = db.Column(db.String(20), default='quantity')  # 'quantity' or 'kilogram'
    quantity = db.Column(db.Integer, default=0)  # Global/total quantity for backward compatibility
    buying_price = db.Column(db.Float, default=0.0)
    selling_price_retail = db.Column(db.Float, default=0.0)
    selling_price_wholesale = db.Column(db.Float, default=0.0)
    price = db.Column(db.Float, default=0.0)  # For backward compatibility
    sales_type = db.Column(db.String(20), default='both')  # 'retail', 'wholesale', or 'both'
    # Multi-location settings
    track_by_location = db.Column(db.Boolean, default=False)  # Whether to track this item by location
    # User ownership
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Item {self.name}>'

    @staticmethod
    def generate_sku(product_name: str, category: str = "") -> str:
        """
        Generate a unique SKU based on product name and category.

        :param product_name: The name of the product
        :param category: Optional category name
        :return: A unique SKU string
        """
        # Clean and shorten product name
        name_code = ''.join(filter(str.isalnum, product_name.upper()))[:4]

        # Clean and shorten category
        category_code = ''.join(filter(str.isalnum, category.upper()))[:3]

        # Generate random alphanumeric suffix
        suffix = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

        # Format: NAME-CAT-RANDOM
        return f"{name_code}-{category_code}-{suffix}" if category else f"{name_code}-{suffix}"

    def to_dict(self, include_locations=False):
        """Convert item to dictionary for API responses"""
        result = {
            'id': self.id,
            'name': self.name,
            'sku': self.sku or '',
            'unit_type': self.unit_type or 'quantity',
            'description': self.description or '',
            'category': self.category or 'Uncategorized',
            'subcategory': self.subcategory or '',
            'sell_by': self.sell_by or 'quantity',
            'quantity': self.quantity or 0,
            'buying_price': float(self.buying_price or 0),
            'selling_price_retail': float(self.selling_price_retail or 0),
            'selling_price_wholesale': float(self.selling_price_wholesale or 0),
            'price': float(self.price or self.selling_price_retail or 0),  # For backward compatibility
            'sales_type': self.sales_type or 'both',
            'track_by_location': self.track_by_location or False,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }
        
        if include_locations and self.track_by_location:
            result['locations'] = [stock.to_dict() for stock in self.location_stocks]
            result['total_stock_across_locations'] = sum(stock.quantity for stock in self.location_stocks)
        
        return result

    def get_stock_at_location(self, location_id):
        """Get stock quantity at a specific location"""
        if not self.track_by_location:
            return self.quantity
        
        stock = next((s for s in self.location_stocks if s.location_id == location_id), None)
        return stock.quantity if stock else 0

    def get_available_stock_at_location(self, location_id):
        """Get available stock quantity at a specific location (excluding reserved)"""
        if not self.track_by_location:
            return self.quantity
        
        stock = next((s for s in self.location_stocks if s.location_id == location_id), None)
        return stock.available_quantity if stock else 0


from enum import Enum

class UserRole(Enum):
    ADMIN = "admin"
    INVENTORY_MANAGER = "inventory_manager" 
    SALESPERSON = "salesperson"
    VIEWER = "viewer"

class User(UserMixin, db.Model):
    """User model for authentication"""
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=True)
    role = db.Column(db.String(20), default=UserRole.VIEWER.value)
    # Removed Firebase UID - using PostgreSQL authentication only

    def set_password(self, password):
        """Set the user's password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the password matches the hash"""
        return check_password_hash(self.password_hash, password)

    # Email verification
    email_verified = db.Column(db.Boolean, default=False)  # Whether email is verified
    verification_token = db.Column(db.String(100), nullable=True)  # Token for email verification
    verification_token_expires = db.Column(db.DateTime, nullable=True)  # Expiration for verification token



    # User profile
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    shop_name = db.Column(db.String(128), nullable=True)
    product_categories = db.Column(db.String(512), nullable=True)  # Comma-separated list of product categories

    # Account status
    active = db.Column(db.Boolean, default=True)
    is_active = db.Column(db.Boolean, default=True)  # Alternative name for consistency
    is_admin = db.Column(db.Boolean, default=False)  # Admin flag for role-based access control

    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)  # Track last login time

    # Relationships
    subusers = db.relationship('Subuser', backref='parent_user', lazy=True, cascade='all, delete-orphan')
    items = db.relationship('Item', backref='owner', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<User {self.username}>'

    def to_dict(self):
        """Convert user to dictionary for API responses"""
        # Handle missing is_active column gracefully
        try:
            is_active_value = getattr(self, 'is_active', getattr(self, 'active', True))
        except (AttributeError, Exception):
            is_active_value = True

        try:
            return {
                'id': getattr(self, 'id', 0),
                'username': getattr(self, 'username', ''),
                'email': getattr(self, 'email', ''),
                'email_verified': getattr(self, 'email_verified', True),
                'first_name': getattr(self, 'first_name', ''),
                'last_name': getattr(self, 'last_name', ''),
                'phone': getattr(self, 'phone', ''),
                'shop_name': getattr(self, 'shop_name', ''),
                'product_categories': getattr(self, 'product_categories', ''),
                'active': getattr(self, 'active', True),
                'is_active': is_active_value,
                'is_admin': getattr(self, 'is_admin', False),
                'created_at': self.created_at.isoformat() if getattr(self, 'created_at', None) else None,
                'updated_at': self.updated_at.isoformat() if getattr(self, 'updated_at', None) else None,
                'last_login': self.last_login.isoformat() if getattr(self, 'last_login', None) else None
            }
        except Exception as e:
            # Fallback dictionary in case of any errors
            return {
                'id': 0,
                'username': '',
                'email': '',
                'email_verified': False,
                'first_name': '',
                'last_name': '',
                'phone': '',
                'shop_name': '',
                'product_categories': '',
                'active': True,
                'is_active': True,
                'is_admin': False,
                'created_at': None,
                'updated_at': None,
                'last_login': None
            }


class Subuser(db.Model):
    """Subuser model for managing team members"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    parent_user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    permissions = db.relationship('SubuserPermission', backref='subuser', lazy=True, cascade='all, delete-orphan')

    def set_password(self, password):
        """Set the subuser's password hash"""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        """Check if the password matches the hash"""
        return check_password_hash(self.password_hash, password)

    def to_dict(self):
        """Convert subuser to dictionary for API responses"""
        try:
            permissions_list = []
            for perm in self.permissions:
                if hasattr(perm, 'granted') and perm.granted:
                    permissions_list.append(perm.permission)
                elif hasattr(perm, 'permission'):
                    permissions_list.append(perm.permission)

            return {
                'id': self.id,
                'name': self.name or '',
                'email': self.email or '',
                'is_active': getattr(self, 'is_active', True),
                'created_at': self.created_at.isoformat() if self.created_at else None,
                'updated_at': self.updated_at.isoformat() if self.updated_at else None,
                'permissions': permissions_list
            }
        except Exception as e:
            # Fallback for any attribute errors
            return {
                'id': getattr(self, 'id', 0),
                'name': getattr(self, 'name', ''),
                'email': getattr(self, 'email', ''),
                'is_active': getattr(self, 'is_active', True),
                'created_at': None,
                'updated_at': None,
                'permissions': []
            }


class SubuserPermission(db.Model):
    """Model for managing subuser permissions"""
    id = db.Column(db.Integer, primary_key=True)
    subuser_id = db.Column(db.Integer, db.ForeignKey('subuser.id'), nullable=False)
    permission = db.Column(db.String(100), nullable=False)
    granted = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Ensure unique permission per subuser
    __table_args__ = (db.UniqueConstraint('subuser_id', 'permission', name='_subuser_permission_uc'),)

    def __repr__(self):
        return f'<SubuserPermission {self.permission}>'

    def to_dict(self):
        """Convert permission to dictionary for API responses"""
        return {
            'id': self.id,
            'subuser_id': self.subuser_id,
            'permission': self.permission,
            'granted': self.granted,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class OnDemandProduct(db.Model):
    """Model for on-demand products that can be created when needed"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    base_price = db.Column(db.Float, default=0.0)
    production_time = db.Column(db.Integer)  # In hours
    category = db.Column(db.String(50))
    materials = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    # User ownership
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<OnDemandProduct {self.name}>'

    def to_dict(self):
        """Convert on-demand product to dictionary for API responses"""
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


class Setting(db.Model):
    """Model for application settings"""
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(64), unique=True, nullable=False)
    value = db.Column(db.Text, nullable=True)
    description = db.Column(db.String(255), nullable=True)
    category = db.Column(db.String(64), default='general')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Setting {self.key}>'

    def to_dict(self):
        """Convert setting to dictionary for API responses"""
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'category': self.category,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Sale(db.Model):
    """Model for sales transactions"""
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True)
    customer_name = db.Column(db.String(100), nullable=False, default='Walk-in Customer')
    customer_phone = db.Column(db.String(20))
    sale_type = db.Column(db.String(20), default='retail')  # 'retail' or 'wholesale'
    subtotal = db.Column(db.Float, default=0.0)
    discount_type = db.Column(db.String(20), default='none')  # 'none', 'percentage', 'fixed'
    discount_value = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(20), default='cash')  # 'cash', 'mobile_money', 'card', 'bank_transfer'
    payment_details = db.Column(db.Text)  # JSON string with payment details
    payment_amount = db.Column(db.Float, default=0.0)
    change_amount = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    # User ownership
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Sale {self.invoice_number}>'

    def to_dict(self):
        """Convert sale to dictionary for API responses"""
        payment_details_dict = {}
        if self.payment_details:
            try:
                payment_details_dict = json.loads(self.payment_details)
            except json.JSONDecodeError:
                payment_details_dict = {}

        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'sale_type': self.sale_type,
            'subtotal': self.subtotal,
            'discount': {
                'type': self.discount_type,
                'value': self.discount_value,
                'amount': self.discount_amount
            },
            'total': self.total,
            'payment': {
                'method': self.payment_method,
                'details': payment_details_dict,
                'amount': self.payment_amount,
                'change': self.change_amount
            },
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class SaleItem(db.Model):
    """Model for items in a sale transaction"""
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id', ondelete='CASCADE'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    product_name = db.Column(db.String(100), nullable=False)
    product_sku = db.Column(db.String(50))
    price = db.Column(db.Float, default=0.0)
    quantity = db.Column(db.Integer, default=1)
    total = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Define relationships
    sale = db.relationship('Sale', backref=db.backref('items', lazy=True, cascade='all, delete-orphan'))
    item = db.relationship('Item', backref=db.backref('sale_items', lazy=True))

    def __repr__(self):
        return f'<SaleItem {self.product_name}>'

    def to_dict(self):
        """Convert sale item to dictionary for API responses"""
        return {
            'id': self.id,
            'sale_id': self.sale_id,
            'item_id': self.item_id,
            'product_name': self.product_name,
            'product_sku': self.product_sku,
            'price': self.price,
            'quantity': self.quantity,
            'total': self.total,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


# Financial Statement Models
class TransactionCategory(Enum):
    """Enum for transaction categories"""
    SALES = "Sales"
    PURCHASE = "Purchase"
    EXPENSE = "Expense"
    SALARY = "Salary"
    RENT = "Rent"
    UTILITIES = "Utilities"
    MAINTENANCE = "Maintenance"
    MARKETING = "Marketing"
    TAX = "Tax"
    INSURANCE = "Insurance"
    TRANSPORTATION = "Transportation"
    OFFICE_SUPPLIES = "Office Supplies"
    OTHER_INCOME = "Other Income"
    OTHER_EXPENSE = "Other Expense"


class TransactionType(Enum):
    """Enum for transaction types"""
    INCOME = "Income"
    EXPENSE = "Expense"


class FinancialTransaction(db.Model):
    """Model for financial transactions (income and expenses)"""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    description = db.Column(db.String(255), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)  # 'Income' or 'Expense'
    category = db.Column(db.String(50), nullable=False)
    reference_id = db.Column(db.String(100))  # To link to sales or other records
    payment_method = db.Column(db.String(50))  # Cash, bank transfer, mobile money, etc.
    
    # Tax and COGS tracking
    tax_rate = db.Column(db.Float, default=0.0)  # Tax rate percentage
    tax_amount = db.Column(db.Float, default=0.0)  # Calculated tax amount
    cost_of_goods_sold = db.Column(db.Float, default=0.0)  # COGS for sales transactions
    gross_amount = db.Column(db.Float, default=0.0)  # Amount before tax
    
    # User ownership
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<FinancialTransaction {self.description} {self.amount}>'

    def to_dict(self):
        """Convert financial transaction to dictionary for API responses"""
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'amount': self.amount,
            'transaction_type': self.transaction_type,
            'category': self.category,
            'reference_id': self.reference_id,
            'payment_method': self.payment_method,
            'tax_rate': self.tax_rate or 0,
            'tax_amount': self.tax_amount or 0,
            'cost_of_goods_sold': self.cost_of_goods_sold or 0,
            'gross_amount': self.gross_amount or 0,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class FinancialSummary(db.Model):
    """Model for storing financial summary data by period"""
    id = db.Column(db.Integer, primary_key=True)
    period_type = db.Column(db.String(20), nullable=False)  # 'daily', 'weekly', 'monthly', 'yearly'
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    total_income = db.Column(db.Float, default=0.0)
    total_expenses = db.Column(db.Float, default=0.0)
    net_profit = db.Column(db.Float, default=0.0)
    summary_data = db.Column(db.Text)  # JSON string with detailed breakdown
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<FinancialSummary {self.period_type} {self.period_start} to {self.period_end}>'

    def to_dict(self):
        """Convert financial summary to dictionary for API responses"""
        summary_data_dict = {}
        if self.summary_data:
            try:
                summary_data_dict = json.loads(self.summary_data)
            except json.JSONDecodeError:
                summary_data_dict = {}

        return {
            'id': self.id,
            'period_type': self.period_type,
            'period_start': self.period_start.isoformat() if self.period_start else None,
            'period_end': self.period_end.isoformat() if self.period_end else None,
            'total_income': self.total_income,
            'total_expenses': self.total_expenses,
            'net_profit': self.net_profit,
            'summary_data': summary_data_dict,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class ChartOfAccounts(db.Model):
    """Model for chart of accounts"""
    id = db.Column(db.Integer, primary_key=True)
    account_code = db.Column(db.String(20), unique=True, nullable=False)
    account_name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(20), nullable=False)  # Asset, Liability, Equity, Revenue, Expense
    parent_account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    parent_account = db.relationship('ChartOfAccounts', remote_side=[id], backref='sub_accounts')
    journal_entries = db.relationship('JournalEntry', backref='account', lazy=True)

    def __repr__(self):
        return f'<Account {self.account_code} - {self.account_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'account_code': self.account_code,
            'account_name': self.account_name,
            'account_type': self.account_type,
            'parent_account_id': self.parent_account_id,
            'parent_account_name': self.parent_account.account_name if self.parent_account else None,
            'description': self.description,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class GeneralLedger(db.Model):
    """Model for general ledger entries"""
    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'), nullable=False)
    debit_amount = db.Column(db.Float, default=0.0)
    credit_amount = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    journal = db.relationship('Journal', backref='ledger_entries')
    account = db.relationship('ChartOfAccounts', backref='ledger_entries')

    def __repr__(self):
        return f'<GeneralLedger Journal:{self.journal_id} Account:{self.account_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'journal_id': self.journal_id,
            'account_id': self.account_id,
            'account_code': self.account.account_code if self.account else '',
            'account_name': self.account.account_name if self.account else '',
            'debit_amount': self.debit_amount,
            'credit_amount': self.credit_amount,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class Journal(db.Model):
    """Model for journal entries"""
    id = db.Column(db.Integer, primary_key=True)
    journal_number = db.Column(db.String(50), unique=True, nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    description = db.Column(db.Text, nullable=False)
    reference_type = db.Column(db.String(50))  # 'sale', 'purchase', 'manual', 'adjustment'
    reference_id = db.Column(db.String(50))  # ID of related transaction
    total_debit = db.Column(db.Float, default=0.0)
    total_credit = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='posted')  # 'draft', 'posted', 'reversed'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    creator = db.relationship('User', foreign_keys=[created_by], backref='created_journals')

    @staticmethod
    def generate_journal_number():
        """Generate a unique journal number"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"JE-{timestamp}"

    def __repr__(self):
        return f'<Journal {self.journal_number}>'

    def to_dict(self):
        return {
            'id': self.id,
            'journal_number': self.journal_number,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'reference_type': self.reference_type,
            'reference_id': self.reference_id,
            'total_debit': self.total_debit,
            'total_credit': self.total_credit,
            'status': self.status,
            'created_by': self.created_by,
            'entries': [entry.to_dict() for entry in self.ledger_entries],
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class JournalEntry(db.Model):
    """Model for individual journal entry lines"""
    id = db.Column(db.Integer, primary_key=True)
    journal_id = db.Column(db.Integer, db.ForeignKey('journal.id', ondelete='CASCADE'), nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('chart_of_accounts.id'), nullable=False)
    debit_amount = db.Column(db.Float, default=0.0)
    credit_amount = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relationships
    journal = db.relationship('Journal', backref='entries')

    def __repr__(self):
        return f'<JournalEntry {self.id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'journal_id': self.journal_id,
            'account_id': self.account_id,
            'account_code': self.account.account_code if self.account else '',
            'account_name': self.account.account_name if self.account else '',
            'debit_amount': self.debit_amount,
            'credit_amount': self.credit_amount,
            'description': self.description,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class CashFlow(db.Model):
    """Model for cash flow tracking"""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    cash_in = db.Column(db.Float, default=0.0)
    cash_out = db.Column(db.Float, default=0.0)
    net_cash_flow = db.Column(db.Float, default=0.0)
    accumulated_cash = db.Column(db.Float, default=0.0)
    source = db.Column(db.String(100))  # Description of cash flow source
    category = db.Column(db.String(50))  # 'operations', 'investing', 'financing'
    reference_id = db.Column(db.String(50))
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<CashFlow {self.date} - Net: {self.net_cash_flow}>'

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'cash_in': self.cash_in,
            'cash_out': self.cash_out,
            'net_cash_flow': self.net_cash_flow,
            'accumulated_cash': self.accumulated_cash,
            'source': self.source,
            'category': self.category,
            'reference_id': self.reference_id,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BalanceSheet(db.Model):
    """Model for balance sheet data"""
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    total_assets = db.Column(db.Float, default=0.0)
    current_assets = db.Column(db.Float, default=0.0)
    inventory_value = db.Column(db.Float, default=0.0)
    cash_and_equivalents = db.Column(db.Float, default=0.0)
    accounts_receivable = db.Column(db.Float, default=0.0)
    total_liabilities = db.Column(db.Float, default=0.0)
    current_liabilities = db.Column(db.Float, default=0.0)
    accounts_payable = db.Column(db.Float, default=0.0)
    total_equity = db.Column(db.Float, default=0.0)
    retained_earnings = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<BalanceSheet {self.date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'total_assets': self.total_assets,
            'current_assets': self.current_assets,
            'inventory_value': self.inventory_value,
            'cash_and_equivalents': self.cash_and_equivalents,
            'accounts_receivable': self.accounts_receivable,
            'total_liabilities': self.total_liabilities,
            'current_liabilities': self.current_liabilities,
            'accounts_payable': self.accounts_payable,
            'total_equity': self.total_equity,
            'retained_earnings': self.retained_earnings,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BankAccount(db.Model):
    """Model for bank accounts"""
    id = db.Column(db.Integer, primary_key=True)
    account_name = db.Column(db.String(100), nullable=False)
    account_number = db.Column(db.String(50), nullable=False)
    bank_name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(20), default='checking')  # checking, savings, credit
    current_balance = db.Column(db.Float, default=0.0)
    currency = db.Column(db.String(3), default='TZS')
    is_active = db.Column(db.Boolean, default=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    transfers_from = db.relationship('BankTransfer', foreign_keys='BankTransfer.from_account_id', backref='from_account', lazy=True)
    transfers_to = db.relationship('BankTransfer', foreign_keys='BankTransfer.to_account_id', backref='to_account', lazy=True)

    def __repr__(self):
        return f'<BankAccount {self.account_name} - {self.bank_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'account_name': self.account_name,
            'account_number': self.account_number,
            'bank_name': self.bank_name,
            'account_type': self.account_type,
            'current_balance': self.current_balance,
            'currency': self.currency,
            'is_active': self.is_active,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class BankTransfer(db.Model):
    """Model for inter-bank transfers"""
    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(50), unique=True, nullable=False)
    from_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'), nullable=False)
    to_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transfer_date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    description = db.Column(db.Text)
    transfer_fee = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='completed')  # pending, completed, failed
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    @staticmethod
    def generate_transfer_number():
        """Generate a unique transfer number"""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"TRF-{timestamp}"

    def __repr__(self):
        return f'<BankTransfer {self.transfer_number} - {self.amount}>'

    def to_dict(self):
        return {
            'id': self.id,
            'transfer_number': self.transfer_number,
            'from_account_id': self.from_account_id,
            'from_account_name': self.from_account.account_name if self.from_account else '',
            'to_account_id': self.to_account_id,
            'to_account_name': self.to_account.account_name if self.to_account else '',
            'amount': self.amount,
            'transfer_date': self.transfer_date.isoformat() if self.transfer_date else None,
            'description': self.description,
            'transfer_fee': self.transfer_fee,
            'status': self.status,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class BankReconciliation(db.Model):
    """Model for bank reconciliation"""
    id = db.Column(db.Integer, primary_key=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_account.id'), nullable=False)
    reconciliation_date = db.Column(db.Date, nullable=False)
    bank_statement_balance = db.Column(db.Float, nullable=False)
    book_balance = db.Column(db.Float, nullable=False)
    adjusted_balance = db.Column(db.Float, nullable=False)
    total_deposits_in_transit = db.Column(db.Float, default=0.0)
    total_outstanding_checks = db.Column(db.Float, default=0.0)
    other_adjustments = db.Column(db.Float, default=0.0)
    status = db.Column(db.String(20), default='pending')  # pending, reconciled, discrepancy
    notes = db.Column(db.Text)
    reconciled_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bank_account = db.relationship('BankAccount', backref='reconciliations')
    reconciler = db.relationship('User', foreign_keys=[reconciled_by], backref='reconciliations_performed')

    def __repr__(self):
        return f'<BankReconciliation {self.reconciliation_date} - {self.bank_account.account_name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'bank_account_id': self.bank_account_id,
            'bank_account_name': self.bank_account.account_name if self.bank_account else '',
            'reconciliation_date': self.reconciliation_date.isoformat() if self.reconciliation_date else None,
            'bank_statement_balance': self.bank_statement_balance,
            'book_balance': self.book_balance,
            'adjusted_balance': self.adjusted_balance,
            'total_deposits_in_transit': self.total_deposits_in_transit,
            'total_outstanding_checks': self.total_outstanding_checks,
            'other_adjustments': self.other_adjustments,
            'status': self.status,
            'notes': self.notes,
            'reconciled_by': self.reconciled_by,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class BranchEquity(db.Model):
    """Model for tracking branch/location-specific equity"""
    id = db.Column(db.Integer, primary_key=True)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    opening_equity = db.Column(db.Float, default=0.0)
    net_income = db.Column(db.Float, default=0.0)
    owner_drawings = db.Column(db.Float, default=0.0)
    additional_investments = db.Column(db.Float, default=0.0)
    closing_equity = db.Column(db.Float, default=0.0)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    location = db.relationship('Location', backref='equity_records')

    def __repr__(self):
        return f'<BranchEquity {self.location.name if self.location else "Unknown"} - {self.date}>'

    def to_dict(self):
        return {
            'id': self.id,
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else '',
            'date': self.date.isoformat() if self.date else None,
            'opening_equity': self.opening_equity,
            'net_income': self.net_income,
            'owner_drawings': self.owner_drawings,
            'additional_investments': self.additional_investments,
            'closing_equity': self.closing_equity,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Category(db.Model):
    """Model for product categories"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50))  # Font Awesome icon class
    color = db.Column(db.String(7), default='#007bff')  # Hex color code
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    subcategories = db.relationship('Subcategory', backref='category', lazy=True, cascade='all, delete-orphan')
    items = db.relationship('Item', backref='category_obj', lazy=True, foreign_keys='Item.category_id')

    def __repr__(self):
        return f'<Category {self.name}>'

    def to_dict(self):
        """Convert category to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'is_active': self.is_active,
            'subcategories': [sub.to_dict() for sub in self.subcategories if sub.is_active],
            'item_count': len([item for item in self.items if item.category == self.name]),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Subcategory(db.Model):
    """Model for product subcategories"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Ensure unique subcategory names within each category
    __table_args__ = (db.UniqueConstraint('name', 'category_id', name='_category_subcategory_uc'),)

    def __repr__(self):
        return f'<Subcategory {self.name}>'

    def to_dict(self):
        """Convert subcategory to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category_id': self.category_id,
            'category_name': self.category.name if self.category else None,
            'is_active': self.is_active,
            'item_count': Item.query.filter_by(subcategory=self.name).count(),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LayawayPlan(db.Model):
    """Model for layaway/installment plans"""
    id = db.Column(db.Integer, primary_key=True)
    customer_name = db.Column(db.String(100), nullable=False)
    customer_phone = db.Column(db.String(20))
    customer_email = db.Column(db.String(120))
    total_amount = db.Column(db.Float, nullable=False)
    down_payment = db.Column(db.Float, default=0.0)
    remaining_balance = db.Column(db.Float, nullable=False)
    installment_amount = db.Column(db.Float, nullable=False)
    payment_frequency = db.Column(db.String(20), default='monthly')  # weekly, bi-weekly, monthly
    next_payment_date = db.Column(db.Date)
    completion_date = db.Column(db.Date)
    status = db.Column(db.String(20), default='active')  # active, completed, cancelled, defaulted
    items_data = db.Column(db.Text)  # JSON string with item details
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    payments = db.relationship('LayawayPayment', backref='layaway_plan', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<LayawayPlan {self.customer_name} - {self.total_amount}>'

    def to_dict(self):
        """Convert layaway plan to dictionary for API responses"""
        items_data_dict = {}
        if self.items_data:
            try:
                items_data_dict = json.loads(self.items_data)
            except json.JSONDecodeError:
                items_data_dict = {}

        return {
            'id': self.id,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'customer_email': self.customer_email,
            'total_amount': self.total_amount,
            'down_payment': self.down_payment,
            'remaining_balance': self.remaining_balance,
            'installment_amount': self.installment_amount,
            'payment_frequency': self.payment_frequency,
            'next_payment_date': self.next_payment_date.isoformat() if self.next_payment_date else None,
            'completion_date': self.completion_date.isoformat() if self.completion_date else None,
            'status': self.status,
            'items': items_data_dict,
            'notes': self.notes,
            'total_paid': sum(payment.amount for payment in self.payments),
            'payments_count': len(self.payments),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LayawayPayment(db.Model):
    """Model for layaway payments"""
    id = db.Column(db.Integer, primary_key=True)
    layaway_plan_id = db.Column(db.Integer, db.ForeignKey('layaway_plan.id', ondelete='CASCADE'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), default='cash')
    payment_date = db.Column(db.Date, default=datetime.utcnow().date)
    reference_number = db.Column(db.String(100))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<LayawayPayment {self.amount} for Plan {self.layaway_plan_id}>'

    def to_dict(self):
        """Convert layaway payment to dictionary for API responses"""
        return {
            'id': self.id,
            'layaway_plan_id': self.layaway_plan_id,
            'amount': self.amount,
            'payment_method': self.payment_method,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'reference_number': self.reference_number,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }


class PricingRule(db.Model):
    """Model for dynamic pricing rules"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    rule_type = db.Column(db.String(20), nullable=False)  # bulk, promotional, time_based, competitor
    conditions = db.Column(db.Text)  # JSON string with conditions
    discount_type = db.Column(db.String(20), default='percentage')  # percentage, fixed_amount
    discount_value = db.Column(db.Float, default=0.0)
    min_quantity = db.Column(db.Integer, default=1)
    max_quantity = db.Column(db.Integer)
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    applicable_items = db.Column(db.Text)  # JSON string with item IDs or categories
    is_active = db.Column(db.Boolean, default=True)
    priority = db.Column(db.Integer, default=1)  # Higher number = higher priority
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<PricingRule {self.name}>'

    def to_dict(self):
        """Convert pricing rule to dictionary for API responses"""
        conditions_dict = {}
        applicable_items_list = []
        
        if self.conditions:
            try:
                conditions_dict = json.loads(self.conditions)
            except json.JSONDecodeError:
                conditions_dict = {}
        
        if self.applicable_items:
            try:
                applicable_items_list = json.loads(self.applicable_items)
            except json.JSONDecodeError:
                applicable_items_list = []

        return {
            'id': self.id,
            'name': self.name,
            'rule_type': self.rule_type,
            'conditions': conditions_dict,
            'discount_type': self.discount_type,
            'discount_value': self.discount_value,
            'min_quantity': self.min_quantity,
            'max_quantity': self.max_quantity,
            'start_date': self.start_date.isoformat() if self.start_date else None,
            'end_date': self.end_date.isoformat() if self.end_date else None,
            'applicable_items': applicable_items_list,
            'is_active': self.is_active,
            'priority': self.priority,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class Location(db.Model):
    """Model for warehouse/store locations"""
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    code = db.Column(db.String(20), unique=True, nullable=False)  # Short code like 'WH01', 'ST01'
    type = db.Column(db.String(20), default='warehouse')  # 'warehouse', 'store', 'office'
    address = db.Column(db.Text)
    city = db.Column(db.String(50))
    state = db.Column(db.String(50))
    postal_code = db.Column(db.String(20))
    country = db.Column(db.String(50))
    phone = db.Column(db.String(20))
    email = db.Column(db.String(120))
    manager_name = db.Column(db.String(100))
    is_active = db.Column(db.Boolean, default=True)
    is_default = db.Column(db.Boolean, default=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    stock_levels = db.relationship('LocationStock', backref='location', lazy=True, cascade='all, delete-orphan')
    transfers_from = db.relationship('StockTransfer', foreign_keys='StockTransfer.from_location_id', backref='from_location', lazy=True)
    transfers_to = db.relationship('StockTransfer', foreign_keys='StockTransfer.to_location_id', backref='to_location', lazy=True)

    def __repr__(self):
        return f'<Location {self.name} ({self.code})>'

    def to_dict(self):
        """Convert location to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'code': self.code,
            'type': self.type,
            'address': self.address,
            'city': self.city,
            'state': self.state,
            'postal_code': self.postal_code,
            'country': self.country,
            'phone': self.phone,
            'email': self.email,
            'manager_name': self.manager_name,
            'is_active': self.is_active,
            'is_default': self.is_default,
            'total_items': len(self.stock_levels),
            'total_stock': sum(stock.quantity for stock in self.stock_levels),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class LocationStock(db.Model):
    """Model for item stock levels at specific locations"""
    id = db.Column(db.Integer, primary_key=True)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id', ondelete='CASCADE'), nullable=False)
    location_id = db.Column(db.Integer, db.ForeignKey('location.id', ondelete='CASCADE'), nullable=False)
    quantity = db.Column(db.Integer, default=0)
    reserved_quantity = db.Column(db.Integer, default=0)  # For pending orders/transfers
    min_stock_level = db.Column(db.Integer, default=0)  # Location-specific minimum stock
    max_stock_level = db.Column(db.Integer, default=0)  # Location-specific maximum stock
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    item = db.relationship('Item', backref=db.backref('location_stocks', lazy=True))

    # Ensure unique combination of item and location
    __table_args__ = (db.UniqueConstraint('item_id', 'location_id', name='_item_location_stock_uc'),)

    def __repr__(self):
        return f'<LocationStock {self.item.name} at {self.location.name}: {self.quantity}>'

    @property
    def available_quantity(self):
        """Calculate available quantity (total - reserved)"""
        return max(0, self.quantity - self.reserved_quantity)

    def to_dict(self):
        """Convert location stock to dictionary for API responses"""
        return {
            'id': self.id,
            'item_id': self.item_id,
            'item_name': self.item.name if self.item else '',
            'item_sku': self.item.sku if self.item else '',
            'location_id': self.location_id,
            'location_name': self.location.name if self.location else '',
            'location_code': self.location.code if self.location else '',
            'quantity': self.quantity,
            'reserved_quantity': self.reserved_quantity,
            'available_quantity': self.available_quantity,
            'min_stock_level': self.min_stock_level,
            'max_stock_level': self.max_stock_level,
            'last_updated': self.last_updated.isoformat() if self.last_updated else None
        }


class StockTransfer(db.Model):
    """Model for stock transfers between locations"""
    id = db.Column(db.Integer, primary_key=True)
    transfer_number = db.Column(db.String(50), unique=True, nullable=False)
    from_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    to_location_id = db.Column(db.Integer, db.ForeignKey('location.id'), nullable=False)
    status = db.Column(db.String(20), default='pending')  # pending, in_transit, completed, cancelled
    transfer_date = db.Column(db.Date, default=datetime.utcnow().date)
    expected_arrival = db.Column(db.Date)
    actual_arrival = db.Column(db.Date)
    notes = db.Column(db.Text)
    requested_by = db.Column(db.String(100))
    approved_by = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    items = db.relationship('StockTransferItem', backref='transfer', lazy=True, cascade='all, delete-orphan')
    creator = db.relationship('User', backref=db.backref('stock_transfers', lazy=True))

    def __repr__(self):
        return f'<StockTransfer {self.transfer_number}>'

    @staticmethod
    def generate_transfer_number():
        """Generate a unique transfer number"""
        import time
        timestamp = str(int(time.time()))[-6:]  # Last 6 digits of timestamp
        random_suffix = ''.join(random.choices(string.digits, k=3))
        return f"TRF-{timestamp}-{random_suffix}"

    def to_dict(self):
        """Convert stock transfer to dictionary for API responses"""
        return {
            'id': self.id,
            'transfer_number': self.transfer_number,
            'from_location_id': self.from_location_id,
            'from_location_name': self.from_location.name if self.from_location else '',
            'from_location_code': self.from_location.code if self.from_location else '',
            'to_location_id': self.to_location_id,
            'to_location_name': self.to_location.name if self.to_location else '',
            'to_location_code': self.to_location.code if self.to_location else '',
            'status': self.status,
            'transfer_date': self.transfer_date.isoformat() if self.transfer_date else None,
            'expected_arrival': self.expected_arrival.isoformat() if self.expected_arrival else None,
            'actual_arrival': self.actual_arrival.isoformat() if self.actual_arrival else None,
            'notes': self.notes,
            'requested_by': self.requested_by,
            'approved_by': self.approved_by,
            'created_by': self.created_by,
            'items_count': len(self.items),
            'total_quantity': sum(item.quantity for item in self.items),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


class StockTransferItem(db.Model):
    """Model for items in a stock transfer"""
    id = db.Column(db.Integer, primary_key=True)
    transfer_id = db.Column(db.Integer, db.ForeignKey('stock_transfer.id', ondelete='CASCADE'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'), nullable=False)
    quantity_requested = db.Column(db.Integer, nullable=False)
    quantity_shipped = db.Column(db.Integer, default=0)
    quantity_received = db.Column(db.Integer, default=0)
    notes = db.Column(db.Text)

    # Relationships
    item = db.relationship('Item', backref=db.backref('transfer_items', lazy=True))

    def __repr__(self):
        return f'<StockTransferItem {self.item.name if self.item else "Unknown"}: {self.quantity_requested}>'

    def to_dict(self):
        """Convert stock transfer item to dictionary for API responses"""
        return {
            'id': self.id,
            'transfer_id': self.transfer_id,
            'item_id': self.item_id,
            'item_name': self.item.name if self.item else '',
            'item_sku': self.item.sku if self.item else '',
            'quantity_requested': self.quantity_requested,
            'quantity_shipped': self.quantity_shipped,
            'quantity_received': self.quantity_received,
            'notes': self.notes
        }