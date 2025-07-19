# Firebase Models - Data structure definitions for Firebase collections
"""
Firebase Collections Structure:

1. users: User account information
2. items: Inventory/product items  
3. sales: Sales transactions
4. customers: Customer information
5. categories: Product categories
6. financial_transactions: Financial records
"""

from datetime import datetime
from typing import Dict, List, Optional, Any
import logging

logger = logging.getLogger(__name__)

class FirebaseModel:
    """Base class for Firebase document models"""
    
    @staticmethod
    def validate_required_fields(data: Dict, required_fields: List[str]) -> bool:
        """Validate that all required fields are present"""
        return all(field in data and data[field] is not None for field in required_fields)
    
    @staticmethod
    def sanitize_data(data: Dict) -> Dict:
        """Remove None values and ensure proper data types"""
        cleaned = {}
        for key, value in data.items():
            if value is not None:
                cleaned[key] = value
        return cleaned

class UserModel(FirebaseModel):
    """User model for Firebase"""
    
    REQUIRED_FIELDS = ['email', 'first_name', 'last_name']
    OPTIONAL_FIELDS = ['username', 'phone', 'is_admin', 'is_active', 'last_login', 'created_at']
    
    @classmethod
    def create_user_data(cls, email: str, first_name: str, last_name: str, **kwargs) -> Dict:
        """Create user data dictionary for Firebase"""
        user_data = {
            'email': email,
            'first_name': first_name,
            'last_name': last_name,
            'username': kwargs.get('username', email.split('@')[0]),
            'phone': kwargs.get('phone', ''),
            'is_admin': kwargs.get('is_admin', False),
            'is_active': kwargs.get('is_active', True),
            'created_at': kwargs.get('created_at', datetime.utcnow().isoformat()),
            'last_login': None
        }
        return cls.sanitize_data(user_data)

class ItemModel(FirebaseModel):
    """Inventory item model for Firebase"""
    
    REQUIRED_FIELDS = ['name', 'user_id']
    OPTIONAL_FIELDS = ['description', 'category', 'stock_quantity', 'minimum_stock', 
                      'buying_price', 'retail_price', 'wholesale_price', 'sku', 
                      'barcode', 'is_active', 'created_at', 'updated_at']
    
    @classmethod
    def create_item_data(cls, name: str, user_id: str, **kwargs) -> Dict:
        """Create item data dictionary for Firebase"""
        item_data = {
            'name': name,
            'user_id': user_id,
            'description': kwargs.get('description', ''),
            'category': kwargs.get('category', 'General'),
            'stock_quantity': int(kwargs.get('stock_quantity', 0)),
            'minimum_stock': int(kwargs.get('minimum_stock', 0)),
            'buying_price': float(kwargs.get('buying_price', 0.0)),
            'retail_price': float(kwargs.get('retail_price', 0.0)),
            'wholesale_price': float(kwargs.get('wholesale_price', 0.0)),
            'sku': kwargs.get('sku', ''),
            'barcode': kwargs.get('barcode', ''),
            'is_active': kwargs.get('is_active', True),
            'created_at': kwargs.get('created_at', datetime.utcnow().isoformat()),
            'updated_at': datetime.utcnow().isoformat()
        }
        return cls.sanitize_data(item_data)

class SaleModel(FirebaseModel):
    """Sales transaction model for Firebase"""
    
    REQUIRED_FIELDS = ['user_id', 'total_amount', 'sale_items']
    OPTIONAL_FIELDS = ['sale_number', 'customer_id', 'customer_name', 'payment_type',
                      'payment_status', 'is_installment', 'down_payment', 'installment_months',
                      'monthly_payment', 'notes', 'created_at']
    
    @classmethod
    def create_sale_data(cls, user_id: str, total_amount: float, sale_items: List[Dict], **kwargs) -> Dict:
        """Create sale data dictionary for Firebase"""
        sale_data = {
            'user_id': user_id,
            'total_amount': float(total_amount),
            'sale_items': sale_items,
            'sale_number': kwargs.get('sale_number', ''),
            'customer_id': kwargs.get('customer_id'),
            'customer_name': kwargs.get('customer_name', 'Walk-in Customer'),
            'payment_type': kwargs.get('payment_type', 'cash'),
            'payment_status': kwargs.get('payment_status', 'completed'),
            'is_installment': kwargs.get('is_installment', False),
            'down_payment': float(kwargs.get('down_payment', 0.0)),
            'installment_months': int(kwargs.get('installment_months', 0)),
            'monthly_payment': float(kwargs.get('monthly_payment', 0.0)),
            'notes': kwargs.get('notes', ''),
            'created_at': kwargs.get('created_at', datetime.utcnow().isoformat())
        }
        return cls.sanitize_data(sale_data)

class CustomerModel(FirebaseModel):
    """Customer model for Firebase"""
    
    REQUIRED_FIELDS = ['name', 'user_id']
    OPTIONAL_FIELDS = ['email', 'phone', 'address', 'city', 'state', 'postal_code',
                      'notes', 'total_purchases', 'loyalty_points', 'is_active', 'created_at']
    
    @classmethod
    def create_customer_data(cls, name: str, user_id: str, **kwargs) -> Dict:
        """Create customer data dictionary for Firebase"""
        customer_data = {
            'name': name,
            'user_id': user_id,
            'email': kwargs.get('email', ''),
            'phone': kwargs.get('phone', ''),
            'address': kwargs.get('address', ''),
            'city': kwargs.get('city', ''),
            'state': kwargs.get('state', ''),
            'postal_code': kwargs.get('postal_code', ''),
            'notes': kwargs.get('notes', ''),
            'total_purchases': float(kwargs.get('total_purchases', 0.0)),
            'loyalty_points': int(kwargs.get('loyalty_points', 0)),
            'is_active': kwargs.get('is_active', True),
            'created_at': kwargs.get('created_at', datetime.utcnow().isoformat())
        }
        return cls.sanitize_data(customer_data)

class CategoryModel(FirebaseModel):
    """Product category model for Firebase"""
    
    REQUIRED_FIELDS = ['name', 'user_id']
    OPTIONAL_FIELDS = ['description', 'parent_id', 'sort_order', 'is_active', 'created_at']
    
    @classmethod
    def create_category_data(cls, name: str, user_id: str, **kwargs) -> Dict:
        """Create category data dictionary for Firebase"""
        category_data = {
            'name': name,
            'user_id': user_id,
            'description': kwargs.get('description', ''),
            'parent_id': kwargs.get('parent_id'),
            'sort_order': int(kwargs.get('sort_order', 0)),
            'is_active': kwargs.get('is_active', True),
            'created_at': kwargs.get('created_at', datetime.utcnow().isoformat())
        }
        return cls.sanitize_data(category_data)