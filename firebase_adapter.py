from firebase_service import firebase_service
from firebase_models import UserModel, ItemModel, SaleModel, CustomerModel, CategoryModel
from datetime import datetime
import logging
import uuid

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
            user_doc = self.service.db.collection('users').document(user_id).get()
            if user_doc.exists:
                user_data = user_doc.to_dict()
                user_data['id'] = user_id
                return user_data
            return None
        except Exception as e:
            logger.error(f"Error getting user by ID {user_id}: {str(e)}")
            return None



    def get_customers_by_user(self, user_id):
        """Get all customers for a user"""
        try:
            customers_ref = self.service.db.collection('customers').where('user_id', '==', user_id)
            customers_docs = customers_ref.stream()

            customers_data = []
            for doc in customers_docs:
                customer_data = doc.to_dict()
                customer_data['id'] = doc.id
                customers_data.append(customer_data)

            return customers_data
        except Exception as e:
            logger.error(f"Error getting customers for user {user_id}: {str(e)}")
            return []

    def create_customer(self, customer_data, user_id):
        """Create a new customer"""
        try:
            customer_data['user_id'] = user_id
            customer_data['created_at'] = datetime.utcnow().isoformat()
            customer_data['updated_at'] = datetime.utcnow().isoformat()

            doc_ref = self.service.db.collection('customers').add(customer_data)
            customer_data['id'] = doc_ref[1].id
            return customer_data
        except Exception as e:
            logger.error(f"Error creating customer: {str(e)}")
            raise e

    def create_category(self, category_data, user_id):
        """Create a new category"""
        try:
            category_data['user_id'] = user_id
            category_data['created_at'] = datetime.utcnow().isoformat()
            category_data['updated_at'] = datetime.utcnow().isoformat()
            category_data['is_active'] = True

            doc_ref = self.service.db.collection('categories').add(category_data)
            category_data['id'] = doc_ref[1].id
            return category_data
        except Exception as e:
            logger.error(f"Error creating category: {str(e)}")
            raise e

    def delete_item(self, item_id, user_id):
        """Soft delete an item"""
        try:
            # Verify item belongs to user
            item_doc = self.service.db.collection('items').document(item_id).get()
            if not item_doc.exists:
                raise Exception("Item not found")

            item_data = item_doc.to_dict()
            if item_data.get('user_id') != user_id:
                raise Exception("Unauthorized access to item")

            # Soft delete by marking as inactive
            self.service.db.collection('items').document(item_id).update({
                'is_active': False,
                'updated_at': datetime.utcnow().isoformat()
            })

            return True
        except Exception as e:
            logger.error(f"Error deleting item {item_id}: {str(e)}")
            raise e

    def get_user_by_email(self, email):
        """Get user by email from Firebase"""
        try:
            # Ensure Firebase is initialized
            if not self.service.db:
                logger.error("Firebase not initialized")
                return None
                
            # First, try to get user from Firebase Auth
            from firebase_admin import auth
            try:
                auth_user = auth.get_user_by_email(email)
                logger.debug(f"Found user in Firebase Auth: {email}")

                # Then get user document from Firestore
                user_doc = self.service.db.collection('users').document(auth_user.uid).get()
                if user_doc.exists:
                    user_data = user_doc.to_dict()
                    user_data['id'] = auth_user.uid
                    logger.debug(f"Found user in Firestore: {email}")
                    return user_data
                else:
                    logger.debug(f"User exists in Auth but not in Firestore: {email}")
                    return None

            except auth.UserNotFoundError:
                logger.debug(f"User not found in Firebase Auth: {email}")
                return None
            except Exception as auth_error:
                logger.error(f"Firebase Auth error for {email}: {str(auth_error)}")
                return None

        except Exception as e:
            logger.error(f"Unexpected error getting user by email {email}: {str(e)}")
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
                    .where('user_id', '==', user_id)
                    .where('is_active', '==', True))

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

    def get_item_by_id(self, item_id, user_id):
        """Get a specific item by ID"""
        try:
            item_doc = self.service.db.collection('items').document(item_id).get()

            if item_doc.exists:
                item_data = item_doc.to_dict()
                if item_data.get('user_id') == user_id:
                    return item_data

            return None
        except Exception as e:
            logger.error(f"Error getting item by ID: {str(e)}")
            return None

    def get_item_by_sku(self, sku, user_id):
        """Get a specific item by SKU"""
        try:
            query = (self.service.db.collection('items')
                    .where('sku', '==', sku)
                    .where('user_id', '==', user_id)
                    .limit(1))

            docs = list(query.stream())
            if docs:
                item_data = docs[0].to_dict()
                item_data['id'] = docs[0].id
                return item_data

            return None
        except Exception as e:
            logger.error(f"Error getting item by SKU: {str(e)}")
            return None

    def item_exists(self, sku, user_id):
        """Check if an item with given SKU exists for user"""
        try:
            query = (self.service.db.collection('items')
                    .where('sku', '==', sku)
                    .where('user_id', '==', user_id)
                    .limit(1))

            docs = list(query.stream())
            return len(docs) > 0
        except Exception as e:
            logger.error(f"Error checking if item exists: {str(e)}")
            return False

    def add(self, item):
        """Add item to Firebase (for CSV import compatibility)"""
        try:
            if hasattr(item, 'to_dict'):
                item_data = item.to_dict()
            else:
                item_data = item.__dict__ if hasattr(item, '__dict__') else item

            # Generate ID if not present
            if not item_data.get('id'):
                item_data['id'] = str(uuid.uuid4())

            # Save to Firestore
            self.service.db.collection('items').document(item_data['id']).set(item_data)
            return item_data
        except Exception as e:
            logger.error(f"Error adding item: {str(e)}")
            raise

    def commit(self):
        """Commit changes (Firebase auto-commits, so this is a no-op)"""
        return True

    def rollback(self):
        """Rollback changes (Firebase doesn't support transactions in this context)"""
        logger.warning("Rollback called on Firebase adapter - no action taken")
        return True

    def update_item_stock(self, item_id, new_stock, user_id):
        """Update item stock quantity"""
        try:
            item_ref = self.service.db.collection('items').document(item_id)
            item_doc = item_ref.get()
            
            if item_doc.exists:
                item_data = item_doc.to_dict()
                if item_data.get('user_id') == user_id:
                    item_ref.update({
                        'stock_quantity': new_stock,
                        'updated_at': datetime.now().isoformat()
                    })
                    logger.info(f"Stock updated for item {item_id}: {new_stock}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error updating item stock: {str(e)}")
            return False

    # Sale operations
    def create_sale(self, sale_data, user_id):
        """Create sale using Firebase service"""
        return self.service.create_sale(sale_data, user_id)

    def get_sales_by_user(self, user_id, limit=None):
        """Get sales using Firebase service"""
        sales = self.service.get_sales_by_user(user_id, limit)
        # Convert to dict format for API compatibility
        return [sale.to_dict() if hasattr(sale, 'to_dict') else sale for sale in sales]

    def get_sale_by_id(self, sale_id, user_id):
        """Get a specific sale by ID"""
        try:
            sale_doc = self.service.db.collection('sales').document(sale_id).get()
            
            if sale_doc.exists:
                sale_data = sale_doc.to_dict()
                if sale_data.get('user_id') == user_id:
                    sale_data['id'] = sale_id
                    return sale_data
                    
            return None
        except Exception as e:
            logger.error(f"Error getting sale by ID: {str(e)}")
            return None

    def update_sale(self, sale_id, updates, user_id):
        """Update a sale"""
        try:
            sale_ref = self.service.db.collection('sales').document(sale_id)
            sale_doc = sale_ref.get()
            
            if sale_doc.exists:
                sale_data = sale_doc.to_dict()
                if sale_data.get('user_id') == user_id:
                    updates['updated_at'] = datetime.now().isoformat()
                    sale_ref.update(updates)
                    logger.info(f"Sale updated: {sale_id}")
                    return True
            return False
        except Exception as e:
            logger.error(f"Error updating sale: {str(e)}")
            return False

    # Customer operations
    def create_customer(self, customer_data, user_id):
        """Create customer using Firebase service"""
        return self.service.create_customer(customer_data, user_id)

    def get_customers_by_user(self, user_id):
        """Get customers using Firebase service"""
        try:
            customers = self.service.get_customers_by_user(user_id)
            # Handle both dict and object formats
            formatted_customers = []
            for customer in customers:
                if hasattr(customer, 'to_dict'):
                    formatted_customers.append(customer.to_dict())
                elif isinstance(customer, dict):
                    formatted_customers.append(customer)
                else:
                    formatted_customers.append(customer.__dict__ if hasattr(customer, '__dict__') else {})
            return formatted_customers
        except Exception as e:
            logger.error(f"Error getting customers for user {user_id}: {str(e)}")
            return []

    def get_customer_by_id(self, customer_id, user_id):
        """Get a specific customer by ID"""
        try:
            customer_ref = self.service.db.collection('customers').document(customer_id)
            customer_doc = customer_ref.get()
            
            if customer_doc.exists:
                customer_data = customer_doc.to_dict()
                if customer_data.get('user_id') == user_id:
                    customer_data['id'] = customer_id
                    return customer_data
                    
            return None
        except Exception as e:
            logger.error(f"Error getting customer by ID: {str(e)}")
            return None

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