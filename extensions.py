# extensions.py
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

# Ensure PostgreSQL configuration
def configure_database(app):
    """Configure PostgreSQL database settings"""
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')

    if database_url:
        # Ensure we're using PostgreSQL
        if database_url.startswith('postgres://'):
            database_url = database_url.replace('postgres://', 'postgresql://', 1)

        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_pre_ping': True,
            'pool_recycle': 300,
            'echo': False
        }

        print(f"✅ Configured PostgreSQL database")
    else:
        print("❌ DATABASE_URL not found in environment variables")

    return app