import os
import logging
from typing import Optional, List
from twilio.rest import Client
from twilio.base.exceptions import TwilioException
from app import app
from models import User

class SMSService:
    """Comprehensive SMS service for business notifications using Twilio"""
    
    def __init__(self):
        self.account_sid = os.environ.get('TWILIO_ACCOUNT_SID')
        self.auth_token = os.environ.get('TWILIO_AUTH_TOKEN')
        self.from_phone = os.environ.get('TWILIO_PHONE_NUMBER')
        
        if not all([self.account_sid, self.auth_token, self.from_phone]):
            app.logger.warning("Twilio credentials not configured. SMS notifications disabled.")
            self.client = None
        else:
            try:
                self.client = Client(self.account_sid, self.auth_token)
                app.logger.info("Twilio SMS service initialized successfully")
            except Exception as e:
                app.logger.error(f"Failed to initialize Twilio client: {str(e)}")
                self.client = None
    
    def send_sms(self, to_phone: str, message: str) -> bool:
        """Send SMS to a phone number"""
        if not self.client:
            app.logger.warning("SMS service not available")
            return False
        
        try:
            # Ensure phone number format
            if not to_phone.startswith('+'):
                # Assume Tanzanian number if no country code
                to_phone = f"+255{to_phone.lstrip('0')}"
            
            message_instance = self.client.messages.create(
                body=message,
                from_=self.from_phone,
                to=to_phone
            )
            
            app.logger.info(f"SMS sent successfully to {to_phone}. SID: {message_instance.sid}")
            return True
            
        except TwilioException as e:
            app.logger.error(f"Twilio error sending SMS to {to_phone}: {str(e)}")
            return False
        except Exception as e:
            app.logger.error(f"Unexpected error sending SMS to {to_phone}: {str(e)}")
            return False
    
    def send_low_stock_alert(self, user: User, item_name: str, current_stock: int, threshold: int) -> bool:
        """Send low stock alert SMS"""
        if not user.phone or not user.sms_notifications:
            return False
        
        message = f"""
🚨 LOW STOCK ALERT - {user.shop_name or 'Your Business'}

Item: {item_name}
Current Stock: {current_stock}
Threshold: {threshold}

Please restock soon to avoid stockouts.

- Mauzo TZ Business System
        """.strip()
        
        return self.send_sms(user.phone, message)
    
    def send_sale_notification(self, user: User, sale_id: int, total_amount: float, customer_name: str = None) -> bool:
        """Send sale notification SMS"""
        if not user.phone or not user.sms_notifications:
            return False
        
        customer_info = f" to {customer_name}" if customer_name else ""
        
        message = f"""
💰 NEW SALE - {user.shop_name or 'Your Business'}

Sale #{sale_id}{customer_info}
Amount: TSh {total_amount:,.2f}

Thank you for using Mauzo TZ!
        """.strip()
        
        return self.send_sms(user.phone, message)
    
    def send_payment_reminder(self, customer_phone: str, customer_name: str, amount_due: float, due_date: str, business_name: str = None) -> bool:
        """Send payment reminder SMS to customer"""
        if not customer_phone:
            return False
        
        business_info = f" from {business_name}" if business_name else ""
        
        message = f"""
💳 PAYMENT REMINDER

Dear {customer_name},

You have an outstanding payment{business_info}:
Amount Due: TSh {amount_due:,.2f}
Due Date: {due_date}

Please make your payment at your earliest convenience.

Thank you!
        """.strip()
        
        return self.send_sms(customer_phone, message)
    
    def send_installment_reminder(self, customer_phone: str, customer_name: str, installment_amount: float, due_date: str, business_name: str = None) -> bool:
        """Send installment payment reminder SMS"""
        if not customer_phone:
            return False
        
        business_info = f" from {business_name}" if business_name else ""
        
        message = f"""
📅 INSTALLMENT DUE

Dear {customer_name},

Your installment payment{business_info} is due:
Amount: TSh {installment_amount:,.2f}
Due Date: {due_date}

Please make your payment to keep your account current.

Thank you!
        """.strip()
        
        return self.send_sms(customer_phone, message)
    
    def send_order_confirmation(self, customer_phone: str, customer_name: str, order_id: int, total_amount: float, business_name: str = None) -> bool:
        """Send order confirmation SMS to customer"""
        if not customer_phone:
            return False
        
        business_info = f" at {business_name}" if business_name else ""
        
        message = f"""
✅ ORDER CONFIRMED

Dear {customer_name},

Your order{business_info} has been confirmed:
Order #: {order_id}
Total: TSh {total_amount:,.2f}

We'll notify you when it's ready for pickup/delivery.

Thank you for your business!
        """.strip()
        
        return self.send_sms(customer_phone, message)
    
    def send_welcome_sms(self, user: User) -> bool:
        """Send welcome SMS to new user"""
        if not user.phone or not user.sms_notifications:
            return False
        
        message = f"""
🎉 Welcome to Mauzo TZ!

Hi {user.first_name}! Your business management account is ready.

Features available:
• Inventory Management
• Sales Tracking
• Customer Management
• Financial Reports

Login at: {app.config.get('SERVER_NAME', 'your-app-url')}

Support: info@mauzotz.com
        """.strip()
        
        return self.send_sms(user.phone, message)
    
    def send_daily_sales_summary(self, user: User, total_sales: float, transaction_count: int, date: str) -> bool:
        """Send daily sales summary SMS"""
        if not user.phone or not user.sms_notifications:
            return False
        
        message = f"""
📊 DAILY SALES SUMMARY - {date}

{user.shop_name or 'Your Business'}

Total Sales: TSh {total_sales:,.2f}
Transactions: {transaction_count}

Keep up the great work!

- Mauzo TZ
        """.strip()
        
        return self.send_sms(user.phone, message)
    
    def send_bulk_sms(self, phone_numbers: List[str], message: str) -> dict:
        """Send bulk SMS to multiple recipients"""
        results = {'success': 0, 'failed': 0, 'errors': []}
        
        for phone in phone_numbers:
            if self.send_sms(phone, message):
                results['success'] += 1
            else:
                results['failed'] += 1
                results['errors'].append(phone)
        
        return results
    
    def send_promotional_sms(self, customer_phone: str, customer_name: str, promotion_text: str, business_name: str = None) -> bool:
        """Send promotional SMS to customer"""
        if not customer_phone:
            return False
        
        business_info = f" from {business_name}" if business_name else ""
        
        message = f"""
🎁 SPECIAL OFFER{business_info}

Dear {customer_name},

{promotion_text}

Don't miss out on this great deal!

Reply STOP to opt out.
        """.strip()
        
        return self.send_sms(customer_phone, message)


# Create global SMS service instance
sms_service = SMSService()