
import pyotp
import qrcode
import io
import base64
import hashlib
import secrets
from datetime import datetime, timedelta
from flask import session
from werkzeug.security import generate_password_hash
import logging

logger = logging.getLogger(__name__)

class SecurityService:
    def __init__(self, user_id):
        self.user_id = user_id

    def setup_2fa(self, user_email):
        """Set up two-factor authentication for user"""
        try:
            # Generate secret key
            secret = pyotp.random_base32()
            
            # Create TOTP object
            totp = pyotp.TOTP(secret)
            
            # Generate QR code
            provisioning_uri = totp.provisioning_uri(
                name=user_email,
                issuer_name="Inventory Management System"
            )
            
            # Create QR code image
            qr = qrcode.QRCode(version=1, box_size=10, border=5)
            qr.add_data(provisioning_uri)
            qr.make(fit=True)
            
            img = qr.make_image(fill_color="black", back_color="white")
            img_buffer = io.BytesIO()
            img.save(img_buffer, format='PNG')
            img_str = base64.b64encode(img_buffer.getvalue()).decode()
            
            return {
                'secret': secret,
                'qr_code': f"data:image/png;base64,{img_str}",
                'manual_entry_key': secret
            }
            
        except Exception as e:
            logger.error(f"Error setting up 2FA: {str(e)}")
            return {'error': str(e)}

    def verify_2fa_token(self, secret, token):
        """Verify 2FA token"""
        try:
            totp = pyotp.TOTP(secret)
            return totp.verify(token, valid_window=1)
        except Exception as e:
            logger.error(f"Error verifying 2FA token: {str(e)}")
            return False

    def check_role_permission(self, user_role, required_permission):
        """Check if user role has required permission"""
        try:
            from models import Role, Permission
            
            # Define role permissions
            role_permissions = {
                'admin': ['all'],
                'manager': ['inventory.read', 'inventory.write', 'sales.read', 'sales.write', 'reports.read'],
                'employee': ['inventory.read', 'sales.read', 'sales.write'],
                'viewer': ['inventory.read', 'reports.read']
            }
            
            user_permissions = role_permissions.get(user_role, [])
            
            return 'all' in user_permissions or required_permission in user_permissions
            
        except Exception as e:
            logger.error(f"Error checking role permission: {str(e)}")
            return False

    def encrypt_sensitive_data(self, data):
        """Encrypt sensitive data"""
        try:
            from cryptography.fernet import Fernet
            import os
            
            # Get encryption key from environment or generate
            key = os.environ.get('ENCRYPTION_KEY')
            if not key:
                key = Fernet.generate_key()
                # In production, store this securely
                
            fernet = Fernet(key)
            encrypted_data = fernet.encrypt(data.encode())
            
            return base64.b64encode(encrypted_data).decode()
            
        except Exception as e:
            logger.error(f"Error encrypting data: {str(e)}")
            return data

    def decrypt_sensitive_data(self, encrypted_data):
        """Decrypt sensitive data"""
        try:
            from cryptography.fernet import Fernet
            import os
            
            key = os.environ.get('ENCRYPTION_KEY')
            if not key:
                return encrypted_data
                
            fernet = Fernet(key)
            decrypted_data = fernet.decrypt(base64.b64decode(encrypted_data.encode()))
            
            return decrypted_data.decode()
            
        except Exception as e:
            logger.error(f"Error decrypting data: {str(e)}")
            return encrypted_data

    def audit_user_action(self, action, details=None):
        """Log user actions for security audit"""
        try:
            from models import SecurityAudit, db
            
            audit_log = SecurityAudit(
                user_id=self.user_id,
                action=action,
                details=details or {},
                ip_address=session.get('ip_address'),
                user_agent=session.get('user_agent'),
                timestamp=datetime.utcnow()
            )
            
            db.session.add(audit_log)
            db.session.commit()
            
            return True
            
        except Exception as e:
            logger.error(f"Error logging audit: {str(e)}")
            return False

    def generate_secure_token(self, length=32):
        """Generate cryptographically secure token"""
        return secrets.token_urlsafe(length)

    def hash_api_key(self, api_key):
        """Hash API key for secure storage"""
        salt = secrets.token_hex(16)
        hashed = hashlib.pbkdf2_hmac('sha256', api_key.encode(), salt.encode(), 100000)
        return f"{salt}:{hashed.hex()}"

    def verify_api_key(self, api_key, stored_hash):
        """Verify API key against stored hash"""
        try:
            salt, hashed = stored_hash.split(':')
            computed_hash = hashlib.pbkdf2_hmac('sha256', api_key.encode(), salt.encode(), 100000)
            return computed_hash.hex() == hashed
        except Exception:
            return False
