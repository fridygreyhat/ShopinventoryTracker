# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

# Database configuration options
def configure_database(app, use_firebase=True):
    """Configure database - Firebase only"""

    # Force Firebase usage only
    return configure_firebase(app)

def configure_firebase(app):
    """Configure Firebase as primary database"""
    try:
        from firebase_config import firebase_config

        # Check for Firebase credentials
        firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
        if not firebase_creds:
            print("❌ ERROR: FIREBASE_CREDENTIALS not found!")
            print("Please add your Firebase service account JSON to environment variables:")
            print("1. Go to Firebase Console > Project Settings > Service Accounts")
            print("2. Generate new private key")
            print("3. Copy the JSON content to FIREBASE_CREDENTIALS environment variable")
            raise Exception("Firebase credentials are required")

        # Initialize Firebase
        if firebase_config.initialize_firebase():
            print("✅ Configured Firebase as primary database")
            app.config['USE_FIREBASE'] = True
            # Disable SQLAlchemy completely
            app.config['SQLALCHEMY_DATABASE_URI'] = None
            app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
            return True
        else:
            raise Exception("Failed to initialize Firebase")

    except Exception as e:
        print(f"❌ Error configuring Firebase: {str(e)}")
        return False