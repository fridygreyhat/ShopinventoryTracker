
from datetime import datetime, timedelta
from models import db, Sale, Item, Customer, SaleItem
from sqlalchemy import func, and_, extract
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    def __init__(self, user_id):
        self.user_id = user_id

    def get_sales_kpis(self, period='monthly'):
        """Get sales KPIs for specified period"""
        try:
            now = datetime.utcnow()
            
            if period == 'daily':
                start_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            elif period == 'weekly':
                start_date = now - timedelta(days=7)
            elif period == 'monthly':
                start_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            else:
                start_date = now - timedelta(days=30)

            # Total sales
            total_sales = db.session.query(func.sum(Sale.total_amount)).filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= start_date
            ).scalar() or 0

            # Sales count
            sales_count = Sale.query.filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= start_date
            ).count()

            # Average order value
            avg_order_value = total_sales / sales_count if sales_count > 0 else 0

            # Top selling items
            top_items = db.session.query(
                Item.name,
                func.sum(SaleItem.quantity).label('total_sold')
            ).join(SaleItem).join(Sale).filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= start_date
            ).group_by(Item.id, Item.name).order_by(
                func.sum(SaleItem.quantity).desc()
            ).limit(5).all()

            return {
                'period': period,
                'total_sales': float(total_sales),
                'sales_count': sales_count,
                'avg_order_value': float(avg_order_value),
                'top_items': [{'name': item[0], 'quantity_sold': item[1]} for item in top_items]
            }

        except Exception as e:
            logger.error(f"Error getting sales KPIs: {str(e)}")
            return {'error': str(e)}

    def get_inventory_kpis(self):
        """Get inventory KPIs"""
        try:
            # Total items
            total_items = Item.query.filter_by(user_id=self.user_id).count()

            # Total stock value
            total_stock_value = db.session.query(
                func.sum(Item.stock_quantity * Item.price)
            ).filter_by(user_id=self.user_id).scalar() or 0

            # Low stock items
            low_stock_items = Item.query.filter(
                Item.user_id == self.user_id,
                Item.stock_quantity <= Item.reorder_level
            ).count()

            # Out of stock items
            out_of_stock = Item.query.filter(
                Item.user_id == self.user_id,
                Item.stock_quantity == 0
            ).count()

            return {
                'total_items': total_items,
                'total_stock_value': float(total_stock_value),
                'low_stock_items': low_stock_items,
                'out_of_stock_items': out_of_stock
            }

        except Exception as e:
            logger.error(f"Error getting inventory KPIs: {str(e)}")
            return {'error': str(e)}

    def get_customer_analytics(self):
        """Get customer analytics"""
        try:
            # Total customers
            total_customers = Customer.query.filter_by(user_id=self.user_id).count()

            # Customer with most purchases
            top_customer = db.session.query(
                Customer.name,
                func.count(Sale.id).label('purchase_count'),
                func.sum(Sale.total_amount).label('total_spent')
            ).join(Sale).filter(
                Sale.user_id == self.user_id
            ).group_by(Customer.id, Customer.name).order_by(
                func.sum(Sale.total_amount).desc()
            ).first()

            # New customers this month
            start_of_month = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            new_customers = Customer.query.filter(
                Customer.user_id == self.user_id,
                Customer.created_at >= start_of_month
            ).count()

            return {
                'total_customers': total_customers,
                'top_customer': {
                    'name': top_customer[0] if top_customer else None,
                    'purchase_count': top_customer[1] if top_customer else 0,
                    'total_spent': float(top_customer[2]) if top_customer else 0
                },
                'new_customers_this_month': new_customers
            }

        except Exception as e:
            logger.error(f"Error getting customer analytics: {str(e)}")
            return {'error': str(e)}

    def generate_sales_report(self, start_date, end_date):
        """Generate detailed sales report"""
        try:
            sales = Sale.query.filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= start_date,
                Sale.created_at <= end_date
            ).order_by(Sale.created_at.desc()).all()

            report_data = []
            total_revenue = 0

            for sale in sales:
                sale_data = {
                    'sale_number': sale.sale_number,
                    'date': sale.created_at.strftime('%Y-%m-%d %H:%M'),
                    'customer': sale.customer.name if sale.customer else 'Walk-in',
                    'total_amount': float(sale.total_amount),
                    'payment_method': sale.payment_method,
                    'items': []
                }

                for item in sale.sale_items:
                    sale_data['items'].append({
                        'name': item.item.name,
                        'quantity': item.quantity,
                        'price': float(item.price),
                        'total': float(item.quantity * item.price)
                    })

                report_data.append(sale_data)
                total_revenue += sale.total_amount

            return {
                'period': f"{start_date.strftime('%Y-%m-%d')} to {end_date.strftime('%Y-%m-%d')}",
                'total_revenue': float(total_revenue),
                'total_sales': len(sales),
                'sales': report_data
            }

        except Exception as e:
            logger.error(f"Error generating sales report: {str(e)}")
            return {'error': str(e)}
