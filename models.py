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
    quantity = db.Column(db.Integer, default=0)
    buying_price = db.Column(db.Float, default=0.0)
    selling_price_retail = db.Column(db.Float, default=0.0)
    selling_price_wholesale = db.Column(db.Float, default=0.0)
    price = db.Column(db.Float, default=0.0)  # For backward compatibility
    sales_type = db.Column(db.String(20), default='both')  # 'retail', 'wholesale', or 'both'
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

    def to_dict(self):
        """Convert item to dictionary for API responses"""
        return {
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
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }


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
    # Firebase UID for authentication
    firebase_uid = db.Column(db.String(128), unique=True, nullable=True)

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
            is_active_value = getattr(self, 'is_active', self.active)
        except (AttributeError, Exception):
            is_active_value = getattr(self, 'active', True)

        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'email_verified': self.email_verified,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'phone': self.phone,
            'shop_name': self.shop_name,
            'product_categories': self.product_categories,
            'active': getattr(self, 'active', True),
            'is_active': is_active_value,
            'is_admin': self.is_admin,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
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
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f'<Sale {self.invoice_number}>'

    def to_dict(self):
        """Convert sale to dictionary for API responses"""
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'customer_name': self.customer_name,
            'customer_phone': self.customer_phone,
            'sale_type': self.sale_type,
            'subtotal': self.subtotal,
            'discount_type': self.discount_type,
            'discount_value': self.discount_value,
            'discount_amount': self.discount_amount,
            'total': self.total,
            'payment_method': self.payment_method,
            'payment_details': self.payment_details,
            'payment_amount': self.payment_amount,
            'change_amount': self.change_amount,
            'notes': self.notes,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

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