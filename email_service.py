import os
import secrets
from datetime import datetime, timedelta
from typing import Optional
from flask import url_for, render_template_string
from flask_mail import Message
from app import app, db, mail
from models import User

class EmailService:
    """Comprehensive email service for notifications and password reset"""
    
    @staticmethod
    def send_email(to: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
        """Send email using Flask-Mail"""
        try:
            msg = Message(
                subject=subject,
                sender=app.config['MAIL_DEFAULT_SENDER'],
                recipients=[to]
            )
            msg.body = body
            if html_body:
                msg.html = html_body
            
            mail.send(msg)
            return True
        except Exception as e:
            app.logger.error(f"Failed to send email to {to}: {str(e)}")
            return False
    
    @staticmethod
    def send_password_reset_email(user: User) -> bool:
        """Send password reset email"""
        try:
            # Generate reset token
            token = secrets.token_urlsafe(32)
            expires_at = datetime.utcnow() + timedelta(hours=1)  # 1 hour expiry
            
            # Store token in user record
            user.reset_token = token
            user.reset_token_expires = expires_at
            db.session.commit()
            
            # Create reset URL
            reset_url = url_for('auth.reset_password', token=token, _external=True)
            
            # Email content
            subject = "Password Reset - Mauzo TZ Business Management"
            
            body = f"""
Dear {user.first_name or user.email},

You have requested to reset your password for your Mauzo TZ account.

Click the link below to reset your password:
{reset_url}

This link will expire in 1 hour for security reasons.

If you did not request this password reset, please ignore this email.

Best regards,
Mauzo TZ Team
info@mauzotz.com
            """
            
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #007bff; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f8f9fa; }}
        .button {{ display: inline-block; padding: 12px 24px; background-color: #007bff; color: white; text-decoration: none; border-radius: 4px; margin: 20px 0; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Password Reset Request</h1>
        </div>
        <div class="content">
            <p>Dear {user.first_name or user.email},</p>
            
            <p>You have requested to reset your password for your Mauzo TZ account.</p>
            
            <p>Click the button below to reset your password:</p>
            
            <a href="{reset_url}" class="button">Reset Password</a>
            
            <p>Or copy and paste this link into your browser:</p>
            <p><a href="{reset_url}">{reset_url}</a></p>
            
            <p><strong>This link will expire in 1 hour for security reasons.</strong></p>
            
            <p>If you did not request this password reset, please ignore this email.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>
            Mauzo TZ Team<br>
            info@mauzotz.com</p>
        </div>
    </div>
</body>
</html>
            """
            
            return EmailService.send_email(user.email, subject, body, html_body)
            
        except Exception as e:
            app.logger.error(f"Failed to send password reset email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_welcome_email(user: User) -> bool:
        """Send welcome email to new users"""
        try:
            subject = "Welcome to Mauzo TZ - Your Business Management Platform"
            
            body = f"""
Dear {user.first_name or user.email},

Welcome to Mauzo TZ!

Your account has been successfully created. You can now access all the powerful features of our business management platform:

• Inventory Management
• Sales Tracking
• Financial Analytics
• Customer Management
• Multi-location Support
• And much more!

Get started by logging into your account and exploring the dashboard.

If you have any questions or need assistance, please don't hesitate to contact us.

Best regards,
Mauzo TZ Team
info@mauzotz.com
            """
            
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #28a745; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f8f9fa; }}
        .features {{ list-style-type: none; padding: 0; }}
        .features li {{ padding: 8px 0; }}
        .features li:before {{ content: "✓ "; color: #28a745; font-weight: bold; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to Mauzo TZ!</h1>
        </div>
        <div class="content">
            <p>Dear {user.first_name or user.email},</p>
            
            <p>Welcome to Mauzo TZ! Your account has been successfully created.</p>
            
            <p>You can now access all the powerful features of our business management platform:</p>
            
            <ul class="features">
                <li>Inventory Management</li>
                <li>Sales Tracking</li>
                <li>Financial Analytics</li>
                <li>Customer Management</li>
                <li>Multi-location Support</li>
                <li>Comprehensive Reporting</li>
            </ul>
            
            <p>Get started by logging into your account and exploring the dashboard.</p>
            
            <p>If you have any questions or need assistance, please don't hesitate to contact us.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>
            Mauzo TZ Team<br>
            info@mauzotz.com</p>
        </div>
    </div>
</body>
</html>
            """
            
            return EmailService.send_email(user.email, subject, body, html_body)
            
        except Exception as e:
            app.logger.error(f"Failed to send welcome email to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_low_stock_notification(user: User, low_stock_items: list) -> bool:
        """Send low stock notification email"""
        try:
            subject = "Low Stock Alert - Mauzo TZ"
            
            items_text = "\n".join([f"• {item.name} - Current Stock: {item.stock_quantity}" for item in low_stock_items])
            
            body = f"""
Dear {user.first_name or user.email},

This is an automated alert to inform you that some items in your inventory are running low on stock:

{items_text}

Please consider restocking these items to avoid stockouts.

You can manage your inventory by logging into your Mauzo TZ account.

Best regards,
Mauzo TZ Team
info@mauzotz.com
            """
            
            items_html = "".join([f"<li>{item.name} - Current Stock: <strong>{item.stock_quantity}</strong></li>" for item in low_stock_items])
            
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #ffc107; color: #212529; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f8f9fa; }}
        .alert {{ background-color: #fff3cd; border: 1px solid #ffeaa7; padding: 15px; border-radius: 4px; margin: 15px 0; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>⚠️ Low Stock Alert</h1>
        </div>
        <div class="content">
            <p>Dear {user.first_name or user.email},</p>
            
            <div class="alert">
                <p><strong>Some items in your inventory are running low on stock:</strong></p>
                <ul>
                    {items_html}
                </ul>
            </div>
            
            <p>Please consider restocking these items to avoid stockouts.</p>
            
            <p>You can manage your inventory by logging into your Mauzo TZ account.</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>
            Mauzo TZ Team<br>
            info@mauzotz.com</p>
        </div>
    </div>
</body>
</html>
            """
            
            return EmailService.send_email(user.email, subject, body, html_body)
            
        except Exception as e:
            app.logger.error(f"Failed to send low stock notification to {user.email}: {str(e)}")
            return False
    
    @staticmethod
    def send_sales_summary_email(user: User, sales_data: dict) -> bool:
        """Send daily/weekly sales summary email"""
        try:
            subject = f"Sales Summary - {sales_data.get('period', 'Today')} - Mauzo TZ"
            
            body = f"""
Dear {user.first_name or user.email},

Here's your sales summary for {sales_data.get('period', 'today')}:

Total Sales: Tsh {sales_data.get('total_sales', 0):,.2f}
Number of Transactions: {sales_data.get('transaction_count', 0)}
Top Product: {sales_data.get('top_product', 'N/A')}
Gross Profit: Tsh {sales_data.get('gross_profit', 0):,.2f}

Thank you for using Mauzo TZ to manage your business!

Best regards,
Mauzo TZ Team
info@mauzotz.com
            """
            
            html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #17a2b8; color: white; padding: 20px; text-align: center; }}
        .content {{ padding: 20px; background-color: #f8f9fa; }}
        .metrics {{ display: flex; flex-wrap: wrap; margin: 20px 0; }}
        .metric {{ background: white; padding: 15px; margin: 5px; border-radius: 4px; flex: 1; min-width: 200px; text-align: center; }}
        .metric-value {{ font-size: 24px; font-weight: bold; color: #007bff; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 Sales Summary</h1>
            <p>{sales_data.get('period', 'Today')}</p>
        </div>
        <div class="content">
            <p>Dear {user.first_name or user.email},</p>
            
            <p>Here's your sales summary for {sales_data.get('period', 'today')}:</p>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">Tsh {sales_data.get('total_sales', 0):,.2f}</div>
                    <div>Total Sales</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{sales_data.get('transaction_count', 0)}</div>
                    <div>Transactions</div>
                </div>
                <div class="metric">
                    <div class="metric-value">Tsh {sales_data.get('gross_profit', 0):,.2f}</div>
                    <div>Gross Profit</div>
                </div>
            </div>
            
            <p><strong>Top Product:</strong> {sales_data.get('top_product', 'N/A')}</p>
            
            <p>Thank you for using Mauzo TZ to manage your business!</p>
        </div>
        <div class="footer">
            <p>Best regards,<br>
            Mauzo TZ Team<br>
            info@mauzotz.com</p>
        </div>
    </div>
</body>
</html>
            """
            
            return EmailService.send_email(user.email, subject, body, html_body)
            
        except Exception as e:
            app.logger.error(f"Failed to send sales summary email to {user.email}: {str(e)}")
            return False