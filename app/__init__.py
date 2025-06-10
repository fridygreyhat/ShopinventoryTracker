"""
Flask application package initialization
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

def create_app(config_name=None):
    """Application factory pattern"""
    app = Flask(__name__)
    
    # Load configuration
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    from config import config
    app.config.from_object(config.get(config_name, config['default']))
    
    # Add proxy fix for deployment
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configure Flask-Login
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    @login_manager.user_loader
    def load_user(user_id):
        from app.models.user import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.routes.main import main_bp
    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.sms import sms_bp
    from app.routes.language import language_bp
    
    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(sms_bp, url_prefix='/sms')
    app.register_blueprint(language_bp, url_prefix='/language')
    
    # Register template filters
    from app.utils.currency import format_currency, format_currency_input, format_profit_margin
    from app.utils.language import translate_filter
    
    app.jinja_env.filters['t'] = translate_filter
    app.jinja_env.filters['currency'] = format_currency
    app.jinja_env.filters['currency_input'] = format_currency_input
    app.jinja_env.filters['profit_margin'] = format_profit_margin
    
    # Register request handlers
    @app.before_request
    def before_request():
        from app.utils.language import init_language_context
        init_language_context()
    
    # Create database tables
    with app.app_context():
        # Import all models to ensure they are registered
        from app.models import user, inventory, sales, financial, location, customer
        db.create_all()
        logger.info("Database tables created successfully")
    
    return app