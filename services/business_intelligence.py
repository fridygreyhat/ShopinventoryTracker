
from datetime import datetime, timedelta
from sqlalchemy import func, extract
from models import db
import json

class BusinessIntelligenceService:
    def __init__(self, user_id):
        self.user_id = user_id
    
    def get_real_time_kpis(self):
        """Get real-time KPI monitoring data"""
        from models import Sale, Item, FinancialTransaction, Customer
        
        today = datetime.utcnow().date()
        this_month_start = datetime(today.year, today.month, 1).date()
        last_month_start = (this_month_start - timedelta(days=1)).replace(day=1)
        
        # Sales KPIs
        today_sales = db.session.query(func.sum(Sale.total_amount)).filter(
            func.date(Sale.created_at) == today,
            Sale.user_id == self.user_id
        ).scalar() or 0
        
        this_month_sales = db.session.query(func.sum(Sale.total_amount)).filter(
            func.date(Sale.created_at) >= this_month_start,
            Sale.user_id == self.user_id
        ).scalar() or 0
        
        last_month_sales = db.session.query(func.sum(Sale.total_amount)).filter(
            func.date(Sale.created_at) >= last_month_start,
            func.date(Sale.created_at) < this_month_start,
            Sale.user_id == self.user_id
        ).scalar() or 0
        
        # Inventory KPIs
        total_items = Item.query.filter_by(user_id=self.user_id, is_active=True).count()
        low_stock_items = Item.query.filter(
            Item.user_id == self.user_id,
            Item.is_active == True,
            Item.stock_quantity <= Item.minimum_stock
        ).count()
        
        # Customer KPIs
        total_customers = Customer.query.filter_by(user_id=self.user_id).count() if hasattr(Customer, 'user_id') else 0
        new_customers_today = Customer.query.filter(
            func.date(Customer.created_at) == today,
            Customer.user_id == self.user_id
        ).count() if hasattr(Customer, 'user_id') else 0
        
        # Calculate growth rates
        sales_growth = ((this_month_sales - last_month_sales) / last_month_sales * 100) if last_month_sales > 0 else 0
        
        return {
            "sales": {
                "today": today_sales,
                "this_month": this_month_sales,
                "last_month": last_month_sales,
                "growth_rate": round(sales_growth, 2)
            },
            "inventory": {
                "total_items": total_items,
                "low_stock_items": low_stock_items,
                "stock_health": round((1 - low_stock_items / total_items) * 100, 2) if total_items > 0 else 0
            },
            "customers": {
                "total": total_customers,
                "new_today": new_customers_today
            },
            "last_updated": datetime.utcnow().isoformat()
        }
    
    def get_comparative_analysis(self, period='monthly'):
        """Get Year-over-Year and Month-over-Month comparative analysis"""
        from models import Sale, FinancialTransaction
        
        current_date = datetime.utcnow()
        
        if period == 'monthly':
            # Month-over-Month analysis
            periods = []
            for i in range(12):
                period_date = current_date - timedelta(days=30*i)
                period_start = period_date.replace(day=1).date()
                if period_date.month == 12:
                    period_end = period_date.replace(year=period_date.year + 1, month=1, day=1).date() - timedelta(days=1)
                else:
                    period_end = period_date.replace(month=period_date.month + 1, day=1).date() - timedelta(days=1)
                
                # Sales data
                sales = db.session.query(func.sum(Sale.total_amount)).filter(
                    func.date(Sale.created_at) >= period_start,
                    func.date(Sale.created_at) <= period_end,
                    Sale.user_id == self.user_id
                ).scalar() or 0
                
                # Expense data
                expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                    FinancialTransaction.date >= period_start,
                    FinancialTransaction.date <= period_end,
                    FinancialTransaction.transaction_type == 'Expense',
                    FinancialTransaction.user_id == self.user_id
                ).scalar() or 0
                
                periods.append({
                    "period": period_start.strftime('%Y-%m'),
                    "sales": sales,
                    "expenses": expenses,
                    "profit": sales - expenses
                })
        
        else:  # yearly
            # Year-over-Year analysis
            periods = []
            for i in range(3):
                year = current_date.year - i
                period_start = datetime(year, 1, 1).date()
                period_end = datetime(year, 12, 31).date()
                
                # Sales data
                sales = db.session.query(func.sum(Sale.total_amount)).filter(
                    func.date(Sale.created_at) >= period_start,
                    func.date(Sale.created_at) <= period_end,
                    Sale.user_id == self.user_id
                ).scalar() or 0
                
                # Expense data
                expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
                    FinancialTransaction.date >= period_start,
                    FinancialTransaction.date <= period_end,
                    FinancialTransaction.transaction_type == 'Expense',
                    FinancialTransaction.user_id == self.user_id
                ).scalar() or 0
                
                periods.append({
                    "period": str(year),
                    "sales": sales,
                    "expenses": expenses,
                    "profit": sales - expenses
                })
        
        return periods
    
    def get_profit_margin_analysis(self):
        """Get profit margin analysis by product and category"""
        from models import Item, SaleItem, Sale
        
        # Analyze by category
        category_analysis = db.session.query(
            Item.category,
            func.sum(SaleItem.quantity * SaleItem.price).label('revenue'),
            func.sum(SaleItem.quantity * Item.buying_price).label('cost')
        ).join(SaleItem).join(Sale).filter(
            Item.user_id == self.user_id,
            Sale.user_id == self.user_id
        ).group_by(Item.category).all()
        
        categories = []
        for cat in category_analysis:
            revenue = cat.revenue or 0
            cost = cat.cost or 0
            profit = revenue - cost
            margin = (profit / revenue * 100) if revenue > 0 else 0
            
            categories.append({
                "category": cat.category or "Uncategorized",
                "revenue": revenue,
                "cost": cost,
                "profit": profit,
                "margin_percent": round(margin, 2)
            })
        
        # Top performing products
        product_analysis = db.session.query(
            Item.id,
            Item.name,
            func.sum(SaleItem.quantity).label('total_sold'),
            func.sum(SaleItem.quantity * SaleItem.price).label('revenue'),
            func.sum(SaleItem.quantity * Item.buying_price).label('cost')
        ).join(SaleItem).join(Sale).filter(
            Item.user_id == self.user_id,
            Sale.user_id == self.user_id
        ).group_by(Item.id, Item.name).order_by(
            func.sum(SaleItem.quantity * SaleItem.price).desc()
        ).limit(10).all()
        
        products = []
        for prod in product_analysis:
            revenue = prod.revenue or 0
            cost = prod.cost or 0
            profit = revenue - cost
            margin = (profit / revenue * 100) if revenue > 0 else 0
            
            products.append({
                "id": prod.id,
                "name": prod.name,
                "total_sold": prod.total_sold,
                "revenue": revenue,
                "cost": cost,
                "profit": profit,
                "margin_percent": round(margin, 2)
            })
        
        return {
            "categories": categories,
            "top_products": products
        }
    
    def get_cash_flow_forecast(self, days_ahead=30):
        """Generate cash flow forecasting"""
        from models import Sale, FinancialTransaction, Item
        
        # Historical data analysis
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=90)
        
        # Daily sales pattern
        daily_sales = db.session.query(
            func.date(Sale.created_at).label('date'),
            func.sum(Sale.total_amount).label('amount')
        ).filter(
            func.date(Sale.created_at) >= start_date,
            Sale.user_id == self.user_id
        ).group_by(func.date(Sale.created_at)).all()
        
        # Calculate average daily sales
        total_sales = sum(day.amount for day in daily_sales)
        avg_daily_sales = total_sales / len(daily_sales) if daily_sales else 0
        
        # Daily expenses pattern
        daily_expenses = db.session.query(
            FinancialTransaction.date,
            func.sum(FinancialTransaction.amount).label('amount')
        ).filter(
            FinancialTransaction.date >= start_date,
            FinancialTransaction.transaction_type == 'Expense',
            FinancialTransaction.user_id == self.user_id
        ).group_by(FinancialTransaction.date).all()
        
        total_expenses = sum(day.amount for day in daily_expenses)
        avg_daily_expenses = total_expenses / len(daily_expenses) if daily_expenses else 0
        
        # Generate forecast
        forecast = []
        current_cash = self._get_current_cash_balance()
        
        for i in range(days_ahead):
            forecast_date = end_date + timedelta(days=i+1)
            
            # Apply weekly patterns (lower sales on weekends)
            weekday = forecast_date.weekday()
            sales_multiplier = 0.7 if weekday in [5, 6] else 1.0
            
            projected_income = avg_daily_sales * sales_multiplier
            projected_expenses = avg_daily_expenses
            net_change = projected_income - projected_expenses
            current_cash += net_change
            
            forecast.append({
                "date": forecast_date.isoformat(),
                "projected_income": round(projected_income, 2),
                "projected_expenses": round(projected_expenses, 2),
                "net_change": round(net_change, 2),
                "cumulative_cash": round(current_cash, 2)
            })
        
        return {
            "current_cash_balance": round(self._get_current_cash_balance(), 2),
            "avg_daily_sales": round(avg_daily_sales, 2),
            "avg_daily_expenses": round(avg_daily_expenses, 2),
            "forecast": forecast
        }
    
    def _get_current_cash_balance(self):
        """Calculate current cash balance from financial transactions"""
        from models import FinancialTransaction
        
        income = db.session.query(func.sum(FinancialTransaction.amount)).filter(
            FinancialTransaction.transaction_type == 'Income',
            FinancialTransaction.user_id == self.user_id
        ).scalar() or 0
        
        expenses = db.session.query(func.sum(FinancialTransaction.amount)).filter(
            FinancialTransaction.transaction_type == 'Expense',
            FinancialTransaction.user_id == self.user_id
        ).scalar() or 0
        
        return income - expenses
    
    def get_dashboard_widgets(self):
        """Get all dashboard widgets data in one call"""
        return {
            "kpis": self.get_real_time_kpis(),
            "comparative_analysis": self.get_comparative_analysis(),
            "profit_margins": self.get_profit_margin_analysis(),
            "cash_flow": self.get_cash_flow_forecast(30)
        }
