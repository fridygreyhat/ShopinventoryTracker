import os
import logging
from twilio.rest import Client

# Set up logging
logger = logging.getLogger(__name__)

# Get Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

def send_sms(to_phone_number, message):
    """
    Send SMS using Twilio
    
    Args:
        to_phone_number (str): Recipient's phone number in E.164 format (+1XXXXXXXXXX)
        message (str): Message content to send
        
    Returns:
        bool: True if successful, False otherwise
    """
    # Validate Twilio credentials
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        logger.error("Twilio credentials are not properly configured")
        return False
    
    try:
        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Send message
        message = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=to_phone_number
        )
        
        logger.info(f"SMS sent successfully. SID: {message.sid}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send SMS: {str(e)}")
        return False

def generate_otp():
    """Generate a 6-digit OTP code"""
    import random
    return ''.join([str(random.randint(0, 9)) for _ in range(6)])

def send_otp(phone_number, otp_code):
    """
    Send OTP via SMS
    
    Args:
        phone_number (str): Phone number in E.164 format (+XXXXXXXXX)
        otp_code (str): OTP code to send
        
    Returns:
        bool: True if successful, False otherwise
    """
    message = f"Your verification code is: {otp_code}. Valid for 10 minutes."
    return send_sms(phone_number, message)

def verify_phone_number(phone_number, code):
    """
    Verify phone number using OTP
    
    Args:
        phone_number (str): Phone number in E.164 format (+XXXXXXXXX)
        code (str): OTP code entered by user
        
    Returns:
        bool: True if verification successful, False otherwise
    """
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        verification_check = client.verify \
            .v2 \
            .services(os.environ.get('TWILIO_VERIFY_SERVICE_ID')) \
            .verification_checks \
            .create(to=phone_number, code=code)
            
        return verification_check.status == 'approved'
        
    except Exception as e:
        logger.error(f"Failed to verify phone number: {str(e)}")
        return False

def send_low_stock_sms(phone_number, low_stock_items):
    """
    Send low stock notification via SMS
    
    Args:
        phone_number (str): Recipient's phone number
        low_stock_items (list): List of low stock items
        
    Returns:
        bool: True if successful, False otherwise
    """
    if not low_stock_items:
        return False
    
    # Format message with low stock items
    items_text = "\n".join([f"• {item['name']} (only {item['quantity']} left)" for item in low_stock_items[:10]])
    
    # Add note if there are more items
    more_items = ""
    if len(low_stock_items) > 10:
        more_items = f"\n\nAnd {len(low_stock_items) - 10} more items..."
    
    message = (
        f"⚠️ LOW STOCK ALERT ⚠️\n\n"
        f"The following items are running low on stock:\n\n"
        f"{items_text}{more_items}\n\n"
        f"Please restock soon."
    )
    
    return send_sms(phone_number, message)