
import locale
from datetime import datetime
from flask import session
import json

class LocalizationService:
    def __init__(self):
        self.supported_languages = {
            'en': 'English',
            'sw': 'Kiswahili'
        }
        
        self.currency_formats = {
            'TZS': {
                'symbol': 'TSh',
                'decimal_places': 2,
                'thousands_separator': ',',
                'decimal_separator': '.'
            },
            'USD': {
                'symbol': '$',
                'decimal_places': 2,
                'thousands_separator': ',',
                'decimal_separator': '.'
            }
        }
        
        self.date_formats = {
            'en': '%Y-%m-%d',
            'sw': '%d/%m/%Y'
        }
        
        self.tax_rates = {
            'VAT': 18.0,  # Tanzania VAT rate
            'WITHHOLDING_TAX': 5.0,
            'SERVICE_TAX': 10.0
        }

    def get_user_language(self):
        """Get current user's language preference"""
        return session.get('user_language', 'en')
    
    def set_user_language(self, language):
        """Set user's language preference"""
        if language in self.supported_languages:
            session['user_language'] = language
            return True
        return False
    
    def format_currency(self, amount, currency='TZS'):
        """Format currency according to local preferences"""
        if currency not in self.currency_formats:
            currency = 'TZS'
        
        format_info = self.currency_formats[currency]
        
        # Format number with thousands separator
        formatted_amount = f"{amount:,.{format_info['decimal_places']}f}"
        
        # Replace separators if needed
        if format_info['thousands_separator'] != ',':
            formatted_amount = formatted_amount.replace(',', format_info['thousands_separator'])
        
        return f"{format_info['symbol']} {formatted_amount}"
    
    def format_date(self, date_obj, language=None):
        """Format date according to cultural preferences"""
        if language is None:
            language = self.get_user_language()
        
        date_format = self.date_formats.get(language, self.date_formats['en'])
        return date_obj.strftime(date_format)
    
    def calculate_vat(self, amount, include_vat=True):
        """Calculate VAT for Tanzania"""
        vat_rate = self.tax_rates['VAT'] / 100
        
        if include_vat:
            # Amount includes VAT, extract it
            vat_amount = amount * vat_rate / (1 + vat_rate)
            base_amount = amount - vat_amount
        else:
            # Amount excludes VAT, add it
            base_amount = amount
            vat_amount = amount * vat_rate
        
        return {
            'base_amount': round(base_amount, 2),
            'vat_amount': round(vat_amount, 2),
            'total_amount': round(base_amount + vat_amount, 2),
            'vat_rate': self.tax_rates['VAT']
        }
    
    def get_business_hours(self):
        """Get local business hours for Tanzania"""
        return {
            'monday': {'open': '08:00', 'close': '17:00'},
            'tuesday': {'open': '08:00', 'close': '17:00'},
            'wednesday': {'open': '08:00', 'close': '17:00'},
            'thursday': {'open': '08:00', 'close': '17:00'},
            'friday': {'open': '08:00', 'close': '17:00'},
            'saturday': {'open': '08:00', 'close': '14:00'},
            'sunday': {'closed': True}
        }
