from firebase_config import firebase_config
from firebase_models import UserModel, ItemModel, SaleModel, CustomerModel, CategoryModel
import logging
import uuid
from datetime import datetime

logger = logging.getLogger(__name__)

class FirebaseService:
    """Service layer for Firebase operations"""

    def __init__(self):
        # Ensure Firebase is initialized before accessing db and auth
        if not firebase_config.initialized:
            firebase_config.initialize_firebase()
        self.db = firebase_config.db
        self.auth = firebase_config.auth
    
    def get_firebase_api_key(self):
        """Get Firebase API key for REST API authentication"""
        return firebase_config.api_key

    # User operations
    def create_user(self, user_data, password=None):
        """Create a new user in Firebase"""
        try:
            # Use provided password or get from user_data
            user_password = password or user_data.get('password')
            if not user_password:
                raise ValueError("Password is required for user creation")
            
            # Create user in Firebase Auth
            auth_user = self.auth.create_user(
                email=user_data['email'],
                password=user_password,
                display_name=f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip(),
                email_verified=False
            )

            # Create user document in Firestore using UserModel
            user_doc_data = UserModel.create_user_data(
                email=user_data['email'],
                first_name=user_data.get('first_name', ''),
                last_name=user_data.get('last_name', ''),
                username=user_data.get('username', user_data['email'].split('@')[0]),
                phone=user_data.get('phone', ''),
                is_admin=user_data.get('is_admin', False),
                is_active=user_data.get('is_active', True),
                created_at=datetime.utcnow().isoformat()
            )
            
            # Add shop-specific fields
            user_doc_data.update({
                'shop_name': user_data.get('shop_name', ''),
                'product_categories': user_data.get('product_categories', ''),
                'email_verified': user_data.get('email_verified', False)
            })

            # Save to Firestore
            self.db.collection('users').document(auth_user.uid).set(user_doc_data)

            logger.info(f"User created successfully: {user_data['email']}")
            # Return user data with ID
            user_doc_data['id'] = auth_user.uid
            return user_doc_data

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
                user_data = user_doc.to_dict()
                user_data['id'] = auth_user.uid
                return user_data

            return None

        except Exception as e:
            logger.error(f"Error getting user by email: {str(e)}")
            return None

    def get_user_by_id(self, user_id):
        """Get user by ID"""
        try:
            user_doc = self.db.collection('users').document(user_id).get()

            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_data['id'] = user_id
                return user_data

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
            # Create item data using ItemModel
            item_doc_data = ItemModel.create_item_data(
                name=item_data['name'],
                user_id=user_id,
                **item_data
            )
            
            item_id = str(uuid.uuid4())
            item_doc_data['id'] = item_id

            # Save to Firestore
            self.db.collection('items').document(item_id).set(item_doc_data)

            logger.info(f"Item created: {item_data['name']}")
            return item_doc_data

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
                item_data = doc.to_dict()
                item_data['id'] = doc.id
                items.append(item_data)

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
                    item_data['id'] = item_id
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
            # Create category data using CategoryModel
            category_doc_data = CategoryModel.create_category_data(
                name=category_data['name'],
                user_id=user_id,
                **category_data
            )
            
            category_id = str(uuid.uuid4())
            category_doc_data['id'] = category_id

            # Save to Firestore
            self.db.collection('categories').document(category_id).set(category_doc_data)

            logger.info(f"Category created: {category_data['name']}")
            return category_doc_data

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
                category_data = doc.to_dict()
                category_data['id'] = doc.id
                categories.append(category_data)

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
                    category_data['id'] = category_id
                    return category_data

            return None
        except Exception as e:
            logger.error(f"Error getting category by ID: {str(e)}")
            return None

    def update_category(self, category_id, updates, user_id):
        """Update a category"""
        try:
            category_ref = self.db.collection('categories').document(category_id)
            category_doc = category_ref.get()

            if category_doc.exists:
                category_data = category_doc.to_dict()
                if category_data.get('user_id') == user_id:
                    updates['updated_at'] = datetime.utcnow().isoformat()
                    category_ref.update(updates)
                    logger.info(f"Category updated: {category_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error updating category: {str(e)}")
            return False

    def delete_category(self, category_id, user_id):
        """Soft delete a category"""
        try:
            category_ref = self.db.collection('categories').document(category_id)
            category_doc = category_ref.get()

            if category_doc.exists:
                category_data = category_doc.to_dict()
                if category_data.get('user_id') == user_id:
                    # Also delete subcategories
                    subcategories_ref = self.db.collection('categories').where('parent_id', '==', category_id)
                    subcategories = subcategories_ref.stream()

                    for subcategory in subcategories:
                        subcategory.reference.update({
                            'is_active': False,
                            'updated_at': datetime.utcnow().isoformat()
                        })

                    # Soft delete the main category
                    category_ref.update({
                        'is_active': False,
                        'updated_at': datetime.utcnow().isoformat()
                    })

                    logger.info(f"Category deleted: {category_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error deleting category: {str(e)}")
            return False

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