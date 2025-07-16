# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

# Ensure PostgreSQL configuration
def configure_database(app):
    """Configure database to use PostgreSQL exclusively"""

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
        print("✅ Configured PostgreSQL database for authentication")
        return True
    except Exception as e:
        print(f"❌ Error configuring PostgreSQL: {str(e)}")
        return False