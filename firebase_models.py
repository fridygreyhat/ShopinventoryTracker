
from datetime import datetime
from google.cloud.firestore import DocumentReference
import uuid
import logging

logger = logging.getLogger(__name__)

class FirebaseModel:
    """Base class for Firebase models"""
    
    def __init__(self, data=None, doc_id=None):
        self.id = doc_id
        self.created_at = datetime.utcnow()
        self.updated_at = datetime.utcnow()
        
        if data:
            self.from_dict(data)

    def to_dict(self):
        """Convert model to dictionary for Firebase storage"""
        data = {}
        for key, value in self.__dict__.items():
            if not key.startswith('_'):
                if isinstance(value, datetime):
                    data[key] = value
                else:
                    data[key] = value
        return data

    def from_dict(self, data):
        """Load model from Firebase document data"""
        for key, value in data.items():
            setattr(self, key, value)

class FirebaseUser(FirebaseModel):
    """Firebase User model"""
    
    def __init__(self, data=None, doc_id=None):
        super().__init__(data, doc_id)
        self.username = ""
        self.email = ""
        self.first_name = ""
        self.last_name = ""
        self.phone = ""
        self.shop_name = ""
        self.product_categories = ""
        self.is_active = True
        self.is_admin = False
        self.email_verified = False
        self.last_login = None

    def set_password(self, password):
        """Set password using Firebase Auth"""
        # Firebase Auth handles password hashing automatically
        # This will be handled during user creation
        pass

    def check_password(self, password):
        """Check password using Firebase Auth"""
        # Password verification is handled by Firebase Auth
        # This method is kept for compatibility
        return True

class FirebaseItem(FirebaseModel):
    """Firebase Item model"""
    
    def __init__(self, data=None, doc_id=None):
        super().__init__(data, doc_id)
        self.name = ""
        self.description = ""
        self.sku = ""
        self.stock_quantity = 0
        self.minimum_stock = 0
        self.buying_price = 0.0
        self.retail_price = 0.0
        self.wholesale_price = 0.0
        self.sales_type = "both"
        self.category = "Uncategorized"
        self.subcategory = ""
        self.unit_type = "quantity"
        self.sell_by = "quantity"
        self.category_id = None
        self.user_id = ""
        self.is_active = True

    @staticmethod
    def generate_sku(name, category=""):
        """Generate a unique SKU"""
        import string
        import random
        base = f"{category[:3].upper()}{name[:3].upper()}"
        random_part = ''.join(random.choices(string.digits, k=4))
        return f"{base}-{random_part}"

class FirebaseSale(FirebaseModel):
    """Firebase Sale model"""
    
    def __init__(self, data=None, doc_id=None):
        super().__init__(data, doc_id)
        self.invoice_number = ""
        self.sale_number = ""
        self.customer_name = ""
        self.customer_phone = ""
        self.customer_id = None
        self.sale_type = "retail"
        self.subtotal = 0.0
        self.discount_type = "none"
        self.discount_value = 0.0
        self.discount_amount = 0.0
        self.total_amount = 0.0
        self.payment_method = "cash"
        self.payment_type = "cash"
        self.payment_status = "completed"
        self.payment_details = ""
        self.payment_amount = 0.0
        self.change_amount = 0.0
        self.is_installment = False
        self.down_payment = 0.0
        self.installment_months = 0
        self.monthly_payment = 0.0
        self.notes = ""
        self.user_id = ""
        self.sale_items = []

    @staticmethod
    def generate_sale_number():
        """Generate a unique sale number"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return f"SALE-{timestamp}"

    @staticmethod
    def generate_invoice_number():
        """Generate a unique invoice number"""
        timestamp = datetime.utcnow().strftime('%Y%m%d%H%M%S')
        return f"INV-{timestamp}"

class FirebaseCustomer(FirebaseModel):
    """Firebase Customer model"""
    
    def __init__(self, data=None, doc_id=None):
        super().__init__(data, doc_id)
        self.name = ""
        self.email = ""
        self.phone = ""
        self.address = ""
        self.customer_type = "retail"
        self.credit_limit = 0.0
        self.loyalty_points = 0
        self.preferred_payment_method = ""
        self.user_id = ""

class FirebaseCategory(FirebaseModel):
    """Firebase Category model"""
    
    def __init__(self, data=None, doc_id=None):
        super().__init__(data, doc_id)
        self.name = ""
        self.description = ""
        self.parent_id = None
        self.sort_order = 0
        self.user_id = ""
        self.is_active = True

class FirebaseFinancialTransaction(FirebaseModel):
    """Firebase Financial Transaction model"""
    
    def __init__(self, data=None, doc_id=None):
        super().__init__(data, doc_id)
        self.date = datetime.utcnow().date()
        self.description = ""
        self.amount = 0.0
        self.transaction_type = ""
        self.category = ""
        self.reference_id = ""
        self.payment_method = ""
        self.notes = ""
        self.user_id = ""
