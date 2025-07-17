# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

# Database configuration options
def configure_database(app, use_firebase=True):
    """Configure database - Firebase or PostgreSQL fallback"""
    
    if use_firebase:
        return configure_firebase(app)
    else:
        return configure_postgresql(app)

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
            return True
        else:
            raise Exception("Failed to initialize Firebase")

    except Exception as e:
        print(f"❌ Error configuring Firebase: {str(e)}")
        return False

def configure_postgresql(app):
    """Configure PostgreSQL database"""

    # Check for PostgreSQL configuration
    postgres_url = os.environ.get('DATABASE_URL')
    if not postgres_url:
        # PostgreSQL is required - no fallback
        print("❌ ERROR: PostgreSQL DATABASE_URL not found!")
        print("Please set up PostgreSQL database in Replit:")
        print("1. Open a new tab and type 'Database'")
        print("2. Click 'create a database'")
        print("3. This will set the DATABASE_URL environment variable")
        raise Exception("PostgreSQL DATABASE_URL is required")

    try:
        # Use PostgreSQL with optimized settings
        app.config['SQLALCHEMY_DATABASE_URI'] = postgres_url
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'pool_timeout': 20,
            'max_overflow': 0,
            'connect_args': {
                'sslmode': 'prefer',
                'connect_timeout': 10
            }
        }
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['USE_FIREBASE'] = False
        print("✅ Configured PostgreSQL database for authentication")
        return True
    except Exception as e:
        print(f"❌ Error configuring PostgreSQL: {str(e)}")
        return False