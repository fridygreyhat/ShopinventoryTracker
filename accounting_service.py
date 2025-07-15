from datetime import datetime
from models import db, ChartOfAccounts, Journal, FinancialTransaction
import logging

logger = logging.getLogger(__name__)

class AccountingService:
    @staticmethod
    def initialize_chart_of_accounts(user_id):
        """Initialize chart of accounts for a user"""
        try:
            # Check if already initialized
            existing = ChartOfAccounts.query.filter_by(user_id=user_id).first()
            if existing:
                return True

            # Default chart of accounts
            accounts = [
                # Assets
                {'code': '1000', 'name': 'Cash', 'type': 'Asset'},
                {'code': '1100', 'name': 'Accounts Receivable', 'type': 'Asset'},
                {'code': '1200', 'name': 'Inventory', 'type': 'Asset'},
                {'code': '1500', 'name': 'Equipment', 'type': 'Asset'},

                # Liabilities
                {'code': '2000', 'name': 'Accounts Payable', 'type': 'Liability'},
                {'code': '2100', 'name': 'Short-term Debt', 'type': 'Liability'},

                # Equity
                {'code': '3000', 'name': 'Owner Equity', 'type': 'Equity'},
                {'code': '3100', 'name': 'Retained Earnings', 'type': 'Equity'},

                # Revenue
                {'code': '4000', 'name': 'Sales Revenue', 'type': 'Revenue'},
                {'code': '4100', 'name': 'Service Revenue', 'type': 'Revenue'},

                # Expenses
                {'code': '5000', 'name': 'Cost of Goods Sold', 'type': 'Expense'},
                {'code': '5100', 'name': 'Operating Expenses', 'type': 'Expense'},
                {'code': '5200', 'name': 'Rent Expense', 'type': 'Expense'},
            ]

            for account_data in accounts:
                account = ChartOfAccounts(
                    account_code=account_data['code'],
                    account_name=account_data['name'],
                    account_type=account_data['type'],
                    user_id=user_id,
                    balance=0.0,
                    is_active=True
                )
                db.session.add(account)

            db.session.commit()
            logger.info(f"Chart of accounts initialized for user {user_id}")
            return True

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error initializing chart of accounts: {str(e)}")
            return False

    @staticmethod
    def create_journal_entry(user_id, description, entries):
        """Create a journal entry with multiple line items"""
        try:
            # Generate journal number
            journal_number = f"JE-{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

            # Calculate totals
            total_debit = sum(entry.get('debit', 0) for entry in entries)
            total_credit = sum(entry.get('credit', 0) for entry in entries)

            # Validate balanced entry
            if abs(total_debit - total_credit) > 0.01:
                return {'success': False, 'error': 'Journal entry must be balanced'}

            # Create journal header
            journal = Journal(
                journal_number=journal_number,
                description=description,
                entry_date=datetime.utcnow().date(),
                total_debit=total_debit,
                total_credit=total_credit,
                user_id=user_id
            )

            db.session.add(journal)
            db.session.commit()

            return {
                'success': True,
                'journal_id': journal.id,
                'journal_number': journal_number
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating journal entry: {str(e)}")
            return {'success': False, 'error': str(e)}

    @staticmethod
    def record_sale_transaction(sale):
        """Record a sale transaction in the accounting system"""
        try:
            # Placeholder for accounting entries
            logger.info(f"Recording sale transaction for sale {sale.id}")
            return True
        except Exception as e:
            logger.error(f"Error recording sale transaction: {str(e)}")
            return False

    @staticmethod
    def get_trial_balance(as_of_date=None):
        """Get trial balance"""
        return {
            'accounts': [],
            'total_debits': 0,
            'total_credits': 0,
            'as_of_date': (as_of_date or date.today()).isoformat()
        }

    @staticmethod
    def get_income_statement(start_date, end_date):
        """Get income statement"""
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat()
            },
            'revenues': [],
            'expenses': [],
            'net_income': 0
        }

    @staticmethod
    def get_balance_sheet(as_of_date=None):
        """Get balance sheet"""
        return {
            'as_of_date': (as_of_date or date.today()).isoformat(),
            'assets': [],
            'liabilities': [],
            'equity': [],
            'total_assets': 0,
            'total_liabilities': 0,
            'total_equity': 0
        }