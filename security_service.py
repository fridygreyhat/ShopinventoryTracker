"""
Security Service for Firebase API Key Protection
This service implements comprehensive security measures to protect Firebase API keys
and other sensitive credentials from unauthorized access.
"""

import os
import logging
import hashlib
import hmac
import time
import json
from typing import Optional, Dict, Any, List
from functools import wraps
from flask import request, session, jsonify, current_app

logger = logging.getLogger(__name__)

class SecurityService:
    """
    Comprehensive security service for protecting Firebase API keys and sensitive operations
    """
    
    def __init__(self):
        self.rate_limit_cache = {}
        self.failed_attempts = {}
        self.blacklisted_ips = set()
        
    def validate_api_key_access(self, user_id: str, ip_address: str) -> bool:
        """
        Validate if a user can access Firebase API key operations
        
        Args:
            user_id: User ID making the request
            ip_address: IP address of the request
            
        Returns:
            bool: True if access is allowed, False otherwise
        """
        # Check if IP is blacklisted
        if ip_address in self.blacklisted_ips:
            logger.warning(f"API key access denied for blacklisted IP: {ip_address}")
            return False
            
        # Check rate limiting
        if not self._check_rate_limit(user_id, ip_address):
            logger.warning(f"Rate limit exceeded for user {user_id} from IP {ip_address}")
            return False
            
        # Check if user is authenticated
        if not user_id or user_id not in session:
            logger.warning(f"Unauthenticated API key access attempt from IP {ip_address}")
            return False
            
        return True
    
    def _check_rate_limit(self, user_id: str, ip_address: str, max_requests: int = 100, window_seconds: int = 3600) -> bool:
        """
        Check if request is within rate limits
        
        Args:
            user_id: User ID
            ip_address: IP address
            max_requests: Maximum requests per window
            window_seconds: Time window in seconds
            
        Returns:
            bool: True if within limits, False otherwise
        """
        current_time = time.time()
        key = f"{user_id}:{ip_address}"
        
        # Clean old entries
        if key in self.rate_limit_cache:
            self.rate_limit_cache[key] = [
                timestamp for timestamp in self.rate_limit_cache[key]
                if current_time - timestamp < window_seconds
            ]
        else:
            self.rate_limit_cache[key] = []
        
        # Check if rate limit exceeded
        if len(self.rate_limit_cache[key]) >= max_requests:
            return False
            
        # Add current request
        self.rate_limit_cache[key].append(current_time)
        return True
    
    def log_security_event(self, event_type: str, user_id: str, ip_address: str, details: Dict[str, Any] = None):
        """
        Log security-related events for monitoring
        
        Args:
            event_type: Type of security event
            user_id: User ID involved
            ip_address: IP address
            details: Additional event details
        """
        log_entry = {
            'timestamp': time.time(),
            'event_type': event_type,
            'user_id': user_id,
            'ip_address': ip_address,
            'details': details or {}
        }
        
        # In a production environment, this would be sent to a security monitoring system
        logger.info(f"Security Event: {json.dumps(log_entry)}")
    
    def validate_firebase_credentials(self) -> bool:
        """
        Validate that Firebase credentials are properly configured
        
        Returns:
            bool: True if credentials are valid, False otherwise
        """
        try:
            # Check for required environment variables
            required_vars = ['FIREBASE_CREDENTIALS', 'FIREBASE_API_KEY']
            for var in required_vars:
                if not os.environ.get(var):
                    logger.error(f"Missing required environment variable: {var}")
                    return False
            
            # Validate Firebase credentials format
            firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
            try:
                cred_dict = json.loads(firebase_creds)
                required_keys = ['type', 'project_id', 'private_key_id', 'private_key', 'client_email']
                for key in required_keys:
                    if key not in cred_dict:
                        logger.error(f"Missing required key in Firebase credentials: {key}")
                        return False
            except json.JSONDecodeError:
                logger.error("Invalid Firebase credentials JSON format")
                return False
            
            # Validate API key format
            api_key = os.environ.get('FIREBASE_API_KEY')
            if not api_key.startswith('AIza'):
                logger.error("Invalid Firebase API key format")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Error validating Firebase credentials: {str(e)}")
            return False
    
    def generate_secure_token(self, user_id: str, operation: str) -> str:
        """
        Generate a secure token for sensitive operations
        
        Args:
            user_id: User ID
            operation: Operation being performed
            
        Returns:
            str: Secure token
        """
        timestamp = str(int(time.time()))
        secret = os.environ.get('SESSION_SECRET', 'default-secret')
        
        # Create token data
        token_data = f"{user_id}:{operation}:{timestamp}"
        
        # Generate HMAC signature
        signature = hmac.new(
            secret.encode('utf-8'),
            token_data.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        
        return f"{token_data}:{signature}"
    
    def validate_secure_token(self, token: str, user_id: str, operation: str, max_age: int = 3600) -> bool:
        """
        Validate a secure token
        
        Args:
            token: Token to validate
            user_id: Expected user ID
            operation: Expected operation
            max_age: Maximum token age in seconds
            
        Returns:
            bool: True if token is valid, False otherwise
        """
        try:
            parts = token.split(':')
            if len(parts) != 4:
                return False
            
            token_user_id, token_operation, timestamp, signature = parts
            
            # Validate token content
            if token_user_id != user_id or token_operation != operation:
                return False
            
            # Check token age
            if time.time() - int(timestamp) > max_age:
                return False
            
            # Validate signature
            secret = os.environ.get('SESSION_SECRET', 'default-secret')
            token_data = f"{token_user_id}:{token_operation}:{timestamp}"
            expected_signature = hmac.new(
                secret.encode('utf-8'),
                token_data.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            
            return hmac.compare_digest(signature, expected_signature)
            
        except Exception as e:
            logger.error(f"Error validating secure token: {str(e)}")
            return False

# Global security service instance
security_service = SecurityService()

def require_firebase_access(f):
    """
    Decorator to require Firebase API key access validation
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Get user ID from session
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Get IP address
        ip_address = request.environ.get('HTTP_X_FORWARDED_FOR', request.remote_addr)
        
        # Validate access
        if not security_service.validate_api_key_access(user_id, ip_address):
            security_service.log_security_event(
                'firebase_access_denied',
                user_id,
                ip_address,
                {'endpoint': request.endpoint}
            )
            return jsonify({'error': 'Access denied'}), 403
        
        # Log successful access
        security_service.log_security_event(
            'firebase_access_granted',
            user_id,
            ip_address,
            {'endpoint': request.endpoint}
        )
        
        return f(*args, **kwargs)
    
    return decorated_function

def validate_environment_security():
    """
    Validate that the environment is properly secured
    
    Returns:
        List[str]: List of security issues found
    """
    issues = []
    
    # Check if Firebase credentials are in environment variables
    if not os.environ.get('FIREBASE_CREDENTIALS'):
        issues.append("FIREBASE_CREDENTIALS environment variable not set")
    
    if not os.environ.get('FIREBASE_API_KEY'):
        issues.append("FIREBASE_API_KEY environment variable not set")
    
    # Check session secret
    session_secret = os.environ.get('SESSION_SECRET')
    if not session_secret or session_secret == 'your-secret-key-change-this-in-production':
        issues.append("SESSION_SECRET should be changed from default value")
    
    # Check if running in production mode
    if os.environ.get('FLASK_ENV') == 'development':
        issues.append("Application running in development mode - consider production settings")
    
    return issues