
import firebase_admin
from firebase_admin import credentials, firestore, auth
import os
import json
import logging

logger = logging.getLogger(__name__)

class FirebaseConfig:
    def __init__(self):
        self.db = None
        self.app = None
        self.initialized = False

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
                return False

            # Parse the credentials JSON
            try:
                cred_dict = json.loads(firebase_creds)
                cred = credentials.Certificate(cred_dict)
            except json.JSONDecodeError as e:
                logger.error(f"Invalid Firebase credentials JSON: {e}")
                return False

            # Initialize Firebase Admin SDK
            self.app = firebase_admin.initialize_app(cred)
            
            # Initialize Firestore
            self.db = firestore.client()
            
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
            self.initialize_firebase()
        return auth

# Global Firebase instance
firebase_config = FirebaseConfig()

def get_firestore_db():
    """Helper function to get Firestore database"""
    return firebase_config.get_db()

def get_firebase_auth():
    """Helper function to get Firebase Auth"""
    return firebase_config.get_auth()
