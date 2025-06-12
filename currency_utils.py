"""
Currency utilities for Tanzanian Shilling (TSh) formatting
"""

from decimal import Decimal
import locale

def format_currency(amount, show_symbol=True, decimal_places=2):
    """
    Format amount as Tanzanian Shilling currency
    
    Args:
        amount: The amount to format (can be int, float, Decimal, or string)
        show_symbol: Whether to show the TSh symbol
        decimal_places: Number of decimal places to show
    
    Returns:
        Formatted currency string
    """
    if amount is None:
        amount = 0
    
    try:
        # Convert to Decimal for precise calculations
        if isinstance(amount, str):
            amount = Decimal(amount)
        elif isinstance(amount, (int, float)):
            amount = Decimal(str(amount))
        elif not isinstance(amount, Decimal):
            amount = Decimal(str(amount))
    except (ValueError, TypeError):
        amount = Decimal('0')
    
    # Format with commas and specified decimal places
    formatted = f"{amount:,.{decimal_places}f}"
    
    if show_symbol:
        return f"Tsh {formatted}"
    return formatted

def parse_currency(currency_string):
    """
    Parse currency string and return Decimal amount
    
    Args:
        currency_string: String like "TSh 1,500.00" or "1500"
    
    Returns:
        Decimal amount
    """
    if not currency_string:
        return Decimal('0')
    
    # Remove Tsh symbol and whitespace
    cleaned = str(currency_string).replace('Tsh', '').replace(',', '').strip()
    
    try:
        return Decimal(cleaned)
    except (ValueError, TypeError):
        return Decimal('0')

def format_currency_input(amount):
    """
    Format currency for input fields (without symbol)
    
    Args:
        amount: The amount to format
    
    Returns:
        Formatted string for input field
    """
    return format_currency(amount, show_symbol=False)

def calculate_percentage(amount, percentage):
    """
    Calculate percentage of amount
    
    Args:
        amount: Base amount
        percentage: Percentage to calculate
    
    Returns:
        Decimal result
    """
    if not amount or not percentage:
        return Decimal('0')
    
    amount = Decimal(str(amount)) if not isinstance(amount, Decimal) else amount
    percentage = Decimal(str(percentage)) if not isinstance(percentage, Decimal) else percentage
    
    return (amount * percentage) / Decimal('100')

def format_profit_margin(cost_price, selling_price):
    """
    Calculate and format profit margin percentage
    
    Args:
        cost_price: Cost price
        selling_price: Selling price
    
    Returns:
        Formatted profit margin string
    """
    try:
        cost = Decimal(str(cost_price)) if cost_price else Decimal('0')
        selling = Decimal(str(selling_price)) if selling_price else Decimal('0')
        
        if cost == 0:
            return "0%"
        
        profit = selling - cost
        margin = (profit / cost) * Decimal('100')
        
        return f"{margin:.1f}%"
    except (ValueError, TypeError):
        return "0%"

# Currency constants
CURRENCY_SYMBOL = "Tsh"
CURRENCY_NAME = "Tanzanian Shilling"
CURRENCY_CODE = "TZS"