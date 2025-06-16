
from datetime import datetime, date
from models import db, Account, JournalEntry, AccountType, Sale, Item
import uuid


class AccountingService:
    """Service class for accounting operations"""
    
    @staticmethod
    def initialize_chart_of_accounts():
        """Initialize standard chart of accounts"""
        standard_accounts = [
            # Assets (1000-1999)
            {'code': '1000', 'name': 'Cash', 'account_type': AccountType.ASSET.value, 'normal_balance': 'Debit'},
            {'code': '1010', 'name': 'Bank - Checking', 'account_type': AccountType.ASSET.value, 'normal_balance': 'Debit'},
            {'code': '1020', 'name': 'Bank - Savings', 'account_type': AccountType.ASSET.value, 'normal_balance': 'Debit'},
            {'code': '1100', 'name': 'Accounts Receivable', 'account_type': AccountType.ASSET.value, 'normal_balance': 'Debit'},
            {'code': '1200', 'name': 'Inventory', 'account_type': AccountType.ASSET.value, 'normal_balance': 'Debit'},
            {'code': '1300', 'name': 'Prepaid Expenses', 'account_type': AccountType.ASSET.value, 'normal_balance': 'Debit'},
            {'code': '1500', 'name': 'Equipment', 'account_type': AccountType.ASSET.value, 'normal_balance': 'Debit'},
            {'code': '1510', 'name': 'Accumulated Depreciation - Equipment', 'account_type': AccountType.ASSET.value, 'normal_balance': 'Credit'},
            
            # Liabilities (2000-2999)
            {'code': '2000', 'name': 'Accounts Payable', 'account_type': AccountType.LIABILITY.value, 'normal_balance': 'Credit'},
            {'code': '2100', 'name': 'Accrued Expenses', 'account_type': AccountType.LIABILITY.value, 'normal_balance': 'Credit'},
            {'code': '2200', 'name': 'Short-term Loans', 'account_type': AccountType.LIABILITY.value, 'normal_balance': 'Credit'},
            {'code': '2500', 'name': 'Long-term Loans', 'account_type': AccountType.LIABILITY.value, 'normal_balance': 'Credit'},
            
            # Equity (3000-3999)
            {'code': '3000', 'name': "Owner's Equity", 'account_type': AccountType.EQUITY.value, 'normal_balance': 'Credit'},
            {'code': '3100', 'name': 'Retained Earnings', 'account_type': AccountType.EQUITY.value, 'normal_balance': 'Credit'},
            {'code': '3200', 'name': 'Owner Withdrawals', 'account_type': AccountType.EQUITY.value, 'normal_balance': 'Debit'},
            
            # Income/Revenue (4000-4999)
            {'code': '4000', 'name': 'Sales Revenue', 'account_type': AccountType.INCOME.value, 'normal_balance': 'Credit'},
            {'code': '4010', 'name': 'Sales Revenue - Retail', 'account_type': AccountType.INCOME.value, 'normal_balance': 'Credit'},
            {'code': '4020', 'name': 'Sales Revenue - Wholesale', 'account_type': AccountType.INCOME.value, 'normal_balance': 'Credit'},
            {'code': '4100', 'name': 'Other Income', 'account_type': AccountType.INCOME.value, 'normal_balance': 'Credit'},
            {'code': '4200', 'name': 'Interest Income', 'account_type': AccountType.INCOME.value, 'normal_balance': 'Credit'},
            
            # Expenses (5000-5999)
            {'code': '5000', 'name': 'Cost of Goods Sold', 'account_type': AccountType.EXPENSE.value, 'normal_balance': 'Debit'},
            {'code': '5100', 'name': 'Rent Expense', 'account_type': AccountType.EXPENSE.value, 'normal_balance': 'Debit'},
            {'code': '5200', 'name': 'Utilities Expense', 'account_type': AccountType.EXPENSE.value, 'normal_balance': 'Debit'},
            {'code': '5300', 'name': 'Salaries Expense', 'account_type': AccountType.EXPENSE.value, 'normal_balance': 'Debit'},
            {'code': '5400', 'name': 'Marketing Expense', 'account_type': AccountType.EXPENSE.value, 'normal_balance': 'Debit'},
            {'code': '5500', 'name': 'Office Supplies Expense', 'account_type': AccountType.EXPENSE.value, 'normal_balance': 'Debit'},
            {'code': '5600', 'name': 'Insurance Expense', 'account_type': AccountType.EXPENSE.value, 'normal_balance': 'Debit'},
            {'code': '5700', 'name': 'Transportation Expense', 'account_type': AccountType.EXPENSE.value, 'normal_balance': 'Debit'},
            {'code': '5800', 'name': 'Maintenance Expense', 'account_type': AccountType.EXPENSE.value, 'normal_balance': 'Debit'},
            {'code': '5900', 'name': 'Other Expenses', 'account_type': AccountType.EXPENSE.value, 'normal_balance': 'Debit'},
        ]
        
        for account_data in standard_accounts:
            existing = Account.query.filter_by(code=account_data['code']).first()
            if not existing:
                account = Account(**account_data)
                db.session.add(account)
        
        db.session.commit()
    
    @staticmethod
    def generate_entry_number():
        """Generate unique journal entry number"""
        today = datetime.now()
        prefix = f"JE-{today.year}-"
        
        # Find the last entry number for this year
        last_entry = JournalEntry.query.filter(
            JournalEntry.entry_number.like(f"{prefix}%")
        ).order_by(JournalEntry.entry_number.desc()).first()
        
        if last_entry:
            # Extract number and increment
            last_number = int(last_entry.entry_number.split('-')[-1])
            new_number = last_number + 1
        else:
            new_number = 1
        
        return f"{prefix}{new_number:04d}"
    
    @staticmethod
    def create_journal_entry(account_id, debit_amount=0, credit_amount=0, description="", 
                           reference_type=None, reference_id=None, transaction_group=None, 
                           entry_date=None, created_by=None):
        """Create a single journal entry"""
        if not entry_date:
            entry_date = datetime.now().date()
        
        if not transaction_group:
            transaction_group = str(uuid.uuid4())[:8]
        
        entry = JournalEntry(
            entry_number=AccountingService.generate_entry_number(),
            date=entry_date,
            account_id=account_id,
            debit_amount=debit_amount,
            credit_amount=credit_amount,
            description=description,
            reference_type=reference_type,
            reference_id=reference_id,
            transaction_group=transaction_group,
            created_by=created_by
        )
        
        db.session.add(entry)
        return entry
    
    @staticmethod
    def record_sale_transaction(sale):
        """Record journal entries for a sale"""
        transaction_group = f"SALE-{sale.id}"
        
        # Get accounts
        cash_account = Account.query.filter_by(code='1000').first()
        bank_account = Account.query.filter_by(code='1010').first()
        sales_revenue_account = Account.query.filter_by(code='4000').first()
        inventory_account = Account.query.filter_by(code='1200').first()
        cogs_account = Account.query.filter_by(code='5000').first()
        
        # Determine which cash account to use based on payment method
        if sale.payment_method == 'cash':
            cash_debit_account = cash_account
        else:
            cash_debit_account = bank_account
        
        # 1. Record revenue
        # Debit: Cash/Bank
        AccountingService.create_journal_entry(
            account_id=cash_debit_account.id,
            debit_amount=sale.total,
            description=f"Sale #{sale.invoice_number} - {sale.customer_name}",
            reference_type='sale',
            reference_id=str(sale.id),
            transaction_group=transaction_group,
            entry_date=sale.created_at.date() if sale.created_at else None
        )
        
        # Credit: Sales Revenue
        AccountingService.create_journal_entry(
            account_id=sales_revenue_account.id,
            credit_amount=sale.total,
            description=f"Sale #{sale.invoice_number} - {sale.customer_name}",
            reference_type='sale',
            reference_id=str(sale.id),
            transaction_group=transaction_group,
            entry_date=sale.created_at.date() if sale.created_at else None
        )
        
        # 2. Record cost of goods sold
        from models import SaleItem
        sale_items = SaleItem.query.filter_by(sale_id=sale.id).all()
        total_cogs = 0
        
        for sale_item in sale_items:
            if sale_item.item:
                item_cogs = sale_item.item.buying_price * sale_item.quantity
                total_cogs += item_cogs
        
        if total_cogs > 0:
            # Debit: Cost of Goods Sold
            AccountingService.create_journal_entry(
                account_id=cogs_account.id,
                debit_amount=total_cogs,
                description=f"COGS for Sale #{sale.invoice_number}",
                reference_type='sale_cogs',
                reference_id=str(sale.id),
                transaction_group=transaction_group,
                entry_date=sale.created_at.date() if sale.created_at else None
            )
            
            # Credit: Inventory
            AccountingService.create_journal_entry(
                account_id=inventory_account.id,
                credit_amount=total_cogs,
                description=f"Inventory reduction for Sale #{sale.invoice_number}",
                reference_type='sale_cogs',
                reference_id=str(sale.id),
                transaction_group=transaction_group,
                entry_date=sale.created_at.date() if sale.created_at else None
            )
        
        db.session.commit()
    
    @staticmethod
    def record_purchase_transaction(item, quantity, total_cost, payment_method='cash'):
        """Record journal entries for inventory purchase"""
        transaction_group = f"PURCHASE-{item.id}-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Get accounts
        cash_account = Account.query.filter_by(code='1000').first()
        bank_account = Account.query.filter_by(code='1010').first()
        inventory_account = Account.query.filter_by(code='1200').first()
        
        # Determine which cash account to use
        if payment_method == 'cash':
            cash_credit_account = cash_account
        else:
            cash_credit_account = bank_account
        
        # Debit: Inventory
        AccountingService.create_journal_entry(
            account_id=inventory_account.id,
            debit_amount=total_cost,
            description=f"Purchase of {quantity} units of {item.name}",
            reference_type='purchase',
            reference_id=str(item.id),
            transaction_group=transaction_group
        )
        
        # Credit: Cash/Bank
        AccountingService.create_journal_entry(
            account_id=cash_credit_account.id,
            credit_amount=total_cost,
            description=f"Payment for purchase of {item.name}",
            reference_type='purchase',
            reference_id=str(item.id),
            transaction_group=transaction_group
        )
        
        db.session.commit()
    
    @staticmethod
    def record_expense_transaction(amount, expense_type, description, payment_method='cash', reference_id=None):
        """Record journal entries for expenses"""
        transaction_group = f"EXPENSE-{datetime.now().strftime('%Y%m%d%H%M%S')}"
        
        # Get accounts
        cash_account = Account.query.filter_by(code='1000').first()
        bank_account = Account.query.filter_by(code='1010').first()
        
        # Map expense types to accounts
        expense_account_mapping = {
            'Rent': '5100',
            'Utilities': '5200',
            'Salary': '5300',
            'Marketing': '5400',
            'Office Supplies': '5500',
            'Insurance': '5600',
            'Transportation': '5700',
            'Maintenance': '5800',
            'Other Expense': '5900'
        }
        
        expense_account_code = expense_account_mapping.get(expense_type, '5900')
        expense_account = Account.query.filter_by(code=expense_account_code).first()
        
        # Determine which cash account to use
        if payment_method == 'cash':
            cash_credit_account = cash_account
        else:
            cash_credit_account = bank_account
        
        # Debit: Expense Account
        AccountingService.create_journal_entry(
            account_id=expense_account.id,
            debit_amount=amount,
            description=description,
            reference_type='expense',
            reference_id=reference_id,
            transaction_group=transaction_group
        )
        
        # Credit: Cash/Bank
        AccountingService.create_journal_entry(
            account_id=cash_credit_account.id,
            credit_amount=amount,
            description=f"Payment for {description}",
            reference_type='expense',
            reference_id=reference_id,
            transaction_group=transaction_group
        )
        
        db.session.commit()
    
    @staticmethod
    def get_trial_balance(as_of_date=None):
        """Generate trial balance"""
        if not as_of_date:
            as_of_date = datetime.now().date()
        
        accounts = Account.query.filter_by(is_active=True).all()
        trial_balance = []
        total_debits = 0
        total_credits = 0
        
        for account in accounts:
            balance = account.get_balance(as_of_date)
            
            if balance != 0:
                if account.normal_balance == 'Debit':
                    debit_balance = balance if balance > 0 else 0
                    credit_balance = abs(balance) if balance < 0 else 0
                else:
                    credit_balance = balance if balance > 0 else 0
                    debit_balance = abs(balance) if balance < 0 else 0
                
                trial_balance.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'debit_balance': debit_balance,
                    'credit_balance': credit_balance
                })
                
                total_debits += debit_balance
                total_credits += credit_balance
        
        return {
            'trial_balance': trial_balance,
            'total_debits': total_debits,
            'total_credits': total_credits,
            'is_balanced': abs(total_debits - total_credits) < 0.01,
            'as_of_date': as_of_date.isoformat()
        }
    
    @staticmethod
    def get_income_statement(start_date, end_date):
        """Generate Profit & Loss statement"""
        income_accounts = Account.query.filter_by(account_type=AccountType.INCOME.value, is_active=True).all()
        expense_accounts = Account.query.filter_by(account_type=AccountType.EXPENSE.value, is_active=True).all()
        
        # Calculate revenue
        revenue_items = []
        total_revenue = 0
        
        for account in income_accounts:
            entries = JournalEntry.query.filter(
                JournalEntry.account_id == account.id,
                JournalEntry.date >= start_date,
                JournalEntry.date <= end_date
            ).all()
            
            account_total = sum(entry.credit_amount - entry.debit_amount for entry in entries)
            
            if account_total != 0:
                revenue_items.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'amount': account_total
                })
                total_revenue += account_total
        
        # Calculate expenses
        expense_items = []
        total_expenses = 0
        
        for account in expense_accounts:
            entries = JournalEntry.query.filter(
                JournalEntry.account_id == account.id,
                JournalEntry.date >= start_date,
                JournalEntry.date <= end_date
            ).all()
            
            account_total = sum(entry.debit_amount - entry.credit_amount for entry in entries)
            
            if account_total != 0:
                expense_items.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'amount': account_total
                })
                total_expenses += account_total
        
        net_income = total_revenue - total_expenses
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'revenue': {
                'items': revenue_items,
                'total': total_revenue
            },
            'expenses': {
                'items': expense_items,
                'total': total_expenses
            },
            'net_income': net_income
        }
    
    @staticmethod
    def get_balance_sheet(as_of_date=None):
        """Generate Balance Sheet"""
        if not as_of_date:
            as_of_date = datetime.now().date()
        
        # Get accounts by type
        asset_accounts = Account.query.filter_by(account_type=AccountType.ASSET.value, is_active=True).all()
        liability_accounts = Account.query.filter_by(account_type=AccountType.LIABILITY.value, is_active=True).all()
        equity_accounts = Account.query.filter_by(account_type=AccountType.EQUITY.value, is_active=True).all()
        
        # Calculate assets
        assets = []
        total_assets = 0
        
        for account in asset_accounts:
            balance = account.get_balance(as_of_date)
            if balance != 0:
                assets.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'amount': balance
                })
                total_assets += balance
        
        # Calculate liabilities
        liabilities = []
        total_liabilities = 0
        
        for account in liability_accounts:
            balance = account.get_balance(as_of_date)
            if balance != 0:
                liabilities.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'amount': balance
                })
                total_liabilities += balance
        
        # Calculate equity
        equity = []
        total_equity = 0
        
        for account in equity_accounts:
            balance = account.get_balance(as_of_date)
            if balance != 0:
                equity.append({
                    'account_code': account.code,
                    'account_name': account.name,
                    'amount': balance
                })
                total_equity += balance
        
        return {
            'as_of_date': as_of_date.isoformat(),
            'assets': {
                'items': assets,
                'total': total_assets
            },
            'liabilities': {
                'items': liabilities,
                'total': total_liabilities
            },
            'equity': {
                'items': equity,
                'total': total_equity
            },
            'total_liabilities_and_equity': total_liabilities + total_equity
        }
