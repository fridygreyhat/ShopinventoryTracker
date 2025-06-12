
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from sqlalchemy import func, and_, or_
from app import db
from models import (
    Item, Sale, SaleItem, FinancialTransaction, ChartOfAccounts, 
    GeneralLedger, Journal, JournalEntry, CashFlow, BalanceSheet, 
    BankAccount, BankTransfer, BankReconciliation, BranchEquity, User
)

class FinancialService:
    """Comprehensive financial and accounting service"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
    
    def initialize_chart_of_accounts(self) -> bool:
        """Initialize default chart of accounts for a new user"""
        try:
            default_accounts = [
                # Assets
                ('1000', 'Cash and Cash Equivalents', 'Asset', None),
                ('1100', 'Accounts Receivable', 'Asset', None),
                ('1200', 'Inventory', 'Asset', None),
                ('1300', 'Prepaid Expenses', 'Asset', None),
                ('1400', 'Equipment', 'Asset', None),
                ('1500', 'Accumulated Depreciation', 'Asset', None),
                
                # Liabilities
                ('2000', 'Accounts Payable', 'Liability', None),
                ('2100', 'Accrued Expenses', 'Liability', None),
                ('2200', 'Short-term Loans', 'Liability', None),
                ('2300', 'Long-term Debt', 'Liability', None),
                
                # Equity
                ('3000', 'Owner\'s Equity', 'Equity', None),
                ('3100', 'Retained Earnings', 'Equity', None),
                ('3200', 'Additional Paid-in Capital', 'Equity', None),
                
                # Revenue
                ('4000', 'Sales Revenue', 'Revenue', None),
                ('4100', 'Service Revenue', 'Revenue', None),
                ('4200', 'Other Income', 'Revenue', None),
                
                # Expenses
                ('5000', 'Cost of Goods Sold', 'Expense', None),
                ('5100', 'Salaries and Wages', 'Expense', None),
                ('5200', 'Rent Expense', 'Expense', None),
                ('5300', 'Utilities Expense', 'Expense', None),
                ('5400', 'Marketing Expense', 'Expense', None),
                ('5500', 'Office Supplies', 'Expense', None),
                ('5600', 'Depreciation Expense', 'Expense', None),
                ('5700', 'Interest Expense', 'Expense', None),
                ('5800', 'Insurance Expense', 'Expense', None),
                ('5900', 'Other Expenses', 'Expense', None),
            ]
            
            for code, name, acc_type, parent_id in default_accounts:
                # Check if account already exists
                existing = ChartOfAccounts.query.filter_by(
                    account_code=code, user_id=self.user_id
                ).first()
                
                if not existing:
                    account = ChartOfAccounts(
                        account_code=code,
                        account_name=name,
                        account_type=acc_type,
                        parent_account_id=parent_id,
                        user_id=self.user_id
                    )
                    db.session.add(account)
            
            db.session.commit()
            return True
            
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing chart of accounts: {e}")
            return False
    
    def create_journal_entry(self, description: str, entries: List[Dict], 
                           reference_type: str = 'manual', reference_id: str = None) -> Optional[Journal]:
        """Create a journal entry with multiple debit/credit entries"""
        try:
            # Validate that debits equal credits
            total_debits = sum(entry.get('debit', 0) for entry in entries)
            total_credits = sum(entry.get('credit', 0) for entry in entries)
            
            if abs(total_debits - total_credits) > 0.01:  # Allow for small rounding differences
                raise ValueError("Debits must equal credits")
            
            # Create journal entry
            journal = Journal(
                journal_number=Journal.generate_journal_number(),
                description=description,
                reference_type=reference_type,
                reference_id=reference_id,
                total_debit=total_debits,
                total_credit=total_credits,
                user_id=self.user_id,
                created_by=self.user_id
            )
            db.session.add(journal)
            db.session.flush()  # Get the journal ID
            
            # Create individual journal entry lines
            for entry in entries:
                journal_entry = JournalEntry(
                    journal_id=journal.id,
                    account_id=entry['account_id'],
                    debit_amount=entry.get('debit', 0),
                    credit_amount=entry.get('credit', 0),
                    description=entry.get('description', description)
                )
                db.session.add(journal_entry)
                
                # Create general ledger entry
                ledger_entry = GeneralLedger(
                    journal_id=journal.id,
                    account_id=entry['account_id'],
                    debit_amount=entry.get('debit', 0),
                    credit_amount=entry.get('credit', 0),
                    description=entry.get('description', description)
                )
                db.session.add(ledger_entry)
            
            db.session.commit()
            return journal
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating journal entry: {e}")
            return None
    
    def record_sale_journal_entry(self, sale: Sale) -> Optional[Journal]:
        """Record journal entries for a sale transaction"""
        try:
            # Get accounts
            cash_account = self._get_account_by_code('1000')  # Cash
            sales_account = self._get_account_by_code('4000')  # Sales Revenue
            cogs_account = self._get_account_by_code('5000')   # Cost of Goods Sold
            inventory_account = self._get_account_by_code('1200')  # Inventory
            
            if not all([cash_account, sales_account, cogs_account, inventory_account]):
                raise ValueError("Required accounts not found")
            
            # Calculate COGS
            total_cogs = 0
            for item in sale.items:
                if item.item_id:
                    inventory_item = Item.query.get(item.item_id)
                    if inventory_item:
                        total_cogs += (inventory_item.buying_price or 0) * item.quantity
            
            entries = [
                {
                    'account_id': cash_account.id,
                    'debit': sale.total,
                    'credit': 0,
                    'description': f'Cash received from sale {sale.invoice_number}'
                },
                {
                    'account_id': sales_account.id,
                    'debit': 0,
                    'credit': sale.total,
                    'description': f'Revenue from sale {sale.invoice_number}'
                }
            ]
            
            # Add COGS entries if there's cost
            if total_cogs > 0:
                entries.extend([
                    {
                        'account_id': cogs_account.id,
                        'debit': total_cogs,
                        'credit': 0,
                        'description': f'Cost of goods sold for {sale.invoice_number}'
                    },
                    {
                        'account_id': inventory_account.id,
                        'debit': 0,
                        'credit': total_cogs,
                        'description': f'Inventory reduction for {sale.invoice_number}'
                    }
                ])
            
            return self.create_journal_entry(
                description=f'Sale transaction - {sale.invoice_number}',
                entries=entries,
                reference_type='sale',
                reference_id=sale.invoice_number
            )
            
        except Exception as e:
            print(f"Error recording sale journal entry: {e}")
            return None
    
    def record_purchase_journal_entry(self, purchase_data: Dict) -> Optional[Journal]:
        """Record journal entries for inventory purchase"""
        try:
            inventory_account = self._get_account_by_code('1200')  # Inventory
            cash_account = self._get_account_by_code('1000')      # Cash
            payable_account = self._get_account_by_code('2000')   # Accounts Payable
            
            if not all([inventory_account, cash_account, payable_account]):
                raise ValueError("Required accounts not found")
            
            total_cost = purchase_data['total_cost']
            payment_method = purchase_data.get('payment_method', 'cash')
            
            entries = [
                {
                    'account_id': inventory_account.id,
                    'debit': total_cost,
                    'credit': 0,
                    'description': f'Inventory purchase - {purchase_data["description"]}'
                }
            ]
            
            if payment_method == 'cash':
                entries.append({
                    'account_id': cash_account.id,
                    'debit': 0,
                    'credit': total_cost,
                    'description': f'Cash payment for inventory purchase'
                })
            else:
                entries.append({
                    'account_id': payable_account.id,
                    'debit': 0,
                    'credit': total_cost,
                    'description': f'Accounts payable for inventory purchase'
                })
            
            return self.create_journal_entry(
                description=f'Inventory purchase - {purchase_data["description"]}',
                entries=entries,
                reference_type='purchase',
                reference_id=purchase_data.get('reference_id')
            )
            
        except Exception as e:
            print(f"Error recording purchase journal entry: {e}")
            return None
    
    def calculate_profit_loss(self, start_date: datetime, end_date: datetime) -> Dict:
        """Calculate profit and loss statement"""
        try:
            # Get revenue accounts (4000 series)
            revenue_accounts = ChartOfAccounts.query.filter(
                ChartOfAccounts.user_id == self.user_id,
                ChartOfAccounts.account_type == 'Revenue',
                ChartOfAccounts.is_active == True
            ).all()
            
            # Get expense accounts (5000 series)
            expense_accounts = ChartOfAccounts.query.filter(
                ChartOfAccounts.user_id == self.user_id,
                ChartOfAccounts.account_type == 'Expense',
                ChartOfAccounts.is_active == True
            ).all()
            
            total_revenue = 0
            total_expenses = 0
            revenue_breakdown = {}
            expense_breakdown = {}
            
            # Calculate revenue
            for account in revenue_accounts:
                balance = self._get_account_balance(account.id, start_date, end_date)
                total_revenue += balance
                revenue_breakdown[account.account_name] = balance
            
            # Calculate expenses
            for account in expense_accounts:
                balance = self._get_account_balance(account.id, start_date, end_date)
                total_expenses += balance
                expense_breakdown[account.account_name] = balance
            
            gross_profit = total_revenue
            cogs = expense_breakdown.get('Cost of Goods Sold', 0)
            if cogs > 0:
                gross_profit = total_revenue - cogs
            
            net_profit = total_revenue - total_expenses
            
            return {
                'period_start': start_date.isoformat(),
                'period_end': end_date.isoformat(),
                'total_revenue': total_revenue,
                'total_expenses': total_expenses,
                'gross_profit': gross_profit,
                'net_profit': net_profit,
                'revenue_breakdown': revenue_breakdown,
                'expense_breakdown': expense_breakdown
            }
            
        except Exception as e:
            print(f"Error calculating profit and loss: {e}")
            return {}
    
    def generate_balance_sheet(self, as_of_date: datetime = None) -> Dict:
        """Generate balance sheet as of a specific date"""
        try:
            if as_of_date is None:
                as_of_date = datetime.now()
            
            # Get all account types
            asset_accounts = ChartOfAccounts.query.filter(
                ChartOfAccounts.user_id == self.user_id,
                ChartOfAccounts.account_type == 'Asset',
                ChartOfAccounts.is_active == True
            ).all()
            
            liability_accounts = ChartOfAccounts.query.filter(
                ChartOfAccounts.user_id == self.user_id,
                ChartOfAccounts.account_type == 'Liability',
                ChartOfAccounts.is_active == True
            ).all()
            
            equity_accounts = ChartOfAccounts.query.filter(
                ChartOfAccounts.user_id == self.user_id,
                ChartOfAccounts.account_type == 'Equity',
                ChartOfAccounts.is_active == True
            ).all()
            
            # Calculate balances
            total_assets = 0
            total_liabilities = 0
            total_equity = 0
            
            asset_breakdown = {}
            liability_breakdown = {}
            equity_breakdown = {}
            
            # Assets
            for account in asset_accounts:
                balance = self._get_account_balance(account.id, None, as_of_date)
                total_assets += balance
                asset_breakdown[account.account_name] = balance
            
            # Liabilities
            for account in liability_accounts:
                balance = self._get_account_balance(account.id, None, as_of_date)
                total_liabilities += balance
                liability_breakdown[account.account_name] = balance
            
            # Equity
            for account in equity_accounts:
                balance = self._get_account_balance(account.id, None, as_of_date)
                total_equity += balance
                equity_breakdown[account.account_name] = balance
            
            # Calculate current inventory value
            inventory_value = self._calculate_inventory_value()
            
            return {
                'as_of_date': as_of_date.isoformat(),
                'total_assets': total_assets,
                'total_liabilities': total_liabilities,
                'total_equity': total_equity,
                'inventory_value': inventory_value,
                'asset_breakdown': asset_breakdown,
                'liability_breakdown': liability_breakdown,
                'equity_breakdown': equity_breakdown,
                'balance_check': abs(total_assets - (total_liabilities + total_equity)) < 0.01
            }
            
        except Exception as e:
            print(f"Error generating balance sheet: {e}")
            return {}
    
    def generate_trial_balance(self, as_of_date: datetime = None) -> Dict:
        """Generate trial balance"""
        try:
            if as_of_date is None:
                as_of_date = datetime.now()
            
            accounts = ChartOfAccounts.query.filter(
                ChartOfAccounts.user_id == self.user_id,
                ChartOfAccounts.is_active == True
            ).all()
            
            trial_balance = []
            total_debits = 0
            total_credits = 0
            
            for account in accounts:
                debit_balance, credit_balance = self._get_account_trial_balance(account.id, as_of_date)
                
                if debit_balance != 0 or credit_balance != 0:
                    trial_balance.append({
                        'account_code': account.account_code,
                        'account_name': account.account_name,
                        'account_type': account.account_type,
                        'debit_balance': debit_balance,
                        'credit_balance': credit_balance
                    })
                    
                    total_debits += debit_balance
                    total_credits += credit_balance
            
            return {
                'as_of_date': as_of_date.isoformat(),
                'accounts': trial_balance,
                'total_debits': total_debits,
                'total_credits': total_credits,
                'is_balanced': abs(total_debits - total_credits) < 0.01
            }
            
        except Exception as e:
            print(f"Error generating trial balance: {e}")
            return {}
    
    def update_cash_flow(self, date: datetime, cash_in: float = 0, cash_out: float = 0, 
                        source: str = '', category: str = 'operations', reference_id: str = None):
        """Update cash flow records"""
        try:
            # Get or create cash flow record for the date
            cash_flow = CashFlow.query.filter(
                CashFlow.user_id == self.user_id,
                CashFlow.date == date.date()
            ).first()
            
            if not cash_flow:
                cash_flow = CashFlow(
                    date=date.date(),
                    user_id=self.user_id,
                    cash_in=0,
                    cash_out=0,
                    net_cash_flow=0,
                    accumulated_cash=0
                )
                db.session.add(cash_flow)
            
            # Update amounts
            cash_flow.cash_in += cash_in
            cash_flow.cash_out += cash_out
            cash_flow.net_cash_flow = cash_flow.cash_in - cash_flow.cash_out
            cash_flow.source = source
            cash_flow.category = category
            cash_flow.reference_id = reference_id
            
            # Calculate accumulated cash flow
            previous_accumulated = db.session.query(func.sum(CashFlow.net_cash_flow)).filter(
                CashFlow.user_id == self.user_id,
                CashFlow.date < date.date()
            ).scalar() or 0
            
            cash_flow.accumulated_cash = previous_accumulated + cash_flow.net_cash_flow
            
            db.session.commit()
            return cash_flow
            
        except Exception as e:
            db.session.rollback()
            print(f"Error updating cash flow: {e}")
            return None
    
    def create_bank_transfer(self, from_account_id: int, to_account_id: int, 
                           amount: float, description: str = '', transfer_fee: float = 0) -> Optional[BankTransfer]:
        """Create inter-bank transfer"""
        try:
            # Validate accounts
            from_account = BankAccount.query.filter(
                BankAccount.id == from_account_id,
                BankAccount.user_id == self.user_id,
                BankAccount.is_active == True
            ).first()
            
            to_account = BankAccount.query.filter(
                BankAccount.id == to_account_id,
                BankAccount.user_id == self.user_id,
                BankAccount.is_active == True
            ).first()
            
            if not from_account or not to_account:
                raise ValueError("Invalid bank accounts")
            
            if from_account.current_balance < (amount + transfer_fee):
                raise ValueError("Insufficient funds")
            
            # Create transfer record
            transfer = BankTransfer(
                transfer_number=BankTransfer.generate_transfer_number(),
                from_account_id=from_account_id,
                to_account_id=to_account_id,
                amount=amount,
                description=description,
                transfer_fee=transfer_fee,
                user_id=self.user_id
            )
            db.session.add(transfer)
            
            # Update account balances
            from_account.current_balance -= (amount + transfer_fee)
            to_account.current_balance += amount
            
            # Create journal entries for the transfer
            cash_account = self._get_account_by_code('1000')
            if cash_account:
                entries = [
                    {
                        'account_id': cash_account.id,
                        'debit': amount,
                        'credit': 0,
                        'description': f'Transfer to {to_account.account_name}'
                    },
                    {
                        'account_id': cash_account.id,
                        'debit': 0,
                        'credit': amount,
                        'description': f'Transfer from {from_account.account_name}'
                    }
                ]
                
                if transfer_fee > 0:
                    fee_account = self._get_account_by_code('5900')  # Other Expenses
                    if fee_account:
                        entries.extend([
                            {
                                'account_id': fee_account.id,
                                'debit': transfer_fee,
                                'credit': 0,
                                'description': 'Bank transfer fee'
                            },
                            {
                                'account_id': cash_account.id,
                                'debit': 0,
                                'credit': transfer_fee,
                                'description': 'Bank transfer fee payment'
                            }
                        ])
                
                self.create_journal_entry(
                    description=f'Bank transfer - {transfer.transfer_number}',
                    entries=entries,
                    reference_type='transfer',
                    reference_id=transfer.transfer_number
                )
            
            db.session.commit()
            return transfer
            
        except Exception as e:
            db.session.rollback()
            print(f"Error creating bank transfer: {e}")
            return None
    
    def _get_account_by_code(self, code: str) -> Optional[ChartOfAccounts]:
        """Get account by code"""
        return ChartOfAccounts.query.filter(
            ChartOfAccounts.account_code == code,
            ChartOfAccounts.user_id == self.user_id,
            ChartOfAccounts.is_active == True
        ).first()
    
    def _get_account_balance(self, account_id: int, start_date: datetime = None, 
                           end_date: datetime = None) -> float:
        """Calculate account balance for a period"""
        query = GeneralLedger.query.filter(GeneralLedger.account_id == account_id)
        
        if start_date or end_date:
            query = query.join(Journal)
            if start_date:
                query = query.filter(Journal.date >= start_date.date())
            if end_date:
                query = query.filter(Journal.date <= end_date.date())
        
        entries = query.all()
        
        total_debits = sum(entry.debit_amount for entry in entries)
        total_credits = sum(entry.credit_amount for entry in entries)
        
        # Account type determines normal balance
        account = ChartOfAccounts.query.get(account_id)
        if account and account.account_type in ['Asset', 'Expense']:
            return total_debits - total_credits
        else:
            return total_credits - total_debits
    
    def _get_account_trial_balance(self, account_id: int, as_of_date: datetime) -> Tuple[float, float]:
        """Get account trial balance (separate debit and credit totals)"""
        entries = GeneralLedger.query.join(Journal).filter(
            GeneralLedger.account_id == account_id,
            Journal.date <= as_of_date.date()
        ).all()
        
        total_debits = sum(entry.debit_amount for entry in entries)
        total_credits = sum(entry.credit_amount for entry in entries)
        
        # Return net balance in appropriate column based on account type
        account = ChartOfAccounts.query.get(account_id)
        net_balance = total_debits - total_credits
        
        if account and account.account_type in ['Asset', 'Expense']:
            return (net_balance if net_balance > 0 else 0, abs(net_balance) if net_balance < 0 else 0)
        else:
            return (abs(net_balance) if net_balance < 0 else 0, net_balance if net_balance > 0 else 0)
    
    def _calculate_inventory_value(self) -> float:
        """Calculate current inventory value"""
        items = Item.query.filter(Item.user_id == self.user_id).all()
        total_value = 0
        
        for item in items:
            item_value = (item.quantity or 0) * (item.buying_price or 0)
            total_value += item_value
        
        return total_value
