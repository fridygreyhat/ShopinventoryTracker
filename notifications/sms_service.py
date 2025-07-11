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
        logger.error(f"Missing credentials - SID: {bool(TWILIO_ACCOUNT_SID)}, Token: {bool(TWILIO_AUTH_TOKEN)}, Phone: {bool(TWILIO_PHONE_NUMBER)}")
        return False
    
    # Format phone number if needed
    formatted_phone = format_phone_number(to_phone_number)
    if not formatted_phone:
        logger.error(f"Invalid phone number format: {to_phone_number}")
        return False
    
    try:
        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Send message
        message_instance = client.messages.create(
            body=message,
            from_=TWILIO_PHONE_NUMBER,
            to=formatted_phone
        )
        
        logger.info(f"SMS sent successfully. SID: {message_instance.sid}, To: {formatted_phone}")
        return True
    
    except Exception as e:
        logger.error(f"Failed to send SMS to {formatted_phone}: {str(e)}")
        return False

def format_phone_number(phone_number):
    """
    Format phone number to E.164 format
    
    Args:
        phone_number (str): Phone number in various formats
        
    Returns:
        str: Formatted phone number or None if invalid
    """
    if not phone_number:
        return None
    
    # Remove all non-digit characters
    digits_only = ''.join(filter(str.isdigit, phone_number))
    
    # Handle different formats
    if len(digits_only) == 10:  # US number without country code
        return f"+1{digits_only}"
    elif len(digits_only) == 11 and digits_only.startswith('1'):  # US number with country code
        return f"+{digits_only}"
    elif len(digits_only) >= 10:  # International number
        if not digits_only.startswith('1') and len(digits_only) >= 10:
            return f"+{digits_only}"
    
    return phone_number if phone_number.startswith('+') else None

def test_sms_configuration():
    """
    Test SMS configuration without sending actual message
    
    Returns:
        dict: Configuration test results
    """
    result = {
        'credentials_configured': False,
        'client_initialized': False,
        'account_verified': False,
        'errors': []
    }
    
    # Check credentials
    if all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER]):
        result['credentials_configured'] = True
    else:
        missing = []
        if not TWILIO_ACCOUNT_SID:
            missing.append('TWILIO_ACCOUNT_SID')
        if not TWILIO_AUTH_TOKEN:
            missing.append('TWILIO_AUTH_TOKEN')
        if not TWILIO_PHONE_NUMBER:
            missing.append('TWILIO_PHONE_NUMBER')
        result['errors'].append(f"Missing environment variables: {', '.join(missing)}")
        return result
    
    try:
        # Initialize client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        result['client_initialized'] = True
        
        # Verify account (this makes a small API call)
        account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        result['account_verified'] = True
        result['account_status'] = account.status
        result['account_name'] = account.friendly_name
        
    except Exception as e:
        result['errors'].append(f"Twilio API error: {str(e)}")
    
    return result

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