
import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class FirebaseSettings:
    """Comprehensive Firebase settings and configuration management"""
    
    def __init__(self):
        self.settings = self._load_default_settings()
        self._validate_environment_variables()
    
    def _load_default_settings(self) -> Dict[str, Any]:
        """Load default Firebase settings"""
        return {
            # Core Firebase Configuration
            'project_id': '',
            'api_key': '',
            'auth_domain': '',
            'database_url': '',
            'storage_bucket': '',
            'messaging_sender_id': '',
            'app_id': '',
            'measurement_id': '',
            
            # Service Account Configuration
            'service_account': {
                'type': 'service_account',
                'project_id': '',
                'private_key_id': '',
                'private_key': '',
                'client_email': '',
                'client_id': '',
                'auth_uri': 'https://accounts.google.com/o/oauth2/auth',
                'token_uri': 'https://oauth2.googleapis.com/token',
                'auth_provider_x509_cert_url': 'https://www.googleapis.com/oauth2/v1/certs',
                'client_x509_cert_url': ''
            },
            
            # Firestore Configuration
            'firestore': {
                'collections': {
                    'users': 'users',
                    'items': 'items',
                    'customers': 'customers',
                    'sales': 'sales',
                    'categories': 'categories',
                    'transactions': 'transactions',
                    'accounting': 'accounting',
                    'reports': 'reports',
                    'settings': 'app_settings'
                },
                'indexes': {
                    'compound_indexes': [
                        {'collection': 'items', 'fields': ['user_id', 'is_active', 'category']},
                        {'collection': 'sales', 'fields': ['user_id', 'created_at', 'status']},
                        {'collection': 'customers', 'fields': ['user_id', 'customer_type', 'created_at']}
                    ]
                }
            },
            
            # Firebase Auth Configuration
            'auth': {
                'sign_in_methods': ['email', 'google', 'phone'],
                'password_policy': {
                    'min_length': 8,
                    'require_uppercase': True,
                    'require_lowercase': True,
                    'require_numbers': True,
                    'require_symbols': False
                },
                'session_timeout': 3600,  # 1 hour
                'max_sessions_per_user': 5
            },
            
            # Firebase Storage Configuration
            'storage': {
                'bucket_name': '',
                'max_file_size': 10 * 1024 * 1024,  # 10MB
                'allowed_file_types': ['jpg', 'jpeg', 'png', 'gif', 'pdf', 'csv', 'xlsx'],
                'upload_paths': {
                    'profile_images': 'users/profiles/',
                    'product_images': 'products/images/',
                    'documents': 'documents/',
                    'exports': 'exports/',
                    'imports': 'imports/'
                }
            },
            
            # Firebase Cloud Functions Configuration
            'cloud_functions': {
                'region': 'us-central1',
                'functions': {
                    'backup_data': 'backupUserData',
                    'send_notifications': 'sendNotifications',
                    'generate_reports': 'generateReports',
                    'process_imports': 'processImports'
                }
            },
            
            # Firebase Analytics Configuration
            'analytics': {
                'enabled': True,
                'track_page_views': True,
                'track_user_engagement': True,
                'custom_events': {
                    'inventory_add': 'inventory_item_added',
                    'sale_completed': 'sale_transaction_completed',
                    'customer_added': 'customer_created',
                    'report_generated': 'report_generated'
                }
            },
            
            # Security Rules Configuration
            'security_rules': {
                'firestore': {
                    'user_isolation': True,
                    'admin_override': True,
                    'rate_limiting': {
                        'reads_per_minute': 1000,
                        'writes_per_minute': 500
                    }
                }
            },
            
            # Backup and Recovery Configuration
            'backup': {
                'enabled': True,
                'schedule': 'daily',
                'retention_days': 30,
                'collections_to_backup': ['users', 'items', 'sales', 'customers'],
                'export_format': 'json'
            },
            
            # Performance and Optimization
            'performance': {
                'cache_duration': 300,  # 5 minutes
                'batch_size': 500,
                'connection_pool_size': 10,
                'timeout_seconds': 30
            },
            
            # Development and Testing Configuration
            'development': {
                'emulator_mode': False,
                'debug_mode': True,
                'test_collections': {
                    'prefix': 'test_',
                    'auto_cleanup': True
                }
            }
        }
    
    def _validate_environment_variables(self):
        """Validate required environment variables"""
        required_vars = [
            'FIREBASE_CREDENTIALS',
            'FIREBASE_API_KEY'
        ]
        
        missing_vars = []
        for var in required_vars:
            if not os.environ.get(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.warning(f"Missing Firebase environment variables: {missing_vars}")
    
    def get_credentials_from_env(self) -> Optional[Dict[str, Any]]:
        """Get Firebase credentials from environment variables"""
        try:
            firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
            if firebase_creds:
                return json.loads(firebase_creds)
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Invalid Firebase credentials JSON: {e}")
            return None
    
    def get_api_key(self) -> Optional[str]:
        """Get Firebase API key from environment"""
        return os.environ.get('FIREBASE_API_KEY')
    
    def get_web_config(self) -> Dict[str, str]:
        """Get Firebase web configuration for client-side SDK"""
        credentials = self.get_credentials_from_env()
        api_key = self.get_api_key()
        
        if not credentials or not api_key:
            logger.warning("Firebase credentials or API key not found")
            return {}
        
        return {
            'apiKey': api_key,
            'authDomain': f"{credentials.get('project_id', '')}.firebaseapp.com",
            'projectId': credentials.get('project_id', ''),
            'storageBucket': f"{credentials.get('project_id', '')}.appspot.com",
            'messagingSenderId': credentials.get('client_id', '').split('-')[0] if credentials.get('client_id') else '',
            'appId': credentials.get('client_id', ''),
            'databaseURL': f"https://{credentials.get('project_id', '')}-default-rtdb.firebaseio.com"
        }
    
    def get_collection_name(self, collection_key: str) -> str:
        """Get collection name from settings"""
        return self.settings['firestore']['collections'].get(collection_key, collection_key)
    
    def get_auth_config(self) -> Dict[str, Any]:
        """Get authentication configuration"""
        return self.settings['auth']
    
    def get_storage_config(self) -> Dict[str, Any]:
        """Get storage configuration"""
        return self.settings['storage']
    
    def get_performance_config(self) -> Dict[str, Any]:
        """Get performance configuration"""
        return self.settings['performance']
    
    def is_development_mode(self) -> bool:
        """Check if in development mode"""
        return self.settings['development']['debug_mode']
    
    def get_security_rules(self) -> Dict[str, Any]:
        """Get security rules configuration"""
        return self.settings['security_rules']
    
    def update_setting(self, key_path: str, value: Any):
        """Update a specific setting using dot notation (e.g., 'auth.session_timeout')"""
        keys = key_path.split('.')
        current = self.settings
        
        for key in keys[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        
        current[keys[-1]] = value
        logger.info(f"Updated Firebase setting: {key_path} = {value}")
    
    def get_setting(self, key_path: str, default: Any = None) -> Any:
        """Get a specific setting using dot notation"""
        keys = key_path.split('.')
        current = self.settings
        
        try:
            for key in keys:
                current = current[key]
            return current
        except (KeyError, TypeError):
            return default
    
    def export_settings(self) -> Dict[str, Any]:
        """Export current settings (excluding sensitive data)"""
        safe_settings = self.settings.copy()
        # Remove sensitive information
        if 'service_account' in safe_settings:
            safe_settings['service_account'] = {'configured': True}
        return safe_settings
    
    def validate_configuration(self) -> Dict[str, bool]:
        """Validate Firebase configuration"""
        validation_results = {
            'credentials_available': bool(self.get_credentials_from_env()),
            'api_key_available': bool(self.get_api_key()),
            'web_config_valid': bool(self.get_web_config()),
            'collections_configured': bool(self.settings['firestore']['collections']),
            'auth_configured': bool(self.settings['auth']['sign_in_methods']),
            'storage_configured': bool(self.settings['storage']['allowed_file_types'])
        }
        
        validation_results['overall_valid'] = all(validation_results.values())
        return validation_results

# Global Firebase settings instance
firebase_settings = FirebaseSettings()

def get_firebase_settings() -> FirebaseSettings:
    """Get global Firebase settings instance"""
    return firebase_settings

def validate_firebase_setup() -> Dict[str, Any]:
    """Validate complete Firebase setup"""
    return firebase_settings.validate_configuration()

def get_firebase_web_config() -> Dict[str, str]:
    """Get Firebase web configuration for client-side usage"""
    return firebase_settings.get_web_config()
