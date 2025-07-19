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
            if self.initialized:
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
            except json.JSONDecodeError as e:
                logger.error(f"Invalid Firebase credentials JSON: {e}")
                return False

            # Check if Firebase is already initialized
            try:
                firebase_admin.get_app()
                logger.info("Firebase app already initialized")
            except ValueError:
                # Initialize Firebase Admin SDK if not already initialized
                self.app = firebase_admin.initialize_app(cred)
                logger.info("Firebase Admin SDK initialized")

            # Initialize Firestore
            self.db = firestore.client()
            
            # Verify Auth is available
            try:
                from firebase_admin import auth
                # Test auth availability
                if hasattr(auth, 'get_user'):
                    logger.info("✅ Firebase Auth is properly initialized and accessible")
                else:
                    logger.warning("⚠️ Firebase Auth module loaded but methods not accessible")
            except Exception as e:
                logger.error(f"❌ Firebase Auth initialization issue: {str(e)}")

            self.initialized = True
            logger.info("✅ Firebase initialized successfully")
            return True

        except Exception as e:
            logger.error(f"❌ Failed to initialize Firebase: {str(e)}")
            return False

    def get_db(self):
        """Get Firestore database instance"""
        if not self.initialized:
            self.initialize_firebase()
        return self.db

    def get_auth(self):
        """Get Firebase Auth instance"""
        if not self.initialized:
            if not self.initialize_firebase():
                return None
        
        try:
            from firebase_admin import auth
            # Test auth functionality by attempting to get the auth module
            # This ensures auth is properly initialized
            try:
                # Try to access a basic auth function to verify it's working
                if hasattr(auth, 'get_user') and hasattr(auth, 'create_user'):
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