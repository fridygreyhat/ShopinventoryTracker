"""
Financial management models
"""
from datetime import datetime
from decimal import Decimal
from app import db


class FinancialTransaction(db.Model):
    """Financial transaction model"""
    __tablename__ = 'financial_transactions'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Transaction details
    transaction_type = db.Column(db.String(50), nullable=False)  # income, expense, transfer
    category = db.Column(db.String(100), nullable=False)
    amount = db.Column(db.Numeric(10, 2), nullable=False)
    description = db.Column(db.Text, nullable=True)
    
    # References
    reference_type = db.Column(db.String(50), nullable=True)  # sale, purchase, expense
    reference_id = db.Column(db.Integer, nullable=True)
    
    # Banking
    bank_account_id = db.Column(db.Integer, db.ForeignKey('bank_accounts.id'), nullable=True)
    
    # Timestamps
    transaction_date = db.Column(db.Date, default=datetime.utcnow().date, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<FinancialTransaction {self.transaction_type}: {self.amount}>'


class BankAccount(db.Model):
    """Bank account model"""
    __tablename__ = 'bank_accounts'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    
    # Account details
    account_name = db.Column(db.String(200), nullable=False)
    account_number = db.Column(db.String(50), nullable=True)
    bank_name = db.Column(db.String(200), nullable=False)
    account_type = db.Column(db.String(50), default='checking', nullable=False)
    
    # Balance
    current_balance = db.Column(db.Numeric(10, 2), default=0, nullable=False)
    
    # Status
    active = db.Column(db.Boolean, default=True, nullable=False)
    is_default = db.Column(db.Boolean, default=False, nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    transactions = db.relationship('FinancialTransaction', backref='bank_account', lazy=True)
    
    def update_balance(self, amount, transaction_type):
        """Update account balance based on transaction"""
        if transaction_type == 'income':
            self.current_balance += amount
        elif transaction_type == 'expense':
            self.current_balance -= amount
        self.updated_at = datetime.utcnow()
    
    def __repr__(self):
        return f'<BankAccount {self.account_name}>'