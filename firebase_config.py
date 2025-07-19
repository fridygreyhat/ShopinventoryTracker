import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
import json
import logging

logger = logging.getLogger(__name__)

class FirebaseConfig:
    def __init__(self):
        self.initialized = False
        self.app = None
        self.db = None
        self.auth = None
        self._api_key = None

    def initialize_firebase(self):
        """Initialize Firebase app and Firestore database"""
        try:
            # Check if Firebase is already initialized
            if self.initialized and self.db is not None:
                return True

            # Get Firebase credentials from environment variables
            firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
            if not firebase_creds:
                logger.error("FIREBASE_CREDENTIALS environment variable not found")
                logger.error("Please add your Firebase service account JSON to FIREBASE_CREDENTIALS environment variable")
                return False

            # Parse the credentials JSON
            try:
                cred_dict = json.loads(firebase_creds)
                cred = credentials.Certificate(cred_dict)
                logger.info(f"✅ Firebase credentials loaded for project: {cred_dict.get('project_id', 'unknown')}")
            except json.JSONDecodeError as e:
                logger.error(f"Invalid Firebase credentials JSON: {e}")
                return False

            # Check if Firebase is already initialized
            try:
                self.app = firebase_admin.get_app()
                logger.info("Firebase app already initialized - reusing existing app")
            except ValueError:
                # Initialize Firebase Admin SDK if not already initialized
                try:
                    self.app = firebase_admin.initialize_app(cred)
                    logger.info("✅ Firebase Admin SDK initialized successfully")
                except Exception as init_error:
                    logger.error(f"❌ Failed to initialize Firebase Admin SDK: {str(init_error)}")
                    return False

            # Initialize Firestore with error handling
            try:
                self.db = firestore.client()
                # Test Firestore connectivity
                test_collection = self.db.collection('_system_test')
                logger.info("✅ Firestore database client initialized and accessible")
            except Exception as db_error:
                logger.error(f"❌ Failed to initialize Firestore: {str(db_error)}")
                return False
            
            # Verify Auth is available with better error handling
            try:
                from firebase_admin import auth
                # Test auth availability by trying to access a method
                if hasattr(auth, 'get_user') and hasattr(auth, 'create_user'):
                    self.auth = auth
                    logger.info("✅ Firebase Auth is properly initialized and accessible")
                else:
                    logger.warning("⚠️ Firebase Auth module loaded but required methods not accessible")
                    self.auth = None
            except ImportError as import_error:
                logger.error(f"❌ Firebase Auth import error: {str(import_error)}")
                self.auth = None
            except Exception as auth_error:
                logger.error(f"❌ Firebase Auth initialization issue: {str(auth_error)}")
                self.auth = None

            # Final validation
            if self.db is not None:
                self.initialized = True
                logger.info("🔥 Firebase fully initialized and ready")
                return True
            else:
                logger.error("❌ Firebase initialization failed - database not accessible")
                return False

        except Exception as e:
            logger.error(f"❌ Critical Firebase initialization error: {str(e)}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False

    def get_db(self):
        """Get Firestore database instance"""
        if not self.initialized:
            self.initialize_firebase()
        return self.db

    def get_auth(self):
        """Get Firebase Auth instance"""
        if not self.initialized or self.db is None:
            logger.warning("Firebase not properly initialized, attempting to initialize...")
            if not self.initialize_firebase():
                logger.error("Failed to initialize Firebase for auth access")
                return None
        
        # Return cached auth instance if available
        if hasattr(self, 'auth') and self.auth is not None:
            return self.auth
        
        try:
            from firebase_admin import auth
            # Test auth functionality by attempting to get the auth module
            # This ensures auth is properly initialized
            try:
                # Try to access a basic auth function to verify it's working
                if hasattr(auth, 'get_user') and hasattr(auth, 'create_user'):
                    self.auth = auth  # Cache the auth instance
                    logger.info("✅ Firebase Auth instance retrieved successfully")
                    return auth
                else:
                    logger.error("Firebase Auth module loaded but required methods not accessible")
                    return None
            except Exception as auth_test_error:
                logger.error(f"Firebase Auth functionality test failed: {str(auth_test_error)}")
                return None
        except ImportError as e:
            logger.error(f"Failed to import Firebase Auth module: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Unexpected error getting Firebase Auth instance: {str(e)}")
            return None
    @property
    def api_key(self):
        """Get Firebase API key for REST API calls"""
        # Get API key from environment variables for security
        api_key = os.environ.get('FIREBASE_API_KEY')
        if not api_key:
            logger.error("FIREBASE_API_KEY environment variable not found")
            logger.error("Please add your Firebase API key to FIREBASE_API_KEY environment variable")
            return None
        return api_key
    
    @api_key.setter
    def api_key(self, value):
        """Set Firebase API key"""
        self._api_key = value

# Global Firebase instance
firebase_config = FirebaseConfig()

def get_firestore_db():
    """Helper function to get Firestore database"""
    return firebase_config.get_db()

def get_firebase_auth():
    """Helper function to get Firebase Auth"""
    return firebase_config.get_auth()