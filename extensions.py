
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
import os

# Initialize extensions
db = SQLAlchemy()
login_manager = LoginManager()

def configure_database(app, use_postgresql=True):
    """Configure PostgreSQL database"""
    if use_postgresql:
        return configure_postgresql(app)
    else:
        return configure_sqlite(app)

def configure_postgresql(app):
    """Configure PostgreSQL as primary database"""
    try:
        database_url = os.environ.get('DATABASE_URL')
        if not database_url:
            print("❌ ERROR: DATABASE_URL not found!")
            print("Please set up PostgreSQL database in Replit:")
            print("1. Go to Database tab in Replit")
            print("2. Click 'Create a database'")
            print("3. The DATABASE_URL will be automatically set")
            return False

        app.config['SQLALCHEMY_DATABASE_URI'] = database_url
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_size': 10,
            'pool_recycle': 120,
            'pool_pre_ping': True
        }
        
        db.init_app(app)
        print("✅ Configured PostgreSQL as primary database")
        return True

    except Exception as e:
        print(f"❌ Error configuring PostgreSQL: {str(e)}")
        return False

def configure_sqlite(app):
    """Configure SQLite as fallback database"""
    try:
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///inventory.db'
        app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
        
        db.init_app(app)
        print("✅ Configured SQLite as fallback database")
        return True

    except Exception as e:
        print(f"❌ Error configuring SQLite: {str(e)}")
        return False
