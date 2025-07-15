
from datetime import datetime
import locale
from flask import session
import logging

logger = logging.getLogger(__name__)

class LocalizationService:
    def __init__(self):
        self.supported_languages = {
            'en': 'English',
            'sw': 'Kiswahili',
            'fr': 'Français',
            'ar': 'العربية'
        }
        self.default_language = 'en'
        self.default_currency = 'TZS'
        self.vat_rate = 0.18  # Tanzania VAT rate

    def get_user_language(self):
        """Get user's preferred language"""
        return session.get('user_language', self.default_language)

    def set_user_language(self, language):
        """Set user's preferred language"""
        if language in self.supported_languages:
            session['user_language'] = language
            return True
        return False

    def format_currency(self, amount, currency='TZS'):
        """Format currency amount according to local preferences"""
        try:
            if currency == 'TZS':
                return f"TSh {amount:,.2f}"
            elif currency == 'USD':
                return f"${amount:,.2f}"
            elif currency == 'EUR':
                return f"€{amount:,.2f}"
            else:
                return f"{currency} {amount:,.2f}"
        except Exception as e:
            logger.error(f"Error formatting currency: {str(e)}")
            return f"{currency} {amount}"

    def format_date(self, date_obj, format_type='short'):
        """Format date according to local preferences"""
        try:
            if format_type == 'short':
                return date_obj.strftime('%d/%m/%Y')
            elif format_type == 'long':
                return date_obj.strftime('%d %B %Y')
            elif format_type == 'datetime':
                return date_obj.strftime('%d/%m/%Y %H:%M')
            else:
                return date_obj.strftime('%d/%m/%Y')
        except Exception as e:
            logger.error(f"Error formatting date: {str(e)}")
            return str(date_obj)

    def calculate_vat(self, amount, include_vat=True):
        """Calculate VAT for Tanzania"""
        try:
            if include_vat:
                # Amount includes VAT, extract it
                vat_exclusive = amount / (1 + self.vat_rate)
                vat_amount = amount - vat_exclusive
            else:
                # Amount is VAT exclusive, add VAT
                vat_amount = amount * self.vat_rate
                vat_exclusive = amount
            
            vat_inclusive = vat_exclusive + vat_amount
            
            return {
                'success': True,
                'vat_exclusive': round(vat_exclusive, 2),
                'vat_amount': round(vat_amount, 2),
                'vat_inclusive': round(vat_inclusive, 2),
                'vat_rate': self.vat_rate * 100
            }
        except Exception as e:
            logger.error(f"Error calculating VAT: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_business_translation(self, key, language=None):
        """Get business term translations"""
        if not language:
            language = self.get_user_language()
        
        translations = {
            'en': {
                'inventory': 'Inventory',
                'sales': 'Sales',
                'customers': 'Customers',
                'reports': 'Reports',
                'settings': 'Settings',
                'total': 'Total',
                'quantity': 'Quantity',
                'price': 'Price',
                'cash': 'Cash',
                'credit': 'Credit'
            },
            'sw': {
                'inventory': 'Hifadhi',
                'sales': 'Mauzo',
                'customers': 'Wateja',
                'reports': 'Ripoti',
                'settings': 'Mipangilio',
                'total': 'Jumla',
                'quantity': 'Idadi',
                'price': 'Bei',
                'cash': 'Pesa Taslimu',
                'credit': 'Mkopo'
            }
        }
        
        return translations.get(language, {}).get(key, key)
