from firebase_service import firebase_service
from firebase_models import FirebaseUser, FirebaseItem, FirebaseSale, FirebaseCustomer, FirebaseCategory
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class FirebaseAdapter:
    """Adapter to make Firebase operations compatible with existing API structure"""

    def __init__(self):
        self.service = firebase_service

    # User operations
    def authenticate_user(self, email, password):
        """Authenticate user with Firebase Auth"""
        try:
            from firebase_admin import auth
            # Get user by email
            user = auth.get_user_by_email(email)
            if user:
                # Get user document from Firestore
                user_doc = self.service.db.collection('users').document(user.uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    user_data['id'] = user.uid
                    return user_data
            return None
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return None

    def create_user(self, user_data):
        """Create user using Firebase service"""
        return self.service.create_user(user_data)

    def get_user_by_id(self, user_id):
        """Get user by ID from Firebase"""
        try:
            # Get user document from Firestore
            user_doc = self.service.db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_data['id'] = user_id
                return user_data
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None

    def get_user_by_email(self, email):
        """Get user by email from Firebase"""
        try:
            # First, get user from Firebase Auth
            from firebase_admin import auth
            try:
                auth_user = auth.get_user_by_email(email)

                # Then get user document from Firestore
                user_doc = self.service.db.collection('users').document(auth_user.uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    user_data['id'] = auth_user.uid
                    return user_data
                else:
                    # If user exists in Auth but not in Firestore, create the document
                    user_data = {
                        'id': auth_user.uid,
                        'email': auth_user.email,
                        'username': auth_user.display_name or '',
                        'first_name': '',
                        'last_name': '',
                        'phone': '',
                        'shop_name': '',
                        'is_active': True,
                        'is_admin': False,
                        'created_at': auth_user.user_metadata.creation_timestamp,
                        'updated_at': auth_user.user_metadata.last_sign_in_timestamp
                    }
                    self.service.db.collection('users').document(auth_user.uid).set(user_data)
                    return user_data

            except auth.UserNotFoundError:
                return None

        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None

    def get_all_users(self):
        """Get all users from Firestore for analysis"""
        try:
            users_ref = self.service.db.collection('users')
            docs = users_ref.stream()

            users = []
            for doc in docs:
                user_data = doc.to_dict()
                user_data['id'] = doc.id
                users.append(user_data)

            return users
        except Exception as e:
            logger.error(f"Error getting all users: {str(e)}")
            return []

    def get_user_stats(self):
        """Get user statistics from Firestore"""
        try:
            users_ref = self.service.db.collection('users')
            docs = users_ref.stream()

            stats = {
                'total_users': 0,
                'active_users': 0,
                'admin_users': 0,
                'verified_users': 0,
                'users_by_creation_date': {},
                'users_by_shop_name': {}
            }

            for doc in docs:
                user_data = doc.to_dict()
                stats['total_users'] += 1

                if user_data.get('is_active', True):
                    stats['active_users'] += 1

                if user_data.get('is_admin', False):
                    stats['admin_users'] += 1

                if user_data.get('email_verified', False):
                    stats['verified_users'] += 1

                # Group by creation date
                created_at = user_data.get('created_at', '')
                if created_at:
                    date_key = created_at.split('T')[0] if 'T' in created_at else created_at
                    stats['users_by_creation_date'][date_key] = stats['users_by_creation_date'].get(date_key, 0) + 1

                # Group by shop name
                shop_name = user_data.get('shop_name', 'No Shop')
                if shop_name:
                    stats['users_by_shop_name'][shop_name] = stats['users_by_shop_name'].get(shop_name, 0) + 1

            return stats
        except Exception as e:
            logger.error(f"Error getting user stats: {str(e)}")
            return None

    # Item operations
    def create_item(self, item_data, user_id):
        """Create item using Firebase service"""
        return self.service.create_item(item_data, user_id)

    def get_items_by_user(self, user_id, **kwargs):
        """Get items with filtering support"""
        try:
            query = (self.service.db.collection('items')
                    .where(filter=('user_id', '==', user_id))
                    .where(filter=('is_active', '==', True)))

            # Apply filters
            category = kwargs.get('category')
            if category:
                query = query.where('category', '==', category)

            # Get documents
            docs = query.stream()
            items = []

            for doc in docs:
                item_data = doc.to_dict()
                item_data['id'] = doc.id
                # Ensure backward compatibility
                item_data['quantity'] = item_data.get('stock_quantity', 0)
                item_data['price'] = item_data.get('retail_price', 0)
                items.append(item_data)

            # Apply search filter if provided
            search_term = kwargs.get('search', '').lower()
            if search_term:
                items = [item for item in items if 
                        search_term in item.get('name', '').lower() or 
                        search_term in item.get('sku', '').lower()]

            return items
        except Exception as e:
            logger.error(f"Error getting items: {str(e)}")
            return []

    def update_item(self, item_id, updates, user_id):
        """Update item using Firebase service"""
        return self.service.update_item(item_id, updates, user_id)

    def delete_item(self, item_id, user_id):
        """Delete item using Firebase service"""
        return self.service.delete_item(item_id, user_id)

    # Sale operations
    def create_sale(self, sale_data, user_id):
        """Create sale using Firebase service"""
        return self.service.create_sale(sale_data, user_id)

    def get_sales_by_user(self, user_id, limit=None):
        """Get sales using Firebase service"""
        sales = self.service.get_sales_by_user(user_id, limit)
        # Convert to dict format for API compatibility
        return [sale.to_dict() if hasattr(sale, 'to_dict') else sale.__dict__ for sale in sales]

    # Customer operations
    def create_customer(self, customer_data, user_id):
        """Create customer using Firebase service"""
        return self.service.create_customer(customer_data, user_id)

    def get_customers_by_user(self, user_id):
        """Get customers using Firebase service"""
        customers = self.service.get_customers_by_user(user_id)
        return [customer.to_dict() if hasattr(customer, 'to_dict') else customer.__dict__ for customer in customers]

    # Category operations
    def create_category(self, category_data, user_id):
        """Create category using Firebase service"""
        return self.service.create_category(category_data, user_id)

    def get_categories_by_user(self, user_id):
        """Get categories using Firebase service"""
        categories = self.service.get_categories_by_user(user_id)
        return [category.to_dict() if hasattr(category, 'to_dict') else category.__dict__ for category in categories]

# Global Firebase adapter instance
firebase_adapter = FirebaseAdapter()