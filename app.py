"""
Flask application with proper architecture and Python patterns
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

# Create the Flask application
app = Flask(__name__)

# Configure application
app.secret_key = os.environ.get("SESSION_SECRET") or 'dev-secret-key'
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

# Database configuration
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}

# Email configuration
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = os.environ.get("MAIL_USE_TLS", "true").lower() in [
    "true", "on", "1"
]
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = ("MauzoTZ Notifications", "info@mauzotz.com")

# Initialize the app with the extension
db.init_app(app)

# Initialize Flask-Login
login_manager.init_app(app)
login_manager.login_view = 'postgresql_auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Initialize Flask-Mail
mail.init_app(app)

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# Initialize language utilities and set up translation system
try:
    from language_utils import init_language_context, translate_filter
    from currency_utils import format_currency, format_currency_input, format_profit_margin
    
    @app.before_request
    def before_request():
        """Initialize language context before each request"""
        init_language_context()

    # Register filters for Jinja2 templates
    app.jinja_env.filters['t'] = translate_filter
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['currency_input'] = format_currency_input
    app.jinja_env.filters['profit_margin'] = format_profit_margin
    
    logger.info("Language and currency utilities initialized successfully")
except ImportError as e:
    logger.warning(f"Language or currency utilities could not be imported: {e}")

# Create database tables and register blueprints
with app.app_context():
    try:
        # Import models to ensure they are registered
        import models  # noqa: F401
        
        # Create all database tables
        db.create_all()
        logger.info("Database tables created successfully")
        
        # Register admin portal blueprint
        try:
            from admin_portal import admin_bp
            app.register_blueprint(admin_bp)
            logger.info("Admin portal blueprint registered")
        except ImportError as e:
            logger.warning(f"Admin portal blueprint could not be imported: {e}")
        
        # Register SMS routes blueprint
        try:
            from routes_sms import sms_bp
            app.register_blueprint(sms_bp)
            logger.info("SMS routes blueprint registered")
        except ImportError as e:
            logger.warning(f"SMS routes blueprint could not be imported: {e}")
            
    except Exception as e:
        logger.error(f"Error during application initialization: {str(e)}")
