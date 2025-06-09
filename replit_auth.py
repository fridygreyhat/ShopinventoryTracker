import os
import jwt
import uuid
from functools import wraps
from urllib.parse import urlencode
from flask import Blueprint, session, redirect, url_for, request, current_app, render_template, g
from flask_dance.consumer import OAuth2ConsumerBlueprint, oauth_authorized, oauth_error
from flask_dance.consumer.storage import BaseStorage
from flask_login import LoginManager, login_user, logout_user, current_user
from oauthlib.oauth2.rfc6749.errors import InvalidGrantError
from sqlalchemy.exc import NoResultFound
from werkzeug.local import LocalProxy
from app import app, db
from models import User

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'replit_auth.login'

# Create Replit OAuth blueprint
replit_auth = Blueprint('replit_auth', __name__, url_prefix='/auth')

# OAuth storage model
class OAuth(db.Model):
    __tablename__ = 'oauth'
    id = db.Column(db.Integer, primary_key=True)
    provider = db.Column(db.String(50), nullable=False)
    provider_user_id = db.Column(db.String(256), nullable=False)
    token = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.String, db.ForeignKey('users.id'), nullable=False)
    browser_session_key = db.Column(db.String, nullable=False)
    user = db.relationship("User")

# User session storage for OAuth tokens
class UserSessionStorage(BaseStorage):
    def get(self, blueprint):
        try:
            token = db.session.query(OAuth).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
            ).one().token
        except (NoResultFound, AttributeError):
            token = None
        return token

    def set(self, blueprint, token):
        if hasattr(current_user, 'get_id') and current_user.get_id():
            db.session.query(OAuth).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
            ).delete()
            new_oauth = OAuth(
                user_id=current_user.get_id(),
                browser_session_key=g.browser_session_key,
                provider=blueprint.name,
                token=token
            )
            db.session.add(new_oauth)
            db.session.commit()

    def delete(self, blueprint):
        if hasattr(current_user, 'get_id') and current_user.get_id():
            db.session.query(OAuth).filter_by(
                user_id=current_user.get_id(),
                browser_session_key=g.browser_session_key,
                provider=blueprint.name
            ).delete()
            db.session.commit()

# Get Replit configuration
def get_replit_config():
    try:
        repl_id = os.environ['REPL_ID']
    except KeyError:
        raise SystemExit("REPL_ID environment variable must be set")
    
    issuer_url = os.environ.get('ISSUER_URL', "https://replit.com/oidc")
    
    return repl_id, issuer_url

# Create Replit OAuth blueprint
def make_replit_blueprint():
    repl_id, issuer_url = get_replit_config()
    
    replit_bp = OAuth2ConsumerBlueprint(
        "replit_auth",
        __name__,
        client_id=repl_id,
        client_secret=None,
        base_url=issuer_url,
        authorization_url_params={
            "prompt": "login consent",
        },
        token_url=issuer_url + "/token",
        token_url_params={
            "auth": (),
            "include_client_id": True,
        },
        auto_refresh_url=issuer_url + "/token",
        auto_refresh_kwargs={
            "client_id": repl_id,
        },
        authorization_url=issuer_url + "/auth",
        use_pkce=True,
        code_challenge_method="S256",
        scope=["openid", "profile", "email", "offline_access"],
        storage=UserSessionStorage(),
    )
    
    @replit_bp.before_app_request
    def set_applocal_session():
        if '_browser_session_key' not in session:
            session['_browser_session_key'] = uuid.uuid4().hex
        session.modified = True
        g.browser_session_key = session['_browser_session_key']
        g.flask_dance_replit = replit_bp.session
    
    return replit_bp

# Create the blueprint
replit_bp = make_replit_blueprint()

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)

def save_user(user_claims):
    user = User()
    user.id = user_claims['sub']
    user.email = user_claims.get('email')
    user.first_name = user_claims.get('first_name')
    user.last_name = user_claims.get('last_name')
    user.profile_image_url = user_claims.get('profile_image_url')
    merged_user = db.session.merge(user)
    db.session.commit()
    return merged_user

@replit_bp.route("/logout")
def logout():
    repl_id, issuer_url = get_replit_config()
    del replit_bp.token
    logout_user()

    end_session_endpoint = issuer_url + "/session/end"
    encoded_params = urlencode({
        "client_id": repl_id,
        "post_logout_redirect_uri": request.url_root,
    })
    logout_url = f"{end_session_endpoint}?{encoded_params}"

    return redirect(logout_url)

@replit_bp.route("/error")
def error():
    return render_template("403.html"), 403

@oauth_authorized.connect
def logged_in(blueprint, token):
    user_claims = jwt.decode(token['id_token'], options={"verify_signature": False})
    user = save_user(user_claims)
    login_user(user)
    blueprint.token = token
    next_url = session.pop("next_url", None)
    if next_url is not None:
        return redirect(next_url)

@oauth_error.connect
def handle_error(blueprint, error, error_description=None, error_uri=None):
    return redirect(url_for('replit_auth.error'))

def require_login(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated:
            session["next_url"] = get_next_navigation_url(request)
            return redirect(url_for('replit_auth.login'))

        replit = LocalProxy(lambda: g.flask_dance_replit)
        expires_in = replit.token.get('expires_in', 0)
        if expires_in < 0:
            repl_id, issuer_url = get_replit_config()
            refresh_token_url = issuer_url + "/token"
            try:
                token = replit.refresh_token(token_url=refresh_token_url, client_id=repl_id)
            except InvalidGrantError:
                session["next_url"] = get_next_navigation_url(request)
                return redirect(url_for('replit_auth.login'))
            replit.token_updater(token)

        return f(*args, **kwargs)
    return decorated_function

def get_next_navigation_url(request):
    is_navigation_url = request.headers.get('Sec-Fetch-Mode') == 'navigate' and request.headers.get('Sec-Fetch-Dest') == 'document'
    if is_navigation_url:
        return request.url
    return request.referrer or request.url

# Register blueprints
app.register_blueprint(replit_bp, url_prefix="/auth")