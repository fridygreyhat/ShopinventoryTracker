
from models import db, Customer, Sale
from datetime import datetime
from sqlalchemy import func
import logging

logger = logging.getLogger(__name__)

class CustomerService:
    def __init__(self, user_id):
        self.user_id = user_id

    def create_customer(self, customer_data):
        """Create a new customer"""
        try:
            # Check if customer already exists
            existing_customer = Customer.query.filter_by(
                phone=customer_data['phone'],
                user_id=self.user_id
            ).first()

            if existing_customer:
                return {
                    'success': False,
                    'error': 'Customer with this phone number already exists'
                }

            # Create new customer
            new_customer = Customer(
                name=customer_data['name'],
                phone=customer_data['phone'],
                email=customer_data.get('email', ''),
                address=customer_data.get('address', ''),
                user_id=self.user_id,
                created_at=datetime.utcnow()
            )

            db.session.add(new_customer)
            db.session.commit()

            return {
                'success': True,
                'customer_id': new_customer.id,
                'message': 'Customer created successfully'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating customer: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_customer_profile(self, customer_id):
        """Get detailed customer profile with purchase history"""
        try:
            customer = Customer.query.filter_by(
                id=customer_id,
                user_id=self.user_id
            ).first()

            if not customer:
                return {'success': False, 'error': 'Customer not found'}

            # Get purchase history
            sales = Sale.query.filter_by(
                customer_id=customer_id,
                user_id=self.user_id
            ).order_by(Sale.created_at.desc()).all()

            # Calculate customer metrics
            total_purchases = len(sales)
            total_spent = sum(sale.total_amount for sale in sales)
            last_purchase = sales[0].created_at if sales else None

            purchase_history = []
            for sale in sales:
                purchase_history.append({
                    'sale_number': sale.sale_number,
                    'date': sale.created_at.strftime('%Y-%m-%d %H:%M'),
                    'total_amount': float(sale.total_amount),
                    'payment_method': sale.payment_method
                })

            return {
                'success': True,
                'customer': {
                    'id': customer.id,
                    'name': customer.name,
                    'phone': customer.phone,
                    'email': customer.email,
                    'address': customer.address,
                    'created_at': customer.created_at.strftime('%Y-%m-%d'),
                    'metrics': {
                        'total_purchases': total_purchases,
                        'total_spent': float(total_spent),
                        'last_purchase': last_purchase.strftime('%Y-%m-%d %H:%M') if last_purchase else None
                    },
                    'purchase_history': purchase_history
                }
            }

        except Exception as e:
            logger.error(f"Error getting customer profile: {str(e)}")
            return {'success': False, 'error': str(e)}

    def update_customer(self, customer_id, customer_data):
        """Update customer information"""
        try:
            customer = Customer.query.filter_by(
                id=customer_id,
                user_id=self.user_id
            ).first()

            if not customer:
                return {'success': False, 'error': 'Customer not found'}

            # Update customer fields
            customer.name = customer_data.get('name', customer.name)
            customer.phone = customer_data.get('phone', customer.phone)
            customer.email = customer_data.get('email', customer.email)
            customer.address = customer_data.get('address', customer.address)

            db.session.commit()

            return {
                'success': True,
                'message': 'Customer updated successfully'
            }

        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating customer: {str(e)}")
            return {'success': False, 'error': str(e)}

    def get_customer_loyalty_metrics(self, customer_id):
        """Get customer loyalty metrics"""
        try:
            customer = Customer.query.filter_by(
                id=customer_id,
                user_id=self.user_id
            ).first()

            if not customer:
                return {'success': False, 'error': 'Customer not found'}

            # Calculate loyalty metrics
            thirty_days_ago = datetime.utcnow() - timedelta(days=30)
            
            recent_purchases = Sale.query.filter(
                Sale.customer_id == customer_id,
                Sale.user_id == self.user_id,
                Sale.created_at >= thirty_days_ago
            ).count()

            total_purchases = Sale.query.filter_by(
                customer_id=customer_id,
                user_id=self.user_id
            ).count()

            # Calculate loyalty score (0-100)
            loyalty_score = min(100, (recent_purchases * 10) + (total_purchases * 5))

            return {
                'success': True,
                'loyalty_metrics': {
                    'recent_purchases': recent_purchases,
                    'total_purchases': total_purchases,
                    'loyalty_score': loyalty_score,
                    'loyalty_tier': self._get_loyalty_tier(loyalty_score)
                }
            }

        except Exception as e:
            logger.error(f"Error getting loyalty metrics: {str(e)}")
            return {'success': False, 'error': str(e)}

    def _get_loyalty_tier(self, score):
        """Determine loyalty tier based on score"""
        if score >= 80:
            return 'Gold'
        elif score >= 50:
            return 'Silver'
        elif score >= 20:
            return 'Bronze'
        else:
            return 'New'

    def search_customers(self, query):
        """Search customers by name or phone"""
        try:
            customers = Customer.query.filter(
                Customer.user_id == self.user_id,
                db.or_(
                    Customer.name.ilike(f'%{query}%'),
                    Customer.phone.ilike(f'%{query}%')
                )
            ).limit(10).all()

            customer_list = []
            for customer in customers:
                customer_list.append({
                    'id': customer.id,
                    'name': customer.name,
                    'phone': customer.phone,
                    'email': customer.email
                })

            return {
                'success': True,
                'customers': customer_list
            }

        except Exception as e:
            logger.error(f"Error searching customers: {str(e)}")
            return {'success': False, 'error': str(e)}
