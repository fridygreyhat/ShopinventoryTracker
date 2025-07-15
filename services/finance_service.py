
from models import db, Sale, Item, FinancialTransaction, ChartOfAccounts
from datetime import datetime, timedelta
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

class FinanceService:
    def __init__(self, user_id):
        self.user_id = user_id

    def record_transaction(self, transaction_data):
        """Record a financial transaction"""
        try:
            transaction = FinancialTransaction(
                transaction_type=transaction_data['type'],
                amount=transaction_data['amount'],
                description=transaction_data['description'],
                category=transaction_data.get('category', 'General'),
                reference_id=transaction_data.get('reference_id'),
                user_id=self.user_id,
                created_at=datetime.utcnow()
            )

            db.session.add(transaction)
            db.session.commit()

            return {
                'success': True,
                'transaction_id': transaction.id,
                'message': 'Transaction recorded successfully'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error recording transaction: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_profit_loss_statement(self, start_date, end_date):
        """Generate profit and loss statement"""
        try:
            # Revenue (from sales)
            revenue = db.session.query(func.sum(Sale.total_amount)).filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= start_date,
                Sale.created_at <= end_date
            ).scalar() or 0

            # Cost of goods sold
            cogs = self._calculate_cogs(start_date, end_date)

            # Gross profit
            gross_profit = revenue - cogs

            # Operating expenses
            expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == self.user_id,
                FinancialTransaction.transaction_type == 'expense',
                FinancialTransaction.created_at >= start_date,
                FinancialTransaction.created_at <= end_date
            ).scalar() or 0

            # Net profit
            net_profit = gross_profit - expenses

            return {
                'success': True,
                'statement': {
                    'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    'revenue': float(revenue),
                    'cost_of_goods_sold': float(cogs),
                    'gross_profit': float(gross_profit),
                    'operating_expenses': float(expenses),
                    'net_profit': float(net_profit),
                    'gross_profit_margin': (gross_profit / revenue * 100) if revenue > 0 else 0,
                    'net_profit_margin': (net_profit / revenue * 100) if revenue > 0 else 0
                }
            }

        except Exception as e:
            logger.error(f"Error generating P&L statement: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _calculate_cogs(self, start_date, end_date):
        """Calculate cost of goods sold for the period"""
        try:
            # Get all sales in the period
            sales = Sale.query.filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= start_date,
                Sale.created_at <= end_date
            ).all()

            total_cogs = 0
            for sale in sales:
                for sale_item in sale.sale_items:
                    item_cost = sale_item.item.cost or 0
                    total_cogs += item_cost * sale_item.quantity

            return total_cogs

        except Exception as e:
            logger.error(f"Error calculating COGS: {str(e)}")
            return 0

    def get_cash_flow_statement(self, start_date, end_date):
        """Generate cash flow statement"""
        try:
            # Cash inflows (sales)
            cash_in = db.session.query(func.sum(Sale.total_amount)).filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= start_date,
                Sale.created_at <= end_date,
                Sale.payment_method.in_(['cash', 'mpesa', 'card'])
            ).scalar() or 0

            # Cash outflows (expenses)
            cash_out = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == self.user_id,
                FinancialTransaction.transaction_type == 'expense',
                FinancialTransaction.created_at >= start_date,
                FinancialTransaction.created_at <= end_date
            ).scalar() or 0

            # Net cash flow
            net_cash_flow = cash_in - cash_out

            return {
                'success': True,
                'cash_flow': {
                    'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    'cash_inflows': float(cash_in),
                    'cash_outflows': float(cash_out),
                    'net_cash_flow': float(net_cash_flow)
                }
            }

        except Exception as e:
            logger.error(f"Error generating cash flow statement: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_expense_breakdown(self, start_date, end_date):
        """Get expense breakdown by category"""
        try:
            expenses = db.session.query(
                FinancialTransaction.category,
                func.sum(FinancialTransaction.amount).label('total')
            ).filter(
                FinancialTransaction.user_id == self.user_id,
                FinancialTransaction.transaction_type == 'expense',
                FinancialTransaction.created_at >= start_date,
                FinancialTransaction.created_at <= end_date
            ).group_by(FinancialTransaction.category).all()

            expense_breakdown = []
            total_expenses = 0

            for expense in expenses:
                expense_breakdown.append({
                    'category': expense[0],
                    'amount': float(expense[1])
                })
                total_expenses += expense[1]

            return {
                'success': True,
                'expense_breakdown': expense_breakdown,
                'total_expenses': float(total_expenses)
            }

        except Exception as e:
            logger.error(f"Error getting expense breakdown: {str(e)}")
            return {'success': False, 'error': str(e)}

    def calculate_tax_liability(self, start_date, end_date):
        """Calculate tax liability for the period"""
        try:
            # Get total sales for VAT calculation
            total_sales = db.session.query(func.sum(Sale.total_amount)).filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= start_date,
                Sale.created_at <= end_date
            ).scalar() or 0

            # Tanzania VAT rate is 18%
            vat_rate = 0.18
            vat_liability = total_sales * vat_rate

            # Corporate tax (estimated at 30% of net profit)
            profit_loss = self.get_profit_loss_statement(start_date, end_date)
            if profit_loss['success']:
                net_profit = profit_loss['statement']['net_profit']
                corporate_tax = max(0, net_profit * 0.30)  # Only if profit is positive
            else:
                corporate_tax = 0

            return {
                'success': True,
                'tax_liability': {
                    'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                    'total_sales': float(total_sales),
                    'vat_liability': float(vat_liability),
                    'corporate_tax': float(corporate_tax),
                    'total_tax_liability': float(vat_liability + corporate_tax)
                }
            }

        except Exception as e:
            logger.error(f"Error calculating tax liability: {str(e)}")
            return {'success': False, 'error': str(e)}
