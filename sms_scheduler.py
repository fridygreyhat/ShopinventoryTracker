import os
import logging
from datetime import datetime, timedelta, date
from typing import List
from app import app, db
from models import User, Customer, InstallmentPlan, Sale
from sms_service import sms_service

class SMSScheduler:
    """Automated SMS scheduling and management system"""
    
    @staticmethod
    def send_daily_summaries():
        """Send daily sales summaries to users who have enabled them"""
        try:
            from sqlalchemy import func
            from models import SaleItem
            
            # Get users with SMS notifications and sales reports enabled
            users = User.query.filter_by(
                active=True,
                sms_notifications=True,
                sales_reports=True
            ).filter(User.phone.isnot(None)).all()
            
            today = date.today()
            
            for user in users:
                # Calculate daily sales for this user
                daily_sales = db.session.query(
                    func.sum(Sale.total_amount).label('total_sales'),
                    func.count(Sale.id).label('transaction_count')
                ).filter(
                    Sale.user_id == user.id,
                    func.date(Sale.created_at) == today
                ).first()
                
                total_sales = float(daily_sales.total_sales or 0)
                transaction_count = int(daily_sales.transaction_count or 0)
                
                if total_sales > 0 or transaction_count > 0:
                    success = sms_service.send_daily_sales_summary(
                        user, total_sales, transaction_count, today.strftime('%Y-%m-%d')
                    )
                    
                    if success:
                        logging.info(f"Daily summary SMS sent to {user.phone}")
                    else:
                        logging.error(f"Failed to send daily summary SMS to {user.phone}")
                        
        except Exception as e:
            logging.error(f"Error sending daily SMS summaries: {str(e)}")
    
    @staticmethod
    def send_payment_reminders():
        """Send payment reminders for overdue installments"""
        try:
            from models import InstallmentPayment
            
            # Find overdue installments
            today = date.today()
            overdue_payments = db.session.query(InstallmentPayment).join(
                InstallmentPlan
            ).join(Customer).filter(
                InstallmentPayment.due_date < today,
                InstallmentPayment.status == 'pending'
            ).all()
            
            for payment in overdue_payments:
                customer = payment.installment_plan.customer
                plan = payment.installment_plan
                
                if customer.phone:
                    # Get business name from the plan's sale
                    business_name = plan.sale.user.shop_name if plan.sale and plan.sale.user else None
                    
                    days_overdue = (today - payment.due_date).days
                    due_date_str = payment.due_date.strftime('%d/%m/%Y')
                    
                    success = sms_service.send_payment_reminder(
                        customer.phone,
                        customer.name,
                        float(payment.amount),
                        f"{due_date_str} ({days_overdue} days overdue)",
                        business_name
                    )
                    
                    if success:
                        logging.info(f"Payment reminder SMS sent to {customer.phone}")
                    else:
                        logging.error(f"Failed to send payment reminder SMS to {customer.phone}")
                        
        except Exception as e:
            logging.error(f"Error sending payment reminder SMS: {str(e)}")
    
    @staticmethod
    def send_upcoming_payment_reminders():
        """Send reminders for payments due in 3 days"""
        try:
            from models import InstallmentPayment
            
            # Find payments due in 3 days
            reminder_date = date.today() + timedelta(days=3)
            upcoming_payments = db.session.query(InstallmentPayment).join(
                InstallmentPlan
            ).join(Customer).filter(
                InstallmentPayment.due_date == reminder_date,
                InstallmentPayment.status == 'pending'
            ).all()
            
            for payment in upcoming_payments:
                customer = payment.installment_plan.customer
                plan = payment.installment_plan
                
                if customer.phone:
                    business_name = plan.sale.user.shop_name if plan.sale and plan.sale.user else None
                    due_date_str = payment.due_date.strftime('%d/%m/%Y')
                    
                    success = sms_service.send_installment_reminder(
                        customer.phone,
                        customer.name,
                        float(payment.amount),
                        due_date_str,
                        business_name
                    )
                    
                    if success:
                        logging.info(f"Upcoming payment reminder SMS sent to {customer.phone}")
                    else:
                        logging.error(f"Failed to send upcoming payment reminder SMS to {customer.phone}")
                        
        except Exception as e:
            logging.error(f"Error sending upcoming payment reminder SMS: {str(e)}")
    
    @staticmethod
    def send_welcome_sms_to_new_users():
        """Send welcome SMS to users registered in the last 24 hours"""
        try:
            # Find users registered in the last 24 hours with SMS enabled
            yesterday = datetime.utcnow() - timedelta(hours=24)
            new_users = User.query.filter(
                User.created_at >= yesterday,
                User.sms_notifications == True,
                User.phone.isnot(None)
            ).all()
            
            for user in new_users:
                success = sms_service.send_welcome_sms(user)
                
                if success:
                    logging.info(f"Welcome SMS sent to new user {user.phone}")
                else:
                    logging.error(f"Failed to send welcome SMS to new user {user.phone}")
                    
        except Exception as e:
            logging.error(f"Error sending welcome SMS to new users: {str(e)}")
    
    @staticmethod
    def run_scheduled_tasks():
        """Run all scheduled SMS tasks"""
        logging.info("Starting scheduled SMS tasks")
        
        # Send daily summaries
        SMSScheduler.send_daily_summaries()
        
        # Send payment reminders
        SMSScheduler.send_payment_reminders()
        
        # Send upcoming payment reminders
        SMSScheduler.send_upcoming_payment_reminders()
        
        # Send welcome SMS to new users
        SMSScheduler.send_welcome_sms_to_new_users()
        
        logging.info("Completed scheduled SMS tasks")


# Create scheduler instance
sms_scheduler = SMSScheduler()