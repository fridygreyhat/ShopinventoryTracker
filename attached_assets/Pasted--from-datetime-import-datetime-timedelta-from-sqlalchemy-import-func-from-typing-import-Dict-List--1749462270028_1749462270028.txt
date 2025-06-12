
from datetime import datetime, timedelta
from sqlalchemy import func
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)

class CustomerManager:
    """Customer management system with profiles and loyalty tracking"""
    
    def __init__(self, db):
        self.db = db
    
    def create_customer_models(self):
        """Create customer-related database models"""
        from app import db
        
        class Customer(db.Model):
            """Customer profile model"""
            id = db.Column(db.Integer, primary_key=True)
            name = db.Column(db.String(100), nullable=False)
            email = db.Column(db.String(120), unique=True)
            phone = db.Column(db.String(20))
            address = db.Column(db.Text)
            date_of_birth = db.Column(db.Date)
            customer_type = db.Column(db.String(20), default='retail')  # 'retail', 'wholesale', 'vip'
            
            # Loyalty program
            loyalty_points = db.Column(db.Integer, default=0)
            loyalty_tier = db.Column(db.String(20), default='bronze')  # 'bronze', 'silver', 'gold', 'platinum'
            
            # Credit management
            credit_limit = db.Column(db.Float, default=0.0)
            current_credit = db.Column(db.Float, default=0.0)
            
            # Preferences
            preferred_payment_method = db.Column(db.String(50))
            marketing_consent = db.Column(db.Boolean, default=True)
            
            # Timestamps
            created_at = db.Column(db.DateTime, default=datetime.utcnow)
            updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
            last_purchase_date = db.Column(db.DateTime)
            
            # Relationships
            purchases = db.relationship('Sale', backref='customer_profile', lazy=True, foreign_keys='Sale.customer_id')
            
            def __repr__(self):
                return f'<Customer {self.name}>'
            
            def to_dict(self):
                return {
                    'id': self.id,
                    'name': self.name,
                    'email': self.email,
                    'phone': self.phone,
                    'address': self.address,
                    'date_of_birth': self.date_of_birth.isoformat() if self.date_of_birth else None,
                    'customer_type': self.customer_type,
                    'loyalty_points': self.loyalty_points,
                    'loyalty_tier': self.loyalty_tier,
                    'credit_limit': self.credit_limit,
                    'current_credit': self.current_credit,
                    'preferred_payment_method': self.preferred_payment_method,
                    'marketing_consent': self.marketing_consent,
                    'created_at': self.created_at.isoformat() if self.created_at else None,
                    'updated_at': self.updated_at.isoformat() if self.updated_at else None,
                    'last_purchase_date': self.last_purchase_date.isoformat() if self.last_purchase_date else None
                }
        
        class CustomerPurchaseHistory(db.Model):
            """Detailed customer purchase history"""
            id = db.Column(db.Integer, primary_key=True)
            customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
            sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=False)
            purchase_amount = db.Column(db.Float, nullable=False)
            loyalty_points_earned = db.Column(db.Integer, default=0)
            loyalty_points_used = db.Column(db.Integer, default=0)
            created_at = db.Column(db.DateTime, default=datetime.utcnow)
            
            # Relationships
            customer = db.relationship('Customer', backref='purchase_history')
            sale = db.relationship('Sale', backref='customer_purchase')
        
        class LoyaltyTransaction(db.Model):
            """Loyalty points transactions"""
            id = db.Column(db.Integer, primary_key=True)
            customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
            transaction_type = db.Column(db.String(20), nullable=False)  # 'earned', 'redeemed', 'expired'
            points = db.Column(db.Integer, nullable=False)
            description = db.Column(db.String(255))
            sale_id = db.Column(db.Integer, db.ForeignKey('sale.id'), nullable=True)
            created_at = db.Column(db.DateTime, default=datetime.utcnow)
            
            # Relationships
            customer = db.relationship('Customer', backref='loyalty_transactions')
        
        return Customer, CustomerPurchaseHistory, LoyaltyTransaction

def calculate_customer_metrics(db, customer_id: int) -> Dict:
    """Calculate comprehensive customer metrics"""
    try:
        from models import Sale, SaleItem
        
        # Get customer purchase data
        customer_sales = Sale.query.filter_by(customer_id=customer_id).all()
        
        if not customer_sales:
            return {
                'total_purchases': 0,
                'total_spent': 0,
                'average_order_value': 0,
                'purchase_frequency': 0,
                'favorite_products': [],
                'last_purchase_date': None,
                'customer_lifetime_value': 0
            }
        
        # Calculate basic metrics
        total_purchases = len(customer_sales)
        total_spent = sum(sale.total for sale in customer_sales)
        average_order_value = total_spent / total_purchases if total_purchases > 0 else 0
        
        # Calculate purchase frequency (purchases per month)
        first_purchase = min(sale.created_at for sale in customer_sales)
        months_active = max(1, (datetime.utcnow() - first_purchase).days / 30)
        purchase_frequency = total_purchases / months_active
        
        # Get favorite products
        product_purchases = db.session.query(
            SaleItem.product_name,
            func.sum(SaleItem.quantity).label('total_quantity'),
            func.count(SaleItem.id).label('purchase_count')
        ).join(Sale).filter(
            Sale.customer_id == customer_id
        ).group_by(SaleItem.product_name).order_by(
            func.sum(SaleItem.quantity).desc()
        ).limit(5).all()
        
        favorite_products = [
            {
                'name': product.product_name,
                'total_quantity': product.total_quantity,
                'purchase_count': product.purchase_count
            }
            for product in product_purchases
        ]
        
        # Last purchase date
        last_purchase_date = max(sale.created_at for sale in customer_sales)
        
        # Simple CLV calculation (total spent * purchase frequency * estimated months remaining)
        estimated_remaining_months = 12  # Assume 1 year retention
        customer_lifetime_value = total_spent + (average_order_value * purchase_frequency * estimated_remaining_months)
        
        return {
            'total_purchases': total_purchases,
            'total_spent': round(total_spent, 2),
            'average_order_value': round(average_order_value, 2),
            'purchase_frequency': round(purchase_frequency, 2),
            'favorite_products': favorite_products,
            'last_purchase_date': last_purchase_date.isoformat() if last_purchase_date else None,
            'customer_lifetime_value': round(customer_lifetime_value, 2),
            'months_active': round(months_active, 1)
        }
        
    except Exception as e:
        logger.error(f"Error calculating customer metrics for customer {customer_id}: {str(e)}")
        return {'error': str(e)}

def calculate_loyalty_points(purchase_amount: float, customer_tier: str = 'bronze') -> int:
    """Calculate loyalty points based on purchase amount and customer tier"""
    base_rate = 1  # 1 point per currency unit
    
    tier_multipliers = {
        'bronze': 1.0,
        'silver': 1.2,
        'gold': 1.5,
        'platinum': 2.0
    }
    
    multiplier = tier_multipliers.get(customer_tier, 1.0)
    points = int(purchase_amount * base_rate * multiplier)
    
    return points

def update_loyalty_tier(customer, total_spent: float):
    """Update customer loyalty tier based on total spending"""
    tier_thresholds = {
        'bronze': 0,
        'silver': 1000,
        'gold': 5000,
        'platinum': 10000
    }
    
    new_tier = 'bronze'
    for tier, threshold in tier_thresholds.items():
        if total_spent >= threshold:
            new_tier = tier
    
    customer.loyalty_tier = new_tier
    return new_tier
