
import os
import json
import logging
from datetime import datetime
from firebase_settings import firebase_settings
from firebase_config import firebase_config
from firebase_api_manager import firebase_api_manager

logger = logging.getLogger(__name__)

class FirebaseConfigViewer:
    """View and analyze Firebase database configurations"""
    
    def __init__(self):
        self.settings = firebase_settings
        self.config = firebase_config
        self.api_manager = firebase_api_manager
    
    def get_complete_configuration(self):
        """Get complete Firebase configuration overview"""
        try:
            config_overview = {
                'timestamp': datetime.now().isoformat(),
                'environment_variables': self._check_environment_variables(),
                'credentials_info': self._get_credentials_info(),
                'web_config': self._get_web_configuration(),
                'firestore_collections': self._get_firestore_collections(),
                'auth_configuration': self._get_auth_configuration(),
                'storage_configuration': self._get_storage_configuration(),
                'security_rules': self._get_security_rules(),
                'performance_settings': self._get_performance_settings(),
                'api_connectivity': self._test_api_connectivity(),
                'initialization_status': self._get_initialization_status(),
                'project_information': self._get_project_information()
            }
            
            return config_overview
            
        except Exception as e:
            logger.error(f"Error getting Firebase configuration: {str(e)}")
            return {'error': str(e)}
    
    def _check_environment_variables(self):
        """Check Firebase environment variables"""
        env_vars = {
            'FIREBASE_CREDENTIALS': {
                'present': bool(os.environ.get('FIREBASE_CREDENTIALS')),
                'valid_json': False,
                'length': 0
            },
            'FIREBASE_API_KEY': {
                'present': bool(os.environ.get('FIREBASE_API_KEY')),
                'length': len(os.environ.get('FIREBASE_API_KEY', ''))
            }
        }
        
        # Check if credentials are valid JSON
        if env_vars['FIREBASE_CREDENTIALS']['present']:
            try:
                creds_json = os.environ.get('FIREBASE_CREDENTIALS')
                json.loads(creds_json)
                env_vars['FIREBASE_CREDENTIALS']['valid_json'] = True
                env_vars['FIREBASE_CREDENTIALS']['length'] = len(creds_json)
            except json.JSONDecodeError:
                env_vars['FIREBASE_CREDENTIALS']['valid_json'] = False
        
        return env_vars
    
    def _get_credentials_info(self):
        """Get Firebase credentials information (sanitized)"""
        try:
            credentials = self.settings.get_credentials_from_env()
            if credentials:
                return {
                    'configured': True,
                    'project_id': credentials.get('project_id', 'Not found'),
                    'client_email': credentials.get('client_email', 'Not found'),
                    'client_id': credentials.get('client_id', 'Not found')[:10] + '...' if credentials.get('client_id') else 'Not found',
                    'auth_uri': credentials.get('auth_uri', 'Not found'),
                    'token_uri': credentials.get('token_uri', 'Not found'),
                    'type': credentials.get('type', 'Not found')
                }
            else:
                return {'configured': False, 'error': 'No credentials found'}
        except Exception as e:
            return {'configured': False, 'error': str(e)}
    
    def _get_web_configuration(self):
        """Get Firebase web configuration"""
        try:
            web_config = self.settings.get_web_config()
            if web_config:
                # Sanitize sensitive information
                sanitized_config = web_config.copy()
                if 'apiKey' in sanitized_config:
                    sanitized_config['apiKey'] = sanitized_config['apiKey'][:10] + '...' if sanitized_config['apiKey'] else 'Not configured'
                return sanitized_config
            else:
                return {'configured': False}
        except Exception as e:
            return {'error': str(e)}
    
    def _get_firestore_collections(self):
        """Get Firestore collection configuration"""
        try:
            collections = self.settings.get_setting('firestore.collections', {})
            indexes = self.settings.get_setting('firestore.indexes', {})
            
            return {
                'collections': collections,
                'indexes': indexes,
                'total_collections': len(collections) if collections else 0
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_auth_configuration(self):
        """Get Firebase Auth configuration"""
        try:
            auth_config = self.settings.get_auth_config()
            return {
                'sign_in_methods': auth_config.get('sign_in_methods', []),
                'password_policy': auth_config.get('password_policy', {}),
                'session_timeout': auth_config.get('session_timeout', 0),
                'max_sessions_per_user': auth_config.get('max_sessions_per_user', 0)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_storage_configuration(self):
        """Get Firebase Storage configuration"""
        try:
            storage_config = self.settings.get_storage_config()
            return {
                'bucket_name': storage_config.get('bucket_name', 'Not configured'),
                'max_file_size': storage_config.get('max_file_size', 0),
                'allowed_file_types': storage_config.get('allowed_file_types', []),
                'upload_paths': storage_config.get('upload_paths', {})
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_security_rules(self):
        """Get Firebase security rules configuration"""
        try:
            security_rules = self.settings.get_security_rules()
            return {
                'firestore': security_rules.get('firestore', {}),
                'user_isolation': security_rules.get('firestore', {}).get('user_isolation', False),
                'admin_override': security_rules.get('firestore', {}).get('admin_override', False),
                'rate_limiting': security_rules.get('firestore', {}).get('rate_limiting', {})
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_performance_settings(self):
        """Get Firebase performance settings"""
        try:
            performance = self.settings.get_performance_config()
            return {
                'cache_duration': performance.get('cache_duration', 0),
                'batch_size': performance.get('batch_size', 0),
                'connection_pool_size': performance.get('connection_pool_size', 0),
                'timeout_seconds': performance.get('timeout_seconds', 0)
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _test_api_connectivity(self):
        """Test Firebase API connectivity"""
        try:
            return self.api_manager.test_api_connectivity()
        except Exception as e:
            return {'error': str(e), 'overall_status': False}
    
    def _get_initialization_status(self):
        """Get Firebase initialization status"""
        try:
            return {
                'firebase_admin_initialized': self.config.initialized,
                'firestore_db_available': bool(self.config.db),
                'auth_module_available': bool(self.config.get_auth()),
                'api_key_configured': bool(self.config.api_key),
                'development_mode': self.settings.is_development_mode()
            }
        except Exception as e:
            return {'error': str(e)}
    
    def _get_project_information(self):
        """Get Firebase project information"""
        try:
            credentials = self.settings.get_credentials_from_env()
            if credentials:
                return {
                    'project_id': credentials.get('project_id', 'Unknown'),
                    'project_number': credentials.get('project_number', 'Unknown'),
                    'service_account_email': credentials.get('client_email', 'Unknown'),
                    'database_url': f"https://{credentials.get('project_id', 'unknown')}-default-rtdb.firebaseio.com",
                    'storage_bucket': f"{credentials.get('project_id', 'unknown')}.appspot.com",
                    'auth_domain': f"{credentials.get('project_id', 'unknown')}.firebaseapp.com"
                }
            else:
                return {'error': 'No project information available'}
        except Exception as e:
            return {'error': str(e)}
    
    def display_configuration(self):
        """Display configuration in a readable format"""
        config = self.get_complete_configuration()
        
        print("🔥 FIREBASE DATABASE CONFIGURATION OVERVIEW")
        print("=" * 60)
        print(f"📅 Generated: {config.get('timestamp', 'Unknown')}")
        print()
        
        # Environment Variables
        print("🔧 ENVIRONMENT VARIABLES:")
        env_vars = config.get('environment_variables', {})
        for var_name, var_info in env_vars.items():
            status = "✅" if var_info.get('present') else "❌"
            print(f"  {status} {var_name}: {'Present' if var_info.get('present') else 'Missing'}")
            if var_info.get('present'):
                if var_name == 'FIREBASE_CREDENTIALS':
                    print(f"    - Valid JSON: {'✅' if var_info.get('valid_json') else '❌'}")
                print(f"    - Length: {var_info.get('length', 0)} characters")
        print()
        
        # Project Information
        print("📋 PROJECT INFORMATION:")
        project_info = config.get('project_information', {})
        if 'error' not in project_info:
            print(f"  • Project ID: {project_info.get('project_id', 'Unknown')}")
            print(f"  • Service Account: {project_info.get('service_account_email', 'Unknown')}")
            print(f"  • Database URL: {project_info.get('database_url', 'Unknown')}")
            print(f"  • Storage Bucket: {project_info.get('storage_bucket', 'Unknown')}")
            print(f"  • Auth Domain: {project_info.get('auth_domain', 'Unknown')}")
        else:
            print(f"  ❌ Error: {project_info.get('error', 'Unknown error')}")
        print()
        
        # Initialization Status
        print("🚀 INITIALIZATION STATUS:")
        init_status = config.get('initialization_status', {})
        if 'error' not in init_status:
            for key, value in init_status.items():
                status = "✅" if value else "❌"
                print(f"  {status} {key.replace('_', ' ').title()}: {value}")
        else:
            print(f"  ❌ Error: {init_status.get('error', 'Unknown error')}")
        print()
        
        # Firestore Collections
        print("🗄️ FIRESTORE COLLECTIONS:")
        collections = config.get('firestore_collections', {})
        if 'error' not in collections:
            collection_list = collections.get('collections', {})
            print(f"  Total Collections: {collections.get('total_collections', 0)}")
            for key, collection_name in collection_list.items():
                print(f"    • {key}: {collection_name}")
        else:
            print(f"  ❌ Error: {collections.get('error', 'Unknown error')}")
        print()
        
        # Authentication Configuration
        print("🔐 AUTHENTICATION CONFIGURATION:")
        auth_config = config.get('auth_configuration', {})
        if 'error' not in auth_config:
            print(f"  • Sign-in Methods: {', '.join(auth_config.get('sign_in_methods', []))}")
            print(f"  • Session Timeout: {auth_config.get('session_timeout', 0)} seconds")
            print(f"  • Max Sessions per User: {auth_config.get('max_sessions_per_user', 0)}")
            
            password_policy = auth_config.get('password_policy', {})
            print("  • Password Policy:")
            for policy_key, policy_value in password_policy.items():
                print(f"    - {policy_key.replace('_', ' ').title()}: {policy_value}")
        else:
            print(f"  ❌ Error: {auth_config.get('error', 'Unknown error')}")
        print()
        
        # API Connectivity
        print("🌐 API CONNECTIVITY:")
        api_test = config.get('api_connectivity', {})
        if 'error' not in api_test:
            print(f"  Overall Status: {'✅ Connected' if api_test.get('overall_status') else '❌ Issues Detected'}")
            tests = api_test.get('tests', {})
            for test_name, test_result in tests.items():
                if test_name.endswith('_error'):
                    continue
                status = "✅" if test_result else "❌"
                print(f"  {status} {test_name.replace('_', ' ').title()}: {test_result}")
        else:
            print(f"  ❌ Error: {api_test.get('error', 'Unknown error')}")
        print()
        
        # Performance Settings
        print("⚡ PERFORMANCE SETTINGS:")
        performance = config.get('performance_settings', {})
        if 'error' not in performance:
            for key, value in performance.items():
                print(f"  • {key.replace('_', ' ').title()}: {value}")
        else:
            print(f"  ❌ Error: {performance.get('error', 'Unknown error')}")
        
        print("=" * 60)
        
        return config

# Create global instance
firebase_config_viewer = FirebaseConfigViewer()

def display_firebase_configuration():
    """Display Firebase configuration"""
    return firebase_config_viewer.display_configuration()

def get_firebase_configuration_json():
    """Get Firebase configuration as JSON"""
    return firebase_config_viewer.get_complete_configuration()

if __name__ == "__main__":
    display_firebase_configuration()
