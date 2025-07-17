
from firebase_config import get_firestore_db, get_firebase_auth
from firebase_models import *
from google.cloud.firestore import Query
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class FirebaseService:
    """Service layer for Firebase operations"""
    
    def __init__(self):
        self.db = get_firestore_db()
        self.auth = get_firebase_auth()

    # User operations
    def create_user(self, user_data):
        """Create a new user in Firebase"""
        try:
            # Create user in Firebase Auth
            auth_user = self.auth.create_user(
                email=user_data['email'],
                password=user_data.get('password', 'temp_password'),
                display_name=f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
            )

            # Create user document in Firestore
            user = FirebaseUser()
            user.id = auth_user.uid
            user.username = user_data.get('username', '')
            user.email = user_data['email']
            user.first_name = user_data.get('first_name', '')
            user.last_name = user_data.get('last_name', '')
            user.phone = user_data.get('phone', '')
            user.shop_name = user_data.get('shop_name', '')
            user.product_categories = user_data.get('product_categories', '')
            user.is_admin = user_data.get('is_admin', False)
            user.is_active = user_data.get('is_active', True)
            user.email_verified = user_data.get('email_verified', False)
            user.created_at = user_data.get('created_at', datetime.utcnow().isoformat())

            # Save to Firestore
            self.db.collection('users').document(auth_user.uid).set(user.to_dict())
            
            logger.info(f"User created successfully: {user.email}")
            return user

        except Exception as e:
            logger.error(f"Error creating user: {str(e)}")
            raise

    def get_user_by_email(self, email):
        """Get user by email"""
        try:
            # Get user from Firebase Auth
            auth_user = self.auth.get_user_by_email(email)
            
            # Get user document from Firestore
            user_doc = self.db.collection('users').document(auth_user.uid).get()
            
            if user_doc.exists:
                user = FirebaseUser(user_doc.to_dict(), auth_user.uid)
                return user
            
            return None

        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None

    def update_user_last_login(self, user_id):
        """Update user's last login timestamp"""
        try:
            self.db.collection('users').document(user_id).update({
                'last_login': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            })
            logger.info(f"Updated last login for user: {user_id}")
        except Exception as e:
            logger.error(f"Error updating last login for user {user_id}: {str(e)}")

    # Item operations
    def create_item(self, item_data, user_id):
        """Create a new inventory item"""
        try:
            item = FirebaseItem()
            
            # Set item properties
            for key, value in item_data.items():
                if hasattr(item, key):
                    setattr(item, key, value)
            
            item.user_id = user_id
            item.id = str(uuid.uuid4())
            
            # Generate SKU if not provided
            if not item.sku:
                item.sku = FirebaseItem.generate_sku(item.name, item.category)

            # Save to Firestore
            self.db.collection('items').document(item.id).set(item.to_dict())
            
            logger.info(f"Item created: {item.name}")
            return item

        except Exception as e:
            logger.error(f"Error creating item: {str(e)}")
            raise

    def get_items_by_user(self, user_id, limit=None):
        """Get all items for a user"""
        try:
            # Use filter keyword argument to avoid deprecation warning
            query = (self.db.collection('items')
                    .where(filter=('user_id', '==', user_id))
                    .where(filter=('is_active', '==', True)))
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            items = []
            
            for doc in docs:
                item_data = doc.to_dict()
                item_data['id'] = doc.id
                items.append(item_data)
            
            return items

        except Exception as e:
            logger.error(f"Error getting items: {str(e)}")
            return []

    def update_item(self, item_id, updates, user_id):
        """Update an item"""
        try:
            # Verify item belongs to user
            item_ref = self.db.collection('items').document(item_id)
            item_doc = item_ref.get()
            
            if not item_doc.exists:
                raise ValueError("Item not found")
            
            item_data = item_doc.to_dict()
            if item_data.get('user_id') != user_id:
                raise ValueError("Unauthorized access to item")
            
            # Add update timestamp
            updates['updated_at'] = datetime.utcnow()
            
            # Update the item
            item_ref.update(updates)
            
            logger.info(f"Item updated: {item_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating item: {str(e)}")
            raise

    def delete_item(self, item_id, user_id):
        """Delete an item (soft delete)"""
        try:
            return self.update_item(item_id, {'is_active': False}, user_id)
        except Exception as e:
            logger.error(f"Error deleting item: {str(e)}")
            raise

    # Sale operations
    def create_sale(self, sale_data, user_id):
        """Create a new sale"""
        try:
            sale = FirebaseSale()
            
            # Set sale properties
            for key, value in sale_data.items():
                if hasattr(sale, key) and key != 'items':
                    setattr(sale, key, value)
            
            sale.user_id = user_id
            sale.id = str(uuid.uuid4())
            
            # Generate numbers if not provided
            if not sale.sale_number:
                sale.sale_number = FirebaseSale.generate_sale_number()
            if not sale.invoice_number:
                sale.invoice_number = FirebaseSale.generate_invoice_number()

            # Handle sale items
            if 'items' in sale_data:
                sale.sale_items = sale_data['items']

            # Save to Firestore
            self.db.collection('sales').document(sale.id).set(sale.to_dict())
            
            logger.info(f"Sale created: {sale.sale_number}")
            return sale

        except Exception as e:
            logger.error(f"Error creating sale: {str(e)}")
            raise

    def get_sales_by_user(self, user_id, limit=None):
        """Get all sales for a user"""
        try:
            # Use filter keyword argument to avoid deprecation warning
            query = self.db.collection('sales').where(filter=('user_id', '==', user_id))
            
            if limit:
                query = query.limit(limit)
            
            docs = query.stream()
            sales = []
            
            for doc in docs:
                sale_data = doc.to_dict()
                sale_data['id'] = doc.id
                sales.append(sale_data)
            
            # Sort in Python instead of Firestore to avoid index requirement
            sales.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            
            return sales

        except Exception as e:
            logger.error(f"Error getting sales: {str(e)}")
            return []

    # Customer operations
    def create_customer(self, customer_data, user_id):
        """Create a new customer"""
        try:
            customer_id = str(uuid.uuid4())
            customer_data['user_id'] = user_id
            customer_data['id'] = customer_id
            customer_data['created_at'] = datetime.utcnow().isoformat()
            customer_data['updated_at'] = datetime.utcnow().isoformat()

            # Save to Firestore
            self.db.collection('customers').document(customer_id).set(customer_data)
            
            logger.info(f"Customer created: {customer_data.get('name')}")
            return customer_data

        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            raise

    def get_customers_by_user(self, user_id):
        """Get all customers for a user"""
        try:
            docs = self.db.collection('customers').where(filter=('user_id', '==', user_id)).stream()
            customers = []
            
            for doc in docs:
                customer_data = doc.to_dict()
                customer_data['id'] = doc.id
                customers.append(customer_data)
            
            return customers

        except Exception as e:
            logger.error(f"Error getting customers: {str(e)}")
            return []

    # Category operations
    def create_category(self, category_data, user_id):
        """Create a new category"""
        try:
            category = FirebaseCategory()
            
            # Set category properties
            for key, value in category_data.items():
                if hasattr(category, key):
                    setattr(category, key, value)
            
            category.user_id = user_id
            category.id = str(uuid.uuid4())

            # Save to Firestore
            self.db.collection('categories').document(category.id).set(category.to_dict())
            
            logger.info(f"Category created: {category.name}")
            return category

        except Exception as e:
            logger.error(f"Error creating category: {str(e)}")
            raise

    def get_categories_by_user(self, user_id):
        """Get all categories for a user"""
        try:
            docs = (self.db.collection('categories')
                   .where(filter=('user_id', '==', user_id))
                   .where(filter=('is_active', '==', True))
                   .stream())
            categories = []
            
            for doc in docs:
                category = FirebaseCategory(doc.to_dict(), doc.id)
                categories.append(category)
            
            return categories

        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return []

# Global Firebase service instance
firebase_service = FirebaseService()
