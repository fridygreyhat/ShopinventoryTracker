import os
import logging
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content

# Set up logging
logger = logging.getLogger(__name__)

# Get SendGrid API key from environment variable
SENDGRID_API_KEY = os.environ.get("SENDGRID_API_KEY")

def send_email(to_email, from_email, subject, html_content=None, text_content=None):
    """
    Send email using SendGrid
    
    Args:
        to_email (str): Recipient's email address
        from_email (str): Sender's email address
        subject (str): Email subject
        html_content (str, optional): HTML content of the email
        text_content (str, optional): Plain text content of the email
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Validate SendGrid API key
    if not SENDGRID_API_KEY:
        logger.error("SendGrid API key is not properly configured")
        return False
    
    try:
        # Initialize SendGrid client
        sg = SendGridAPIClient(SENDGRID_API_KEY)
        
        # Create message
        message = Mail(
            from_email=Email(from_email),
            to_emails=To(to_email),
            subject=subject
        )
        
        # Add content to message
        if html_content:
            message.content = Content("text/html", html_content)
        elif text_content:
            message.content = Content("text/plain", text_content)
        else:
            logger.error("Either HTML or text content must be provided")
            return False
        
        # Send email
        response = sg.send(message)
        logger.info(f"Email sent successfully. Status: {response.status_code}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send email: {str(e)}")
        return False

def send_low_stock_email(to_email, from_email, low_stock_items):
    """
    Send low stock notification email
    
    Args:
        to_email (str): Recipient's email address
        from_email (str): Sender's email address
        low_stock_items (list): List of low stock items
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not low_stock_items:
        return False
    
    # Create email subject
    subject = "Low Stock Alert - Inventory Management System"
    
    # Create table rows for low stock items
    item_rows = ""
    for item in low_stock_items:
        item_rows += f"""
        <tr>
            <td style="padding: 8px; border: 1px solid #ddd;">{item['name']}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{item['sku'] or 'N/A'}</td>
            <td style="padding: 8px; border: 1px solid #ddd; text-align: center;">{item['quantity']}</td>
            <td style="padding: 8px; border: 1px solid #ddd;">{item['category'] or 'N/A'}</td>
        </tr>
        """
    
    # Create HTML content
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .header {{ background-color: #f44336; color: white; padding: 15px; text-align: center; }}
            .content {{ padding: 20px; background-color: #f9f9f9; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th {{ background-color: #f2f2f2; text-align: left; padding: 12px 8px; border: 1px solid #ddd; }}
            .footer {{ margin-top: 20px; text-align: center; font-size: 12px; color: #777; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h2>⚠️ Low Stock Alert</h2>
            </div>
            <div class="content">
                <p>The following items in your inventory are running low on stock and may need to be restocked soon:</p>
                
                <table>
                    <thead>
                        <tr>
                            <th>Item Name</th>
                            <th>SKU</th>
                            <th>Quantity Left</th>
                            <th>Category</th>
                        </tr>
                    </thead>
                    <tbody>
                        {item_rows}
                    </tbody>
                </table>
                
                <p>Please take action to restock these items at your earliest convenience.</p>
            </div>
            <div class="footer">
                <p>This is an automated notification from your Inventory Management System.</p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return send_email(to_email, from_email, subject, html_content=html_content)