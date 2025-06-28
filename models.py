from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase
import enum

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    first_name = db.Column(db.String(64))
    last_name = db.Column(db.String(64))
    phone = db.Column(db.String(20))
    shop_name = db.Column(db.String(128))
    product_categories = db.Column(db.String(512))
    is_active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    email_verified = db.Column(db.Boolean, default=False)
    firebase_uid = db.Column(db.String(128))
    verification_token = db.Column(db.String(64))
    verification_token_expires = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)

    def set_password(self, password):
        """Set password hash"""
        import hashlib
        self.password_hash = hashlib.sha256(password.encode()).hexdigest()

    def check_password(self, password):
        """Check if provided password matches hash"""
        import hashlib
        return self.password_hash == hashlib.sha256(password.encode()).hexdigest()

    def to_dict(self):
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'shop_name': self.shop_name,
            'is_active': self.is_active,
            'is_admin': self.is_admin,
            'email_verified': self.email_verified,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'last_login': self.last_login.isoformat() if self.last_login else None
        }

class Item(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    sku = db.Column(db.String(50), unique=True)
    quantity = db.Column(db.Integer, default=0)
    price = db.Column(db.Float, default=0.0)
    buying_price = db.Column(db.Float, default=0.0)
    selling_price_retail = db.Column(db.Float, default=0.0)
    selling_price_wholesale = db.Column(db.Float, default=0.0)
    sales_type = db.Column(db.String(20), default='both')
    category = db.Column(db.String(100), default='Uncategorized')
    subcategory = db.Column(db.String(100))
    unit_type = db.Column(db.String(20), default='quantity')
    sell_by = db.Column(db.String(20), default='quantity')
    category_id = db.Column(db.Integer)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    is_active = db.Column(db.Boolean, default=True)
    stock_quantity = db.Column(db.Integer, default=0)
    minimum_stock = db.Column(db.Integer, default=0)
    retail_price = db.Column(db.Float, default=0.0)
    wholesale_price = db.Column(db.Float, default=0.0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

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
            'quantity': self.quantity,
            'price': self.price,
            'buying_price': self.buying_price,
            'selling_price_retail': self.selling_price_retail,
            'selling_price_wholesale': self.selling_price_wholesale,
            'sales_type': self.sales_type,
            'category': self.category,
            'subcategory': self.subcategory,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Setting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), unique=True, nullable=False)
    value = db.Column(db.Text)
    description = db.Column(db.Text)
    category = db.Column(db.String(50), default='general')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'key': self.key,
            'value': self.value,
            'description': self.description,
            'category': self.category,
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
    id = db.Column(db.Integer, primary_key=True)
    invoice_number = db.Column(db.String(50), unique=True, nullable=False)
    customer_name = db.Column(db.String(100))
    customer_phone = db.Column(db.String(20))
    sale_type = db.Column(db.String(20), default='retail')
    subtotal = db.Column(db.Float, default=0.0)
    discount_type = db.Column(db.String(20), default='none')
    discount_value = db.Column(db.Float, default=0.0)
    discount_amount = db.Column(db.Float, default=0.0)
    total = db.Column(db.Float, default=0.0)
    total_amount = db.Column(db.Float, default=0.0)
    payment_method = db.Column(db.String(20), default='cash')
    payment_details = db.Column(db.Text)
    payment_amount = db.Column(db.Float, default=0.0)
    change_amount = db.Column(db.Float, default=0.0)
    notes = db.Column(db.Text)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'invoice_number': self.invoice_number,
            'customer_name': self.customer_name,
            'total': self.total,
            'payment_method': self.payment_method,
            'created_at': self.created_at.isoformat() if self.created_at else None
        }

class SaleItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    product_name = db.Column(db.String(100), nullable=False)
    product_sku = db.Column(db.String(50))
    price = db.Column(db.Float, default=0.0)
    quantity = db.Column(db.Integer, default=1)
    total = db.Column(db.Float, default=0.0)

    def to_dict(self):
        return {
            'id': self.id,
            'product_name': self.product_name,
            'quantity': self.quantity,
            'price': self.price,
            'total': self.total
        }

class FinancialTransaction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False)
    description = db.Column(db.String(200), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    transaction_type = db.Column(db.String(20), nullable=False)
    category = db.Column(db.String(100))
    reference_id = db.Column(db.String(100))
    payment_method = db.Column(db.String(50))
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'description': self.description,
            'amount': self.amount,
            'transaction_type': self.transaction_type,
            'category': self.category
        }

# Placeholder classes for other models
class Category(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text)
    icon = db.Column(db.String(50), default='fas fa-box')
    color = db.Column(db.String(20), default='#007bff')
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'icon': self.icon,
            'color': self.color,
            'is_active': self.is_active
        }

class Subcategory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    category_id = db.Column(db.Integer, db.ForeignKey('category.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'category_id': self.category_id,
            'is_active': self.is_active
        }

class Customer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(20))
    national_id = db.Column(db.String(50))
    email = db.Column(db.String(120))
    address = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'phone': self.phone,
            'national_id': self.national_id,
            'email': self.email,
            'address': self.address
        }

class InstallmentSale(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    item_id = db.Column(db.Integer, db.ForeignKey('item.id'))
    quantity = db.Column(db.Integer, default=1)
    total_amount = db.Column(db.Float, nullable=False)
    down_payment = db.Column(db.Float, default=0.0)
    number_of_installments = db.Column(db.Integer, nullable=False)
    installment_amount = db.Column(db.Float, nullable=False)
    start_date = db.Column(db.Date, nullable=False)
    status = db.Column(db.String(20), default='Active')
    agreement_signed = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'customer_id': self.customer_id,
            'total_amount': self.total_amount,
            'down_payment': self.down_payment,
            'number_of_installments': self.number_of_installments,
            'installment_amount': self.installment_amount,
            'status': self.status
        }

class InstallmentPayment(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    installment_sale_id = db.Column(db.Integer, db.ForeignKey('installment_sale.id'), nullable=False)
    payment_date = db.Column(db.Date, nullable=False)
    amount_paid = db.Column(db.Float, nullable=False)
    payment_method = db.Column(db.String(20), default='cash')
    remarks = db.Column(db.Text)
    created_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'payment_date': self.payment_date.isoformat() if self.payment_date else None,
            'amount_paid': self.amount_paid,
            'payment_method': self.payment_method
        }

# Additional models referenced in app.py but not essential for basic functionality
class OnDemandProduct(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text)
    base_price = db.Column(db.Float, default=0.0)
    production_time = db.Column(db.Integer, default=0)
    category = db.Column(db.String(100))
    materials = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'description': self.description,
            'base_price': self.base_price,
            'is_active': self.is_active
        }

class TransactionCategory(enum.Enum):
    SALES = "Sales"
    PURCHASES = "Purchases"
    MARKETING = "Marketing"
    UTILITIES = "Utilities"
    RENT = "Rent"
    SUPPLIES = "Supplies"
    OTHER_INCOME = "Other Income"
    OTHER_EXPENSE = "Other Expense"

# Accounting models
class Account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(20), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    account_type = db.Column(db.String(50), nullable=False)
    normal_balance = db.Column(db.String(10), nullable=False)
    parent_id = db.Column(db.Integer, db.ForeignKey('account.id'))
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime)
    updated_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'code': self.code,
            'name': self.name,
            'account_type': self.account_type,
            'normal_balance': self.normal_balance,
            'is_active': self.is_active
        }

class JournalEntry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    entry_number = db.Column(db.String(50))
    date = db.Column(db.Date, nullable=False)
    account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    debit_amount = db.Column(db.Float, default=0.0)
    credit_amount = db.Column(db.Float, default=0.0)
    description = db.Column(db.Text)
    reference_type = db.Column(db.String(50))
    reference_id = db.Column(db.String(100))
    transaction_group = db.Column(db.String(100))
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'date': self.date.isoformat() if self.date else None,
            'debit_amount': self.debit_amount,
            'credit_amount': self.credit_amount,
            'description': self.description
        }

class BankReconciliation(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    bank_account_id = db.Column(db.Integer, db.ForeignKey('account.id'), nullable=False)
    reconciliation_date = db.Column(db.Date, nullable=False)
    bank_statement_balance = db.Column(db.Float, nullable=False)
    book_balance = db.Column(db.Float, nullable=False)
    outstanding_deposits = db.Column(db.Float, default=0.0)
    outstanding_checks = db.Column(db.Float, default=0.0)
    bank_fees = db.Column(db.Float, default=0.0)
    reconciled_balance = db.Column(db.Float, nullable=False)
    is_reconciled = db.Column(db.Boolean, default=False)
    notes = db.Column(db.Text)
    created_by = db.Column(db.Integer, db.ForeignKey('user.id'))
    created_at = db.Column(db.DateTime)

    def to_dict(self):
        return {
            'id': self.id,
            'reconciliation_date': self.reconciliation_date.isoformat() if self.reconciliation_date else None,
            'bank_statement_balance': self.bank_statement_balance,
            'book_balance': self.book_balance,
            'is_reconciled': self.is_reconciled
        }