
from notifications.email_service import EmailService
from notifications.sms_service import SMSService
from models import db, User, Item, Sale
import logging

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self, user_id):
        self.user_id = user_id
        self.email_service = EmailService()
        self.sms_service = SMSService()

    def send_low_stock_alert(self, items):
        """Send low stock alert via email and SMS"""
        try:
            user = User.query.get(self.user_id)
            if not user:
                return {'success': False, 'error': 'User not found'}

            # Prepare alert message
            item_list = "\n".join([f"- {item.name}: {item.stock_quantity} remaining" for item in items])
            
            email_subject = "Low Stock Alert - Immediate Action Required"
            email_body = f"""
            Dear {user.first_name},

            The following items in your inventory are running low:

            {item_list}

            Please restock these items as soon as possible to avoid stockouts.

            Best regards,
            Inventory Management System
            """

            sms_message = f"Low Stock Alert: {len(items)} items need restocking. Check your inventory dashboard for details."

            # Send email
            email_result = self.email_service.send_email(
                to_email=user.email,
                subject=email_subject,
                body=email_body
            )

            # Send SMS if phone number is available
            sms_result = {'success': True, 'message': 'SMS not sent - no phone number'}
            if hasattr(user, 'phone') and user.phone:
                sms_result = self.sms_service.send_sms(
                    phone_number=user.phone,
                    message=sms_message
                )

            return {
                'success': True,
                'email_sent': email_result['success'],
                'sms_sent': sms_result['success'],
                'items_alerted': len(items)
            }

        except Exception as e:
            logger.error(f"Error sending low stock alert: {str(e)}")
            return {'success': False, 'error': str(e)}

    def send_sale_notification(self, sale_id):
        """Send sale confirmation notification"""
        try:
            sale = Sale.query.filter_by(id=sale_id, user_id=self.user_id).first()
            if not sale:
                return {'success': False, 'error': 'Sale not found'}

            user = User.query.get(self.user_id)
            
            # Prepare sale details
            items_summary = []
            for item in sale.sale_items:
                items_summary.append(f"{item.item.name} x{item.quantity}")

            email_subject = f"Sale Confirmation - {sale.sale_number}"
            email_body = f"""
            Sale Confirmation

            Sale Number: {sale.sale_number}
            Date: {sale.created_at.strftime('%Y-%m-%d %H:%M')}
            Customer: {sale.customer.name if sale.customer else 'Walk-in Customer'}
            Items: {', '.join(items_summary)}
            Total Amount: TZS {sale.total_amount:,.2f}
            Payment Method: {sale.payment_method.title()}

            Thank you for using our system!
            """

            # Send email notification
            email_result = self.email_service.send_email(
                to_email=user.email,
                subject=email_subject,
                body=email_body
            )

            # Send SMS to customer if phone is available
            customer_sms_result = {'success': True, 'message': 'Customer SMS not sent'}
            if sale.customer and sale.customer.phone:
                customer_message = f"Thank you for your purchase! Sale #{sale.sale_number} - Total: TZS {sale.total_amount:,.2f}"
                customer_sms_result = self.sms_service.send_sms(
                    phone_number=sale.customer.phone,
                    message=customer_message
                )

            return {
                'success': True,
                'email_sent': email_result['success'],
                'customer_sms_sent': customer_sms_result['success'],
                'sale_number': sale.sale_number
            }

        except Exception as e:
            logger.error(f"Error sending sale notification: {str(e)}")
            return {'success': False, 'error': str(e)}

    def send_daily_report(self):
        """Send daily sales report"""
        try:
            user = User.query.get(self.user_id)
            
            # Get today's sales
            from datetime import datetime, timedelta
            today = datetime.utcnow().date()
            
            sales_today = Sale.query.filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= today,
                Sale.created_at < today + timedelta(days=1)
            ).all()

            total_sales = sum(sale.total_amount for sale in sales_today)
            
            email_subject = f"Daily Sales Report - {today.strftime('%Y-%m-%d')}"
            email_body = f"""
            Daily Sales Report

            Date: {today.strftime('%Y-%m-%d')}
            Total Sales: {len(sales_today)}
            Total Revenue: TZS {total_sales:,.2f}

            Top Selling Items:
            {self._get_top_selling_items_today()}

            Have a great day!
            """

            # Send email
            email_result = self.email_service.send_email(
                to_email=user.email,
                subject=email_subject,
                body=email_body
            )

            return {
                'success': True,
                'email_sent': email_result['success'],
                'total_sales': len(sales_today),
                'total_revenue': float(total_sales)
            }

        except Exception as e:
            logger.error(f"Error sending daily report: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _get_top_selling_items_today(self):
        """Get top selling items for today"""
        try:
            from datetime import datetime, timedelta
            from sqlalchemy import func
            
            today = datetime.utcnow().date()
            
            top_items = db.session.query(
                Item.name,
                func.sum(Sale.sale_items.quantity).label('total_sold')
            ).join(Sale.sale_items).join(Sale).filter(
                Sale.user_id == self.user_id,
                Sale.created_at >= today,
                Sale.created_at < today + timedelta(days=1)
            ).group_by(Item.name).order_by(
                func.sum(Sale.sale_items.quantity).desc()
            ).limit(5).all()

            if not top_items:
                return "No sales recorded today"

            return "\n".join([f"- {item[0]}: {item[1]} sold" for item in top_items])

        except Exception as e:
            logger.error(f"Error getting top selling items: {str(e)}")
            return "Unable to retrieve top selling items"

    def send_custom_notification(self, message, channels=['email']):
        """Send custom notification via specified channels"""
        try:
            user = User.query.get(self.user_id)
            results = {}

            if 'email' in channels:
                email_result = self.email_service.send_email(
                    to_email=user.email,
                    subject="Custom Notification",
                    body=message
                )
                results['email'] = email_result['success']

            if 'sms' in channels and hasattr(user, 'phone') and user.phone:
                sms_result = self.sms_service.send_sms(
                    phone_number=user.phone,
                    message=message[:160]  # SMS character limit
                )
                results['sms'] = sms_result['success']

            return {
                'success': True,
                'results': results
            }

        except Exception as e:
            logger.error(f"Error sending custom notification: {str(e)}")
            return {'success': False, 'error': str(e)}
