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
        self.api_key = None

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
    @property
    def api_key(self):
        """Get Firebase API key for REST API calls"""
        # Use the API key from your Firebase config
        return "AIzaSyBc8dD1OwzxWJrf-bAxowOtYj-OHZr2epo"

# Global Firebase instance
firebase_config = FirebaseConfig()

def get_firestore_db():
    """Helper function to get Firestore database"""
    return firebase_config.get_db()

def get_firebase_auth():
    """Helper function to get Firebase Auth"""
    return firebase_config.get_auth()