import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix
from config import config

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s: %(message)s'
)

logger = logging.getLogger(__name__)

class Base(DeclarativeBase):
    pass

# Initialize extensions
db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
mail = Mail()

def create_app(config_name=None):
    """Application factory pattern for production deployment"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    app = Flask(__name__)
    
    # Load configuration
    app.config.from_object(config.get(config_name, config['default']))
    
    # Security middleware
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)
    
    # Configure Flask-Login
    login_manager.login_view = 'postgresql_auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    return app

# Create application instance
app = create_app()
mail = Mail(app)

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

with app.app_context():
    # Import models to ensure they are registered
    import models  # noqa: F401
    
    # Register admin portal blueprint
    from admin_portal import admin_bp
    app.register_blueprint(admin_bp)
    
    # Register SMS routes blueprint
    from routes_sms import sms_bp
    app.register_blueprint(sms_bp)
    
    db.create_all()
    logging.info("Database tables created successfully")

# Import language utilities and set up translation system
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
app.jinja_env.filters['profit_margin'] = lambda cost, selling: format_profit_margin(cost, selling)
