import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from werkzeug.middleware.proxy_fix import ProxyFix
from dotenv import load_dotenv

from extensions import db, Base

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.DEBUG)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

from manage import register_commands
register_commands(app)

# Configure database
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL")
app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True,
}
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Configure mail
app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", 587))
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USE_SSL"] = False
app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
app.config["MAIL_DEFAULT_SENDER"] = "info@mauzotz.com"

# Initialize extensions
db.init_app(app)
mail = Mail(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'postgresql_auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return User.query.get(int(user_id))

# App context setup
with app.app_context():
    import models  # Ensure models are loaded
    from admin_portal import admin_bp
    from auth import auth_bp

    app.register_blueprint(admin_bp)
    app.register_blueprint(auth_bp)

    db.create_all()
    logging.info("Database tables created successfully")

# Filters & pre-request hooks
from language_utils import init_language_context, translate_filter
from currency_utils import format_currency, format_currency_input, format_profit_margin

@app.before_request
def before_request():
    init_language_context()

app.jinja_env.filters['t'] = translate_filter
app.jinja_env.filters['currency'] = format_currency
app.jinja_env.filters['currency_input'] = format_currency_input
app.jinja_env.filters['profit_margin'] = lambda cost, selling: format_profit_margin(cost, selling)

@app.route('/routes')
def list_routes():
    output = []
    for rule in app.url_map.iter_rules():
        methods = ','.join(rule.methods)
        line = f"{rule.endpoint}: {rule.rule} [{methods}]"
        output.append(line)
    return '<br>'.join(output)
