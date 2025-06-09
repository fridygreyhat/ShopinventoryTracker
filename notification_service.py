from datetime import datetime, timedelta
from sqlalchemy import and_
from app import db
from models import User, Item
from email_service import EmailService
import logging

class NotificationService:
    """Service for managing business notifications"""
    
    @staticmethod
    def check_and_send_low_stock_alerts():
        """Check for low stock items and send alerts to users who have enabled them"""
        try:
            # Get all active users with low stock alerts enabled
            users = User.query.filter_by(
                active=True,
                low_stock_alerts=True,
                email_notifications=True
            ).all()
            
            for user in users:
                # Get items below threshold for this user
                low_stock_items = Item.query.filter(
                    and_(
                        Item.user_id == user.id,
                        Item.is_active == True,
                        Item.stock_quantity <= user.low_stock_threshold
                    )
                ).all()
                
                if low_stock_items:
                    # Send email notification
                    success = EmailService.send_low_stock_notification(user, low_stock_items)
                    if success:
                        logging.info(f"Low stock alert sent to {user.email}")
                    else:
                        logging.error(f"Failed to send low stock alert to {user.email}")
                        
        except Exception as e:
            logging.error(f"Error in low stock alert check: {str(e)}")
    
    @staticmethod
    def send_daily_sales_summary():
        """Send daily sales summary to users who have enabled sales reports"""
        try:
            from datetime import date
            from sqlalchemy import func
            from models import Sale, SaleItem
            
            today = date.today()
            
            # Get all active users with sales reports enabled
            users = User.query.filter_by(
                active=True,
                sales_reports=True,
                email_notifications=True
            ).all()
            
            for user in users:
                # Calculate today's sales data
                today_sales = db.session.query(
                    func.sum(Sale.total_amount),
                    func.count(Sale.id)
                ).filter(
                    and_(
                        Sale.user_id == user.id,
                        func.date(Sale.created_at) == today
                    )
                ).first()
                
                total_sales = today_sales[0] or 0
                transaction_count = today_sales[1] or 0
                
                # Get top selling item
                top_item = db.session.query(
                    Item.name,
                    func.sum(SaleItem.quantity).label('total_sold')
                ).join(SaleItem).join(Sale).filter(
                    and_(
                        Sale.user_id == user.id,
                        func.date(Sale.created_at) == today
                    )
                ).group_by(Item.id, Item.name).order_by(
                    func.sum(SaleItem.quantity).desc()
                ).first()
                
                top_product = top_item[0] if top_item else 'No sales today'
                
                # Calculate gross profit
                gross_profit = db.session.query(
                    func.sum((SaleItem.unit_price - SaleItem.unit_cost) * SaleItem.quantity)
                ).join(Sale).filter(
                    and_(
                        Sale.user_id == user.id,
                        func.date(Sale.created_at) == today
                    )
                ).scalar() or 0
                
                sales_data = {
                    'period': 'Today',
                    'total_sales': total_sales,
                    'transaction_count': transaction_count,
                    'top_product': top_product,
                    'gross_profit': gross_profit
                }
                
                # Only send if there were sales today
                if total_sales > 0:
                    success = EmailService.send_sales_summary_email(user, sales_data)
                    if success:
                        logging.info(f"Daily sales summary sent to {user.email}")
                    else:
                        logging.error(f"Failed to send sales summary to {user.email}")
                        
        except Exception as e:
            logging.error(f"Error in daily sales summary: {str(e)}")
    
    @staticmethod
    def check_stock_after_sale(user_id, item_ids):
        """Check stock levels after a sale and send immediate alerts if needed"""
        try:
            user = User.query.get(user_id)
            if not user or not user.low_stock_alerts or not user.email_notifications:
                return
            
            # Check if any of the sold items are now below threshold
            low_stock_items = Item.query.filter(
                and_(
                    Item.id.in_(item_ids),
                    Item.user_id == user_id,
                    Item.is_active == True,
                    Item.stock_quantity <= user.low_stock_threshold
                )
            ).all()
            
            if low_stock_items:
                # Send immediate alert
                success = EmailService.send_low_stock_notification(user, low_stock_items)
                if success:
                    logging.info(f"Immediate low stock alert sent to {user.email}")
                    
        except Exception as e:
            logging.error(f"Error in post-sale stock check: {str(e)}")