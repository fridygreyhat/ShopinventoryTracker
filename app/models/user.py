"""
User model and authentication
"""
from datetime import datetime, timedelta
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db


class User(UserMixin, db.Model):
    """User model with authentication and preferences"""
    __tablename__ = 'users'
    
    # Primary identification
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(320), unique=True, nullable=False)
    password_hash = db.Column(db.String(256), nullable=False)
    
    # Personal information
    first_name = db.Column(db.String(64), nullable=True)
    last_name = db.Column(db.String(64), nullable=True)
    phone = db.Column(db.String(20), nullable=True)
    
    # Business information
    shop_name = db.Column(db.String(128), nullable=True)
    product_categories = db.Column(db.String(512), nullable=True)
    business_type = db.Column(db.String(100), default='retail', nullable=False)
    
    # Account status
    email_verified = db.Column(db.Boolean, default=False, nullable=False)
    active = db.Column(db.Boolean, default=True, nullable=False)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    role = db.Column(db.String(50), default='user', nullable=False)
    
    # Timestamps
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # User preferences
    language = db.Column(db.String(10), default='en', nullable=False)
    currency_format = db.Column(db.String(10), default='TSh', nullable=False)
    date_format = db.Column(db.String(20), default='DD/MM/YYYY', nullable=False)
    timezone = db.Column(db.String(50), default='Africa/Dar_es_Salaam', nullable=False)
    
    # Notification settings
    email_notifications = db.Column(db.Boolean, default=True, nullable=False)
    sms_notifications = db.Column(db.Boolean, default=False, nullable=False)
    low_stock_alerts = db.Column(db.Boolean, default=True, nullable=False)
    sales_reports = db.Column(db.Boolean, default=True, nullable=False)
    
    # Business settings
    default_tax_rate = db.Column(db.Numeric(5, 2), default=0, nullable=False)
    low_stock_threshold = db.Column(db.Integer, default=10, nullable=False)
    
    # Password reset
    reset_token = db.Column(db.String(255), nullable=True)
    reset_token_expires = db.Column(db.DateTime, nullable=True)
    
    # Email verification
    email_verification_token = db.Column(db.String(255), nullable=True)
    email_verification_token_expires = db.Column(db.DateTime, nullable=True)
    
    # Relationships
    items = db.relationship('Item', backref='user', lazy=True, cascade='all, delete-orphan')
    sales = db.relationship('Sale', backref='user', lazy=True, cascade='all, delete-orphan')
    customers = db.relationship('Customer', backref='user', lazy=True, cascade='all, delete-orphan')
    locations = db.relationship('Location', backref='user', lazy=True, cascade='all, delete-orphan')
    financial_transactions = db.relationship('FinancialTransaction', backref='user', lazy=True, cascade='all, delete-orphan')
    
    def __init__(self, **kwargs):
        """Initialize user with provided data"""
        super(User, self).__init__(**kwargs)
        
    def set_password(self, password):
        """Set user password with hash"""
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        """Check if provided password matches hash"""
        return check_password_hash(self.password_hash, password)
        
    def generate_reset_token(self):
        """Generate password reset token"""
        import secrets
        self.reset_token = secrets.token_urlsafe(32)
        self.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
        return self.reset_token
        
    def verify_reset_token(self, token):
        """Verify password reset token"""
        if (self.reset_token == token and 
            self.reset_token_expires and 
            self.reset_token_expires > datetime.utcnow()):
            return True
        return False
        
    def clear_reset_token(self):
        """Clear password reset token"""
        self.reset_token = None
        self.reset_token_expires = None
        
    def generate_email_verification_token(self):
        """Generate email verification token"""
        import secrets
        self.email_verification_token = secrets.token_urlsafe(32)
        self.email_verification_token_expires = datetime.utcnow() + timedelta(days=1)
        return self.email_verification_token
        
    def verify_email_token(self, token):
        """Verify email verification token"""
        if (self.email_verification_token == token and 
            self.email_verification_token_expires and 
            self.email_verification_token_expires > datetime.utcnow()):
            self.email_verified = True
            self.email_verification_token = None
            self.email_verification_token_expires = None
            return True
        return False
        
    def has_permission(self, permission):
        """Check if user has specific permission"""
        if self.is_admin:
            return True
        
        # Define role-based permissions
        permissions_map = {
            'user': ['view_own_data'],
            'inventory_manager': ['manage_inventory', 'manage_categories', 'manage_locations'],
            'sales_manager': ['manage_sales', 'view_reports'],
            'accountant': ['manage_finances', 'view_reports'],
            'manager': ['manage_inventory', 'manage_sales', 'manage_finances', 'view_reports']
        }
        
        user_permissions = permissions_map.get(self.role, [])
        return permission in user_permissions
        
    @property
    def full_name(self):
        """Get user's full name"""
        if self.first_name and self.last_name:
            return f"{self.first_name} {self.last_name}"
        return self.username
        
    @property
    def display_name(self):
        """Get display name for UI"""
        return self.shop_name or self.full_name or self.username
        
    def to_dict(self):
        """Convert user to dictionary for API responses"""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'first_name': self.first_name,
            'last_name': self.last_name,
            'shop_name': self.shop_name,
            'phone': self.phone,
            'business_type': self.business_type,
            'active': self.active,
            'is_admin': self.is_admin,
            'role': self.role,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'language': self.language,
            'currency_format': self.currency_format
        }
        
    def __repr__(self):
        return f'<User {self.username}>'