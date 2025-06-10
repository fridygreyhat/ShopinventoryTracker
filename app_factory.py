"""
Flask application factory
"""
import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
mail = Mail()

def create_app(config_name='development'):
    """Create Flask application using factory pattern"""
    app = Flask(__name__)
    
    # Configure application
    configure_app(app, config_name)
    
    # Initialize extensions
    initialize_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Register template filters
    register_template_filters(app)
    
    # Register request handlers
    register_request_handlers(app)
    
    # Create database tables
    create_database_tables(app)
    
    return app

def configure_app(app, config_name):
    """Configure Flask application"""
    # Basic configuration
    app.secret_key = os.environ.get("SESSION_SECRET") or 'dev-secret-key'
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Database configuration
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        'pool_pre_ping': True,
        "pool_recycle": 300,
    }
    
    # Mail configuration
    app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', '587'))
    app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
    app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
    app.config['MAIL_DEFAULT_SENDER'] = ('MauzoTZ Notifications', 'info@mauzotz.com')
    
    # Application settings
    app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
    app.config['UPLOAD_FOLDER'] = 'static/uploads'

def initialize_extensions(app):
    """Initialize Flask extensions"""
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configure Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))

def register_blueprints(app):
    """Register application blueprints"""
    # Import and register auth blueprint
    from auth import auth_bp
    app.register_blueprint(auth_bp, url_prefix='/auth')
    
    # Import and register admin blueprint
    from admin_portal import admin_bp
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    # Import and register SMS blueprint
    from routes_sms import sms_bp
    app.register_blueprint(sms_bp, url_prefix='/sms')
    
    # Import and register language blueprint
    from language_routes import language_bp
    app.register_blueprint(language_bp, url_prefix='/language')

def register_template_filters(app):
    """Register Jinja2 template filters"""
    from currency_utils import format_currency, format_currency_input, format_profit_margin
    from language_utils import translate_filter
    
    app.jinja_env.filters['t'] = translate_filter
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['currency_input'] = format_currency_input
    app.jinja_env.filters['profit_margin'] = format_profit_margin

def register_request_handlers(app):
    """Register request handlers"""
    @app.before_request
    def before_request():
        from language_utils import init_language_context
        init_language_context()

def create_database_tables(app):
    """Create database tables"""
    with app.app_context():
        try:
            # Import all models to ensure they are registered
            import models
            db.create_all()
            logger.info("Database tables created successfully")
        except Exception as e:
            logger.error(f"Error creating database tables: {str(e)}")

# Create app instance for backward compatibility
app = create_app()