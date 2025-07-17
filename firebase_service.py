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

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            user_doc = self.db.collection('users').document(user_id).get()

            if user_doc.exists:
                user = FirebaseUser(user_doc.to_dict(), user_id)
                return user

            return None
        except Exception as e:
            logger.error(f"Error getting user by ID: {str(e)}")
            return None

    def update_user_last_login(self, user_id):
        """Update user's last login timestamp"""
        try:
            self.db.collection('users').document(user_id).update({
                'last_login': datetime.utcnow().isoformat()
            })
            logger.info(f"Updated last login for user {user_id}")
        except Exception as e:
            logger.error(f"Error updating last login: {str(e)}")

    # Item operations
    def create_item(self, item_data, user_id):
        """Create a new item"""
        try:
            item = FirebaseItem()

            # Set item properties
            for key, value in item_data.items():
                if hasattr(item, key):
                    setattr(item, key, value)

            item.user_id = user_id
            item.id = str(uuid.uuid4())

            # Save to Firestore
            self.db.collection('items').document(item.id).set(item.to_dict())

            logger.info(f"Item created: {item.name}")
            return item

        except Exception as e:
            logger.error(f"Error creating item: {str(e)}")
            raise

    def get_items_by_user(self, user_id):
        """Get all items for a user"""
        try:
            query = (self.db.collection('items')
                    .where('user_id', '==', user_id)
                    .where('is_active', '==', True))

            docs = query.stream()
            items = []

            for doc in docs:
                item = FirebaseItem(doc.to_dict(), doc.id)
                items.append(item)

            return items

        except Exception as e:
            logger.error(f"Error getting items: {str(e)}")
            return []

    def get_item_by_id(self, item_id, user_id):
        """Get a specific item by ID"""
        try:
            item_doc = self.db.collection('items').document(item_id).get()

            if item_doc.exists:
                item_data = item_doc.to_dict()
                if item_data.get('user_id') == user_id:
                    item = FirebaseItem(item_data, item_id)
                    return item

            return None
        except Exception as e:
            logger.error(f"Error getting item by ID: {str(e)}")
            return None

    def update_item(self, item_id, item_data, user_id):
        """Update an existing item"""
        try:
            # First check if item exists and belongs to user
            item_doc = self.db.collection('items').document(item_id).get()

            if not item_doc.exists:
                raise ValueError("Item not found")

            item_data_current = item_doc.to_dict()
            if item_data_current.get('user_id') != user_id:
                raise ValueError("Item does not belong to user")

            # Update the item
            item_data['updated_at'] = datetime.utcnow().isoformat()
            self.db.collection('items').document(item_id).update(item_data)

            logger.info(f"Item updated: {item_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating item: {str(e)}")
            raise

    def delete_item(self, item_id, user_id):
        """Soft delete an item"""
        try:
            # First check if item exists and belongs to user
            item_doc = self.db.collection('items').document(item_id).get()

            if not item_doc.exists:
                raise ValueError("Item not found")

            item_data_current = item_doc.to_dict()
            if item_data_current.get('user_id') != user_id:
                raise ValueError("Item does not belong to user")

            # Soft delete by marking as inactive
            self.db.collection('items').document(item_id).update({
                'is_active': False,
                'updated_at': datetime.utcnow().isoformat()
            })

            logger.info(f"Item deleted: {item_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting item: {str(e)}")
            raise

    # Customer operations
    def create_customer(self, customer_data, user_id):
        """Create a new customer"""
        try:
            customer = FirebaseCustomer()

            # Set customer properties
            for key, value in customer_data.items():
                if hasattr(customer, key):
                    setattr(customer, key, value)

            customer.user_id = user_id
            customer.id = str(uuid.uuid4())

            # Save to Firestore
            self.db.collection('customers').document(customer.id).set(customer.to_dict())

            logger.info(f"Customer created: {customer.name}")
            return customer

        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            raise

    def get_customers_by_user(self, user_id):
        """Get all customers for a user"""
        try:
            # Simple query without ordering to avoid index requirements
            docs = (self.db.collection('customers')
                   .where('user_id', '==', user_id)
                   .stream())
            customers = []

            for doc in docs:
                customer_data = doc.to_dict()
                customer_data['id'] = doc.id
                customers.append(customer_data)

            # Sort in Python instead of Firestore to avoid index requirement
            customers.sort(key=lambda x: x.get('created_at', ''), reverse=True)
            return customers

        except Exception as e:
            logger.error(f"Error getting customers: {str(e)}")
            return []

    def get_customer_by_id(self, customer_id, user_id):
        """Get a specific customer by ID"""
        try:
            customer_doc = self.db.collection('customers').document(customer_id).get()

            if customer_doc.exists:
                customer_data = customer_doc.to_dict()
                if customer_data.get('user_id') == user_id:
                    customer_data['id'] = customer_id
                    return customer_data

            return None
        except Exception as e:
            logger.error(f"Error getting customer by ID: {str(e)}")
            return None

    def update_customer(self, customer_id, customer_data, user_id):
        """Update an existing customer"""
        try:
            # First check if customer exists and belongs to user
            customer_doc = self.db.collection('customers').document(customer_id).get()

            if not customer_doc.exists:
                raise ValueError("Customer not found")

            customer_data_current = customer_doc.to_dict()
            if customer_data_current.get('user_id') != user_id:
                raise ValueError("Customer does not belong to user")

            # Update the customer
            customer_data['updated_at'] = datetime.utcnow().isoformat()
            self.db.collection('customers').document(customer_id).update(customer_data)

            logger.info(f"Customer updated: {customer_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating customer: {str(e)}")
            raise

    def delete_customer(self, customer_id, user_id):
        """Soft delete a customer"""
        try:
            # First check if customer exists and belongs to user
            customer_doc = self.db.collection('customers').document(customer_id).get()

            if not customer_doc.exists:
                raise ValueError("Customer not found")

            customer_data_current = customer_doc.to_dict()
            if customer_data_current.get('user_id') != user_id:
                raise ValueError("Customer does not belong to user")

            # Soft delete by marking as inactive
            self.db.collection('customers').document(customer_id).update({
                'is_active': False,
                'updated_at': datetime.utcnow().isoformat()
            })

            logger.info(f"Customer deleted: {customer_id}")
            return True

        except Exception as e:
            logger.error(f"Error deleting customer: {str(e)}")
            raise

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
                   .where('user_id', '==', user_id)
                   .where('is_active', '==', True)
                   .stream())
            categories = []

            for doc in docs:
                category = FirebaseCategory(doc.to_dict(), doc.id)
                categories.append(category)

            return categories

        except Exception as e:
            logger.error(f"Error getting categories: {str(e)}")
            return []

    def get_category_by_id(self, category_id, user_id):
        """Get a specific category by ID"""
        try:
            category_doc = self.db.collection('categories').document(category_id).get()

            if category_doc.exists:
                category_data = category_doc.to_dict()
                # Verify the category belongs to the user
                if category_data.get('user_id') == user_id:
                    category = FirebaseCategory(category_data, category_id)
                    return category

            return None
        except Exception as e:
            logger.error(f"Error getting category by ID: {str(e)}")
            return None

    # Sales operations
    def create_sale(self, sale_data, user_id):
        """Create a new sale"""
        try:
            sale = FirebaseSale()

            # Set sale properties
            for key, value in sale_data.items():
                if hasattr(sale, key):
                    setattr(sale, key, value)

            sale.user_id = user_id
            sale.id = str(uuid.uuid4())

            # Save to Firestore
            self.db.collection('sales').document(sale.id).set(sale.to_dict())

            logger.info(f"Sale created: {sale.id}")
            return sale

        except Exception as e:
            logger.error(f"Error creating sale: {str(e)}")
            raise

    def get_sales_by_user(self, user_id, limit=None):
        """Get all sales for a user"""
        try:
            # Simple query without ordering to avoid index requirements
            query = self.db.collection('sales').where('user_id', '==', user_id)

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

    def get_sale_by_id(self, sale_id, user_id):
        """Get a specific sale by ID"""
        try:
            sale_doc = self.db.collection('sales').document(sale_id).get()

            if sale_doc.exists:
                sale_data = sale_doc.to_dict()
                if sale_data.get('user_id') == user_id:
                    sale_data['id'] = sale_id
                    return sale_data

            return None
        except Exception as e:
            logger.error(f"Error getting sale by ID: {str(e)}")
            return None

    def update_sale(self, sale_id, sale_data, user_id):
        """Update an existing sale"""
        try:
            # First check if sale exists and belongs to user
            sale_doc = self.db.collection('sales').document(sale_id).get()

            if not sale_doc.exists:
                raise ValueError("Sale not found")

            sale_data_current = sale_doc.to_dict()
            if sale_data_current.get('user_id') != user_id:
                raise ValueError("Sale does not belong to user")

            # Update the sale
            sale_data['updated_at'] = datetime.utcnow().isoformat()
            self.db.collection('sales').document(sale_id).update(sale_data)

            logger.info(f"Sale updated: {sale_id}")
            return True

        except Exception as e:
            logger.error(f"Error updating sale: {str(e)}")
            raise

# Global Firebase service instance
firebase_service = FirebaseService()