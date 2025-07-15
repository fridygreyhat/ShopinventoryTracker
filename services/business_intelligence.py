from datetime import datetime, timedelta
from flask import current_app
from models import db, Sale, Item, FinancialTransaction, Customer
from sqlalchemy import func, and_, extract
import logging

logger = logging.getLogger(__name__)

class BusinessIntelligenceService:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_real_time_kpis(self):
        """Get real-time KPI data"""
        try:
            # Calculate basic KPIs
            today = datetime.now().date()
            month_start = today.replace(day=1)

            # Total sales this month
            monthly_sales = db.session.query(func.sum(Sale.total_amount)).filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= month_start
            ).scalar() or 0

            # Total items
            total_items = Item.query.filter_by(user_id=self.user_id, is_active=True).count()

            # Low stock items
            low_stock_items = Item.query.filter(
                Item.user_id == self.user_id,
                Item.is_active == True,
                Item.stock_quantity <= Item.minimum_stock
            ).count()

            # Total customers
            total_customers = Customer.query.filter_by(user_id=self.user_id).count()

            return {
                'success': True,
                'kpis': {
                    'monthly_sales': float(monthly_sales),
                    'total_items': total_items,
                    'low_stock_items': low_stock_items,
                    'total_customers': total_customers,
                    'generated_at': datetime.now().isoformat()
                }
            }
        except Exception as e:
            logger.error(f"Error getting KPIs: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_comparative_analysis(self, period='monthly'):
        """Get comparative analysis (YoY, MoM)"""
        try:
            today = datetime.now()
            current_month = today.month
            current_year = today.year

            # Current month sales
            current_sales = db.session.query(func.sum(Sale.total_amount)).filter(
                Sale.user_id == self.user_id,
                extract('month', Sale.created_at) == current_month,
                extract('year', Sale.created_at) == current_year
            ).scalar() or 0

            # Previous month sales
            prev_month = current_month - 1 if current_month > 1 else 12
            prev_year = current_year if current_month > 1 else current_year - 1

            prev_sales = db.session.query(func.sum(Sale.total_amount)).filter(
                Sale.user_id == self.user_id,
                extract('month', Sale.created_at) == prev_month,
                extract('year', Sale.created_at) == prev_year
            ).scalar() or 0

            # Calculate growth
            if prev_sales > 0:
                growth_rate = ((current_sales - prev_sales) / prev_sales) * 100
            else:
                growth_rate = 100 if current_sales > 0 else 0

            return {
                'success': True,
                'analysis': {
                    'current_period': float(current_sales),
                    'previous_period': float(prev_sales),
                    'growth_rate': round(growth_rate, 2),
                    'period': period
                }
            }
        except Exception as e:
            logger.error(f"Error in comparative analysis: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_profit_margin_analysis(self):
        """Get profit margin analysis"""
        try:
            # Get items with sales data
            items_with_profit = db.session.query(
                Item.id,
                Item.name,
                Item.buying_price,
                Item.retail_price,
                func.sum(Sale.total_amount).label('total_revenue')
            ).join(Sale).filter(
                Sale.user_id == self.user_id,
                Item.user_id == self.user_id
            ).group_by(Item.id).all()

            profit_data = []
            for item in items_with_profit:
                if item.retail_price and item.buying_price:
                    profit_margin = ((item.retail_price - item.buying_price) / item.retail_price) * 100
                    profit_data.append({
                        'item_name': item.name,
                        'profit_margin': round(profit_margin, 2),
                        'total_revenue': float(item.total_revenue or 0)
                    })

            return {
                'success': True,
                'profit_analysis': profit_data[:10]  # Top 10
            }
        except Exception as e:
            logger.error(f"Error in profit margin analysis: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_cash_flow_forecast(self, days_ahead=30):
        """Get cash flow forecasting"""
        try:
            # Simple forecast based on historical data
            end_date = datetime.now() + timedelta(days=days_ahead)

            # Average daily income from last 30 days
            thirty_days_ago = datetime.now() - timedelta(days=30)
            avg_daily_income = db.session.query(func.avg(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == self.user_id,
                FinancialTransaction.transaction_type == 'Income',
                FinancialTransaction.created_at >= thirty_days_ago
            ).scalar() or 0

            # Average daily expenses
            avg_daily_expenses = db.session.query(func.avg(FinancialTransaction.amount)).filter(
                FinancialTransaction.user_id == self.user_id,
                FinancialTransaction.transaction_type == 'Expense',
                FinancialTransaction.created_at >= thirty_days_ago
            ).scalar() or 0

            projected_income = float(avg_daily_income) * days_ahead
            projected_expenses = float(avg_daily_expenses) * days_ahead
            projected_net = projected_income - projected_expenses

            return {
                'success': True,
                'forecast': {
                    'days_ahead': days_ahead,
                    'projected_income': round(projected_income, 2),
                    'projected_expenses': round(projected_expenses, 2),
                    'projected_net_cash_flow': round(projected_net, 2)
                }
            }
        except Exception as e:
            logger.error(f"Error in cash flow forecast: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_dashboard_widgets(self):
        """Get all BI dashboard data in one call"""
        try:
            kpis = self.get_real_time_kpis()
            comparative = self.get_comparative_analysis()
            profit_margins = self.get_profit_margin_analysis()
            cash_flow = self.get_cash_flow_forecast()

            return {
                'success': True,
                'dashboard': {
                    'kpis': kpis.get('kpis', {}),
                    'comparative_analysis': comparative.get('analysis', {}),
                    'profit_margins': profit_margins.get('profit_analysis', []),
                    'cash_flow_forecast': cash_flow.get('forecast', {})
                }
            }
        except Exception as e:
            logger.error(f"Error getting dashboard widgets: {str(e)}")
            return {'success': False, 'error': str(e)}