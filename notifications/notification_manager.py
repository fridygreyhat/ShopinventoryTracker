import logging
from notifications.sms_service import send_low_stock_sms
from notifications.email_service import send_low_stock_email

# Set up logging
logger = logging.getLogger(__name__)

def check_low_stock_and_notify(db, Item, Setting):
    """
    Check for low stock items and send notifications if needed
    
    Args:
        db: SQLAlchemy database instance
        Item: Item model class
        Setting: Setting model class
        
    Returns:
        dict: Notification results
    """
    result = {
        "success": False,
        "sms_sent": False,
        "email_sent": False,
        "low_stock_count": 0,
        "errors": []
    }
    
    try:
        # Get settings for notifications
        low_stock_threshold = get_setting_value(Setting, "low_stock_threshold", 10)
        notification_email = get_setting_value(Setting, "notification_email", "")
        notification_phone = get_setting_value(Setting, "notification_phone", "")
        sender_email = get_setting_value(Setting, "sender_email", "inventory@yourbusiness.com")
        
        # Check if notifications are enabled
        sms_notifications_enabled = get_setting_value(Setting, "sms_notifications_enabled", False)
        email_notifications_enabled = get_setting_value(Setting, "email_notifications_enabled", False)
        
        # If notifications are disabled, return early
        if not sms_notifications_enabled and not email_notifications_enabled:
            result["errors"].append("Both SMS and email notifications are disabled in settings")
            return result
        
        # Get low stock items
        low_stock_items = get_low_stock_items(Item, low_stock_threshold)
        
        # If no low stock items, return early
        if not low_stock_items:
            result["success"] = True
            return result
        
        # Set low stock count
        result["low_stock_count"] = len(low_stock_items)
        
        # Convert items to dict format for notifications
        items_for_notification = [item.to_dict() for item in low_stock_items]
        
        # Send SMS notification if enabled
        if sms_notifications_enabled and notification_phone:
            sms_result = send_low_stock_sms(notification_phone, items_for_notification)
            result["sms_sent"] = sms_result
            if not sms_result:
                result["errors"].append("Failed to send SMS notification")
        elif sms_notifications_enabled and not notification_phone:
            result["errors"].append("SMS notifications are enabled but no phone number is configured")
        
        # Send email notification if enabled
        if email_notifications_enabled and notification_email and sender_email:
            email_result = send_low_stock_email(
                notification_email, 
                sender_email, 
                items_for_notification
            )
            result["email_sent"] = email_result
            if not email_result:
                result["errors"].append("Failed to send email notification")
        elif email_notifications_enabled:
            if not notification_email:
                result["errors"].append("Email notifications are enabled but no recipient email is configured")
            if not sender_email:
                result["errors"].append("Email notifications are enabled but no sender email is configured")
        
        # Mark overall success
        result["success"] = result["sms_sent"] or result["email_sent"] or result["low_stock_count"] == 0
        
        return result
    
    except Exception as e:
        error_message = f"Error checking low stock and sending notifications: {str(e)}"
        logger.error(error_message)
        result["errors"].append(error_message)
        return result

def get_low_stock_items(Item, threshold=10):
    """
    Get items with stock below the threshold
    
    Args:
        Item: Item model class
        threshold (int): Low stock threshold
        
    Returns:
        list: List of Item objects with low stock
    """
    try:
        low_stock_items = Item.query.filter(Item.quantity <= threshold).all()
        return low_stock_items
    except Exception as e:
        logger.error(f"Error fetching low stock items: {str(e)}")
        return []

def get_setting_value(Setting, key, default=None):
    """
    Get setting value from database
    
    Args:
        Setting: Setting model class
        key (str): Setting key
        default: Default value if setting not found
        
    Returns:
        any: Setting value or default
    """
    try:
        setting = Setting.query.filter_by(key=key).first()
        if setting:
            # Handle boolean settings stored as strings
            if setting.value.lower() in ('true', 'false'):
                return setting.value.lower() == 'true'
            # Try to convert to integer if possible
            try:
                return int(setting.value)
            except (ValueError, TypeError):
                pass
            # Return as is
            return setting.value
        return default
    except Exception as e:
        logger.error(f"Error fetching setting {key}: {str(e)}")
        return default