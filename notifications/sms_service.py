import os
import logging
from twilio.rest import Client
import requests
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

# Get Twilio credentials from environment variables
TWILIO_ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

def send_sms(phone_number, message):
    """
    Send SMS using Africa's Talking API

    Args:
        phone_number (str): Phone number to send SMS to
        message (str): Message content

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # You would replace this with actual Africa's Talking API implementation
        # For now, this is a placeholder

        logger.info(f"SMS sent to {phone_number}: {message}")
        return True

    except Exception as e:
        logger.error(f"Failed to send SMS to {phone_number}: {str(e)}")
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

def send_whatsapp_message(phone_number, message, template_name=None):
    """
    Send WhatsApp message using WhatsApp Business API

    Args:
        phone_number (str): Phone number to send message to (with country code)
        message (str): Message content
        template_name (str): Optional template name for business messages

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # WhatsApp Business API endpoint
        whatsapp_api_url = os.environ.get('WHATSAPP_API_URL')
        whatsapp_token = os.environ.get('WHATSAPP_ACCESS_TOKEN')

        if not whatsapp_api_url or not whatsapp_token:
            logger.warning("WhatsApp API credentials not configured")
            return False

        headers = {
            'Authorization': f'Bearer {whatsapp_token}',
            'Content-Type': 'application/json'
        }

        # Format phone number (ensure it starts with country code)
        if not phone_number.startswith('+'):
            phone_number = '+255' + phone_number.lstrip('0')  # Tanzania country code

        # Prepare message payload
        if template_name:
            # Use template message for business notifications
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "template",
                "template": {
                    "name": template_name,
                    "language": {
                        "code": "en"
                    },
                    "components": [
                        {
                            "type": "body",
                            "parameters": [
                                {
                                    "type": "text",
                                    "text": message
                                }
                            ]
                        }
                    ]
                }
            }
        else:
            # Use text message
            payload = {
                "messaging_product": "whatsapp",
                "to": phone_number,
                "type": "text",
                "text": {
                    "body": message
                }
            }

        response = requests.post(whatsapp_api_url, headers=headers, json=payload)

        if response.status_code == 200:
            logger.info(f"WhatsApp message sent to {phone_number}")
            return True
        else:
            logger.error(f"WhatsApp API error: {response.status_code} - {response.text}")
            return False

    except Exception as e:
        logger.error(f"Failed to send WhatsApp message to {phone_number}: {str(e)}")
        return False

def send_bulk_notifications(contacts, message, method='both'):
    """
    Send bulk notifications via SMS and/or WhatsApp

    Args:
        contacts (list): List of contact dictionaries with 'phone' and optionally 'name'
        message (str): Message content
        method (str): 'sms', 'whatsapp', or 'both'

    Returns:
        dict: Results summary
    """
    results = {
        'total_contacts': len(contacts),
        'sms_sent': 0,
        'whatsapp_sent': 0,
        'failed': 0,
        'errors': []
    }

    for contact in contacts:
        phone = contact.get('phone', '')
        name = contact.get('name', 'Customer')

        if not phone:
            results['failed'] += 1
            results['errors'].append(f"No phone number for {name}")
            continue

        # Personalize message if name is available
        personalized_message = message.replace('[NAME]', name)

        success = False

        if method in ['sms', 'both']:
            if send_sms(phone, personalized_message):
                results['sms_sent'] += 1
                success = True

        if method in ['whatsapp', 'both']:
            if send_whatsapp_message(phone, personalized_message):
                results['whatsapp_sent'] += 1
                success = True

        if not success:
            results['failed'] += 1
            results['errors'].append(f"Failed to send to {name} ({phone})")

    return results