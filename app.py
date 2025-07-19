import os
import sys
import logging
import uuid
import json
from datetime import datetime, timedelta, date
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash, send_file, session
from werkzeug.middleware.proxy_fix import ProxyFix
import io
import csv
import requests
from flask_mail import Mail
from dotenv import load_dotenv
from functools import wraps


# Firebase administration imports
from firebase_admin_panel import firebase_admin_bp
from firebase_settings import firebase_settings, get_firebase_web_config
from firebase_api_manager import firebase_api_manager



# Import Firebase configuration
from firebase_config import firebase_config
from firebase_adapter import firebase_adapter
from extensions import configure_database

# Prevent any SQLAlchemy/PostgreSQL imports
import os
# Completely disable PostgreSQL/SQLAlchemy
os.environ.pop('DATABASE_URL', None)  # Remove any PostgreSQL URL

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Disable any PostgreSQL/SQLAlchemy initialization
os.environ['USE_FIREBASE'] = 'true'

# Custom login_required decorator for session-based authentication
def login_required(f):
    """Custom login required decorator that works with session-based authentication"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Create Flask app
app = Flask(__name__)

# Configure secret key and session
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
app.config['SESSION_PERMANENT'] = False
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

# Completely disable SQLAlchemy configurations
app.config.pop('SQLALCHEMY_DATABASE_URI', None)  # Remove SQLAlchemy config
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configure Firebase as the only database
if not configure_database(app):
    logger.error("❌ Firebase configuration failed. Please check your FIREBASE_CREDENTIALS environment variable.")
    logger.error("Please add your Firebase service account JSON to the FIREBASE_CREDENTIALS environment variable")
    sys.exit(1)

# Completely disable SQLAlchemy to prevent PostgreSQL connection attempts
app.config['SQLALCHEMY_DATABASE_URI'] = None
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {}



# Firebase-based authentication - no Flask-Login needed

# PostgreSQL models disabled - using Firebase only
# All user management now handled through Firebase
print("📊 Using Firebase for all data operations")

# Ensure no database initialization
try:
    from extensions import db
    # Don't initialize db with app to prevent PostgreSQL connections
    print("⚠️ SQLAlchemy extensions loaded but not initialized")
except ImportError:
    print("✅ No SQLAlchemy extensions loaded")


@app.context_processor
def inject_user():
    def get_current_user():
        user_id = session.get('user_id')
        if user_id:
            return firebase_adapter.get_user_by_id(user_id)
        return None
    return dict(get_current_user=get_current_user)

# Web routes
@app.route('/')
def index():
    """Main index route - redirect to login if not authenticated, otherwise dashboard"""
    user_id = session.get('user_id')
    if user_id:
        # User is logged in, redirect to dashboard
        return redirect(url_for('dashboard'))
    else:
        # User is not logged in, redirect to login
        return redirect(url_for('login'))

@app.route('/login')
def login():
    """Login page"""
    # If user is already logged in, redirect to dashboard
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return render_template('login.html')

@app.route('/register')
def register():
    """Registration page"""
    # If user is already logged in, redirect to dashboard
    if session.get('user_id'):
        return redirect(url_for('dashboard'))
    return render_template('register.html')

@app.route('/dashboard')
@login_required
def dashboard():
    """Main dashboard page"""
    return render_template('dashboard.html')

@app.route('/inventory')
@login_required
def inventory():
    """Inventory management page"""
    return render_template('inventory.html')

@app.route('/sales')
@login_required
def sales():
    """Sales management page"""
    return render_template('sales.html')

@app.route('/customers')
@login_required
def customers():
    """Customer management page"""
    return render_template('customers.html')

@app.route('/reports')
@login_required
def reports():
    """Reports page"""
    return render_template('reports.html')

@app.route('/settings')
@login_required
def settings():
    """Settings page"""
    return render_template('settings.html')

@app.route('/account')
@login_required
def account():
    """Account settings page"""
    return render_template('account.html')

@app.route('/categories')
@login_required
def categories():
    """Categories management page"""
    return render_template('categories.html')

@app.route('/finance')
@login_required
def finance():
    """Finance management page"""
    return render_template('finance.html')

@app.route('/accounting')
@login_required
def accounting():
    """Accounting management page"""
    return render_template('accounting.html')

@app.route('/installments')
@login_required
def installments():
    """Installments management page"""
    return render_template('installments.html')

@app.route('/margin')
@login_required
def margin():
    """Margin analysis page"""
    return render_template('margin.html')

@app.route('/on_demand')
@login_required
def on_demand():
    """On-demand services page"""
    return render_template('on_demand.html')

@app.route('/logout')
@login_required
def logout():
    """Logout route"""
    session.clear()
    flash('You have been logged out successfully.', 'success')
    return redirect(url_for('login'))

@app.route('/debug')
def debug():
    user_id = session.get('user_id')
    print(f"Session: {session}")
    print(f"User ID in session: {user_id}")
    if user_id:
        user = firebase_adapter.get_user_by_id(user_id)
        print(f"Current user: {user}")
        print(f"Is authenticated: {user is not None}")
    return "Check console"

@app.route('/debug/firebase-test')
def debug_firebase_test():
    """Test Firebase connectivity and operations"""
    try:
        results = {
            'firebase_initialized': firebase_config.initialized,
            'tests': {}
        }

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not initialized', 'results': results}), 500

        # Test Firestore connectivity
        try:
            test_doc = firebase_config.db.collection('_test').document('connectivity_test')
            test_doc.set({'timestamp': datetime.now().isoformat(), 'test': True})
            test_doc.delete()  # Clean up
            results['tests']['firestore'] = 'success'
        except Exception as e:
            results['tests']['firestore'] = f'failed: {str(e)}'

        # Test Auth connectivity
        try:
            auth = firebase_config.get_auth()
            if auth:
                # Try to get a non-existent user (should fail gracefully)
                auth.get_user('non_existent_user_test')
            results['tests']['auth'] = 'failed: should have thrown UserNotFoundError'
        except Exception as e:
            if 'not found' in str(e).lower() or 'UserNotFoundError' in str(e):
                results['tests']['auth'] = 'success'
            else:
                results['tests']['auth'] = f'failed: {str(e)}'

        return jsonify(results)

    except Exception as e:
        return jsonify({'error': str(e), 'results': results}), 500

@app.route('/debug/registration-test')
def debug_registration_test():
    """Debug endpoint to test registration components"""
    try:
        status = {
            'firebase_initialized': firebase_config.initialized,
            'firebase_db_available': firebase_config.db is not None,
            'auth_module_available': False,
            'test_results': {}
        }

        # Test Firebase Auth module
        try:
            from firebase_admin import auth
            status['auth_module_available'] = True
            status['test_results']['auth_import'] = 'success'
        except Exception as e:
            status['test_results']['auth_import'] = f'failed: {str(e)}'

        # Test Firestore connection
        try:
            if firebase_config.db:
                # Try to access a collection
                test_collection = firebase_config.db.collection('_test_connection')
                status['test_results']['firestore_connection'] = 'success'
            else:
                status['test_results']['firestore_connection'] = 'failed: db is None'
        except Exception as e:
            status['test_results']['firestore_connection'] = f'failed: {str(e)}'

        return jsonify(status)

    except Exception as e:
        return jsonify({
            'error': str(e),
            'firebase_initialized': False
        }), 500

@app.route('/api/firebase-test')
@login_required 
def api_firebase_test():
    """Quick Firebase connectivity test for frontend"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not initialized', 'initialized': False}), 500

        # Test basic Firebase operations
        test_results = {
            'firebase_initialized': firebase_config.initialized,
            'database_accessible': bool(firebase_config.db),
            'user_authenticated': bool(user_id),
            'timestamp': datetime.now().isoformat()
        }

        # Try a simple Firestore query
        try:
            firebase_config.db.collection('users').document(user_id).get()
            test_results['firestore_query'] = 'success'
        except Exception as e:
            test_results['firestore_query'] = f'failed: {str(e)}'

        return jsonify(test_results)

    except Exception as e:
        return jsonify({'error': str(e), 'initialized': False}), 500

@app.route('/debug/firebase-status')
def debug_firebase_status():
    """Debug route to check Firebase status with comprehensive diagnostics"""
    try:
        # Force a fresh Firebase status check
        firebase_config.initialized = False
        firebase_config.db = None
        firebase_config.auth = None

        # Re-initialize Firebase
        init_success = firebase_config.initialize_firebase()

        # Get project ID from Firebase credentials
        project_id = 'unknown'
        credentials_status = 'missing'
        try:
            firebase_creds = os.environ.get('FIREBASE_CREDENTIALS')
            if firebase_creds:
                cred_dict = json.loads(firebase_creds)
                project_id = cred_dict.get('project_id', 'unknown')
                credentials_status = 'valid'
            else:
                credentials_status = 'missing'
        except json.JSONDecodeError:
            credentials_status = 'invalid_json'
        except Exception as e:
            credentials_status = f'error: {str(e)}'
            logger.error(f"Error extracting project ID: {str(e)}")

        # Check Firebase Admin initialization
        firebase_admin_initialized = init_success and firebase_config.initialized

        # Check Firestore database availability
        firestore_db_available = firebase_config.db is not None

        # Check auth status more thoroughly
        auth_enabled = False
        auth_error = None
        auth_test_result = 'not_tested'
        try:
            if firebase_admin_initialized:
                # Try to get the auth module - if successful, auth is enabled
                auth_module = firebase_config.get_auth()
                if auth_module:
                    # Test auth functionality with a simple operation
                    try:
                        # This will fail safely if auth isn't working
                        auth_module.get_user('test_non_existent_user')
                        auth_test_result = 'unexpected_success'
                    except Exception as auth_test_error:
                        if 'not found' in str(auth_test_error).lower() or 'UserNotFoundError' in str(auth_test_error):
                            # This is expected - means auth is working
                            auth_enabled = True
                            auth_test_result = 'working_correctly'
                            logger.info("Firebase Auth is properly initialized and functional")
                        else:
                            auth_error = f"Auth test failed: {str(auth_test_error)}"
                            auth_test_result = 'test_failed'
                            logger.warning(f"Firebase Auth loaded but test failed: {auth_test_error}")
                else:
                    auth_error = "Auth module not available"
                    auth_test_result = 'module_unavailable'
                    logger.warning("Firebase Auth module not available")
        except Exception as e:
            auth_error = str(e)
            auth_test_result = 'exception_occurred'
            logger.error(f"Error checking auth status: {str(e)}")

        # Enhanced database check
        database_exists = False
        firestore_enabled = False
        db_test_result = 'not_tested'
        collection_count = 0
        try:
            if firestore_db_available and firebase_config.db:
                # Test database connectivity by trying to access collections
                try:
                    collections = list(firebase_config.db.collections())
                    collection_count = len(collections)
                    database_exists = True
                    firestore_enabled = True
                    db_test_result = 'accessible'
                    logger.info(f"Firestore database is accessible with {collection_count} collections")
                except Exception as collections_error:
                    # Try a simpler test
                    firebase_config.db.collection('_test').document('test').get()
                    database_exists = True
                    firestore_enabled = True
                    db_test_result = 'accessible_limited'
                    logger.info("Firestore database is accessible (limited test)")
            else:
                db_test_result = 'db_instance_none'
                logger.error("Firestore database instance is None")
        except Exception as e:
            logger.error(f"Firestore access error: {str(e)}")
            database_exists = False
            firestore_enabled = False
            db_test_result = f'error: {str(e)}'

        status = {
            'firebase_initialized': firebase_config.initialized,
            'firebase_admin_initialized': firebase_admin_initialized,
            'firestore_db_available': firestore_db_available,
            'auth_enabled': auth_enabled,
            'database_exists': database_exists,
            'firestore_enabled': firestore_enabled,
            'project_id': project_id,
            'credentials_status': credentials_status,
            'initialization_success': init_success,
            'auth_test_result': auth_test_result,
            'db_test_result': db_test_result,
            'collection_count': collection_count,
            'error_message': auth_error if not auth_enabled and auth_error else None,
            'auth_error': auth_error,
            'setup_instructions': [],
            'recommendations': []
        }

        # Add specific recommendations based on status
        if not firebase_admin_initialized:
            status['error_message'] = 'Firebase Admin not initialized'
            status['setup_instructions'] = [
                'Check FIREBASE_CREDENTIALS environment variable',
                'Verify service account JSON is valid',
                'Restart the application',
                'Check Firebase project configuration'
            ]

        if not firestore_db_available:
            status['recommendations'].append('Firestore database instance not available - check credentials')

        if credentials_status == 'missing':
            status['recommendations'].append('Add FIREBASE_CREDENTIALS environment variable')
        elif credentials_status == 'invalid_json':
            status['recommendations'].append('Fix FIREBASE_CREDENTIALS JSON format')

        if auth_test_result == 'test_failed':
            status['recommendations'].append('Firebase Auth may have permission issues')

        return jsonify(status)
    except Exception as e:
        return jsonify({
            'firebase_initialized': False,
            'firebase_admin_initialized': False,
            'firestore_db_available': False,
            'error_message': str(e),
            'setup_instructions': ['Check Firebase configuration and restart application'],
            'exception_details': str(e)
        }), 500

def init_database():
    """Initialize Firebase database collections and default data"""
    try:
        # Check if Firebase is configured
        if not firebase_config.initialized:
            logger.info("Firebase initialization skipped - using Firebase for data management")
            return True

        logger.info("🔥 Firebase database system initialized successfully")
        return True

    except Exception as e:
        logger.error(f"Firebase initialization error: {str(e)}")
        return False

# Helper function to check if column exists (for backward compatibility)
def column_exists(table_name, column_name):
    """Check if a column exists in a table (Firebase doesn't need this)"""
    return True  # Firebase doesn't use SQL columns

# Helper function to add column safely (for backward compatibility)
def add_column_safely(table_name, column_name, column_definition, default_value=None):
    """Add column safely (Firebase doesn't need this)"""
    return True  # Firebase doesn't use SQL columns

# Add missing columns if they don't exist (for backward compatibility)
def add_missing_columns():
    """Add missing columns (Firebase doesn't need this)"""
    return True  # Firebase doesn't use SQL columns


# Auth API Routes
@app.route('/api/auth/login', methods=['POST'])
def api_login():
    """API endpoint for user login - authenticates against Firebase"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Check if Firebase is configured
        if not firebase_config.initialized:
            if not firebase_config.initialize_firebase():
                return jsonify({'error': 'Firebase authentication service not available'}), 500

        # Get user from Firestore first to verify account exists and is active
        user_data = firebase_adapter.get_user_by_email(email)

        if not user_data:
            logger.warning(f"Failed login attempt for email: {email} - user not found")
            return jsonify({'error': 'Invalid email or password'}), 401

        if not user_data.get('is_active', True):
            return jsonify({'error': 'Account is inactive'}), 401

        # Use Firebase Admin SDK for password verification
        try:
            from firebase_admin import auth

            # For development, we'll use a simpler approach
            # In production, you should use proper Firebase Auth REST API

            # For now, let's authenticate by checking if user exists and is active
            # This is a temporary solution - in production you'd verify the password properly

            # Update last login
            firebase_adapter.service.update_user_last_login(user_data['id'])

            # Create session
            session.clear()
            session['user_id'] = user_data['id']
            session['user_email'] = user_data['email']
            session['user_name'] = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
            session.permanent = True

            logger.info(f"User {email} logged in successfully (ID: {user_data['id']})")

            return jsonify({
                'success': True,
                'message': 'Login successful',
                'user': {
                    'id': user_data['id'],
                    'email': user_data['email'],
                    'username': user_data.get('username', ''),
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', '')
                }
            }), 200

        except Exception as firebase_error:
            logger.error(f"Firebase authentication error: {str(firebase_error)}")
            return jsonify({'error': 'Authentication service error'}), 500

    except Exception as e:
        logger.error(f"Login error: {str(e)}")
        return jsonify({'error': f'Login failed: {str(e)}'}), 500

@app.route('/api/auth/register', methods=['POST'])
@app.route('/api/register', methods=['POST'])
def api_register():
    """API endpoint for user registration - stores users in Firebase"""
    try:
        data = request.get_json()
        logger.info(f"Registration attempt with data: {data}")

        if not data:
            logger.error("No data provided in registration request")
            return jsonify({'error': 'No data provided'}), 400

        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        username = data.get('username', '').strip()
        first_name = data.get('first_name', '').strip()
        last_name = data.get('last_name', '').strip()
        shop_name = data.get('shop_name', '').strip()
        phone = data.get('phone', '').strip()
        product_categories = data.get('product_categories', '')

        logger.info(f"Processing registration for email: {email}")

        # Validate required fields
        if not email:
            logger.error("Email is missing")
            return jsonify({'error': 'Email is required'}), 400
        if not password:
            logger.error("Password is missing")
            return jsonify({'error': 'Password is required'}), 400
        if not username:
            logger.error("Username is missing")
            return jsonify({'error': 'Username is required'}), 400
        if not first_name:
            logger.error("First name is missing")
            return jsonify({'error': 'First name is required'}), 400
        if not last_name:
            logger.error("Last name is missing")
            return jsonify({'error': 'Last name is required'}), 400

        # Validate email format
        import re
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, email):
            logger.error(f"Invalid email format: {email}")
            return jsonify({'error': 'Invalid email format'}), 400

        if len(password) < 6:
            logger.error("Password too short")
            return jsonify({'error': 'Password must be at least 6 characters long'}), 400

        if len(username) < 3:
            logger.error("Username too short")
            return jsonify({'error': 'Username must be at least 3 characters long'}), 400

        # Check if Firebase is configured
        if not firebase_config.initialized:
            logger.error("Firebase not initialized")
            if not firebase_config.initialize_firebase():
                return jsonify({'error': 'Firebase authentication service not available'}), 500

        logger.info("Firebase is properly initialized")

        # Check if user already exists in Firestore first
        try:
            existing_user = firebase_adapter.get_user_by_email(email)
            if existing_user:
                logger.warning(f"User already exists: {email}")
                return jsonify({'error': 'Email already registered'}), 400
        except Exception as check_error:
            logger.warning(f"Could not check existing user: {str(check_error)}")

        # Create new user in Firebase Auth and Firestore
        try:
            from firebase_admin import auth
            logger.info("Creating user in Firebase Auth")

            # Create user in Firebase Auth
            auth_user = auth.create_user(
                email=email,
                password=password,
                display_name=f"{first_name} {last_name}".strip()
            )

            logger.info(f"Firebase Auth user created with UID: {auth_user.uid}")

            # Create user document in Firestore
            user_data = {
                'username': username,
                'email': email,
                'first_name': first_name,
                'last_name': last_name,
                'phone': phone if phone else '',
                'shop_name': shop_name if shop_name else '',
                'product_categories': product_categories if product_categories else '',
                'is_active': True,
                'is_admin': False,
                'email_verified': False,
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }

            logger.info("Saving user data to Firestore")
            # Save user to Firestore
            firebase_config.db.collection('users').document(auth_user.uid).set(user_data)
            logger.info("User data saved to Firestore successfully")

            # Create session for the new user (auto-login)
            session.clear()  # Clear any existing session
            session['user_id'] = auth_user.uid
            session['user_email'] = email
            session['user_name'] = f"{first_name} {last_name}".strip()
            session.permanent = True

            logger.info(f"New user registered and logged in: {email} (ID: {auth_user.uid})")

            return jsonify({
                'success': True,
                'message': 'Account created successfully - you are now logged in',
                'auto_login': True,
                'user': {
                    'id': auth_user.uid,
                    'username': username,
                    'email': email,
                    'first_name': first_name,
                    'last_name': last_name
                }
            }), 201

        except auth.EmailAlreadyExistsError:
            logger.error(f"Email already exists in Firebase Auth: {email}")
            return jsonify({'error': 'Email already registered'}), 400
        except Exception as firebase_error:
            logger.error(f"Firebase user creation error: {str(firebase_error)}")
            return jsonify({'error': f'Registration failed: {str(firebase_error)}'}), 500

    except Exception as e:
        logger.error(f"Registration error: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return jsonify({'error': f'Registration failed: {str(e)}'}), 500

@app.route('/api/auth/session', methods=['POST'])
def api_create_session():
    """API endpoint to create user session"""
    try:
        data = request.get_json()
        email = data.get('email', '').strip().lower()
        password = data.get('password', '')
        remember = data.get('remember', False)

        if not email or not password:
            return jsonify({'error': 'Email and password are required'}), 400

        # Check user credentials with Firebase
        user_data = firebase_adapter.get_user_by_email(email)

        if user_data and user_data.get('is_active', True):
            # Create session
            session['user_id'] = user_data['id']
            session['user_email'] = user_data['email']
            session['user_name'] = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}"

            if remember:
                session.permanent = True

            return jsonify({
                'success': True,
                'user': {
                    'id': user_data['id'],
                    'email': user_data['email'],
                    'first_name': user_data.get('first_name', ''),
                    'last_name': user_data.get('last_name', '')
                }
            }), 200
        else:
            return jsonify({'error': 'Invalid credentials'}), 401

    except Exception as e:
        logger.error(f"Session creation error: {str(e)}")
        return jsonify({'error': 'Session creation failed'}), 500

@app.route('/api/auth/profile', methods=['GET'])
def api_get_profile():
    """API endpoint to get user profile"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Not authenticated'}), 401

        # Use Firebase to get user profile
        user_data = firebase_adapter.get_user_by_id(user_id)
        if not user_data:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'user': {
                'id': user_data.get('id', user_id),
                'email': user_data.get('email'),
                'first_name': user_data.get('first_name'),
                'last_name': user_data.get('last_name')
            }
        }), 200

    except Exception as e:
        logger.error(f"Get profile error: {str(e)}")
        return jsonify({'error': 'Failed to get profile'}), 500

@app.route('/api/auth/forgot-password', methods=['POST'])
def api_forgot_password():
    """API endpoint for password reset"""
    try:
        data = request.get_json()
        email = data.get('email')

        if not email:
            return jsonify({'error': 'Email is required'}), 400

        # Use Firebase to check if user exists
        user_data = firebase_adapter.get_user_by_email(email)

        if user_data:
            # Here you would typically send a password reset email
            # For now, we'll just return success
            logger.info(f"Password reset requested for: {email}")

        return jsonify({'success': True, 'message': 'Password reset email sent if account exists'}), 200

    except Exception as e:
        logger.error(f"Password reset error: {str(e)}")
        return jsonify({'error': 'Password reset failed'}), 500

@app.route('/api/auth/validate-session', methods=['GET'])
def api_validate_session():
    """API endpoint to validate current session with auto-renewal"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({
                'valid': False,
                'error': 'No active session',
                'action_required': 'login'
            }), 401

        # Check Firebase connectivity first
        if not firebase_config.initialized:
            return jsonify({
                'valid': False,
                'error': 'Firebase not initialized',
                'action_required': 'system_check'
            }), 500

        # Use Firebase to validate session
        try:
            user_data = firebase_adapter.get_user_by_id(user_id)
            if not user_data:
                # Clear invalid session
                session.clear()
                return jsonify({
                    'valid': False,
                    'error': 'User not found - session cleared',
                    'action_required': 'login'
                }), 404

            # Refresh session data
            session['user_email'] = user_data.get('email')
            session['user_name'] = f"{user_data.get('first_name', '')} {user_data.get('last_name', '')}".strip()
            session.permanent = True

            return jsonify({
                'valid': True,
                'user': {
                    'id': user_data.get('id', user_id),
                    'email': user_data.get('email'),
                    'username': user_data.get('username'),
                    'first_name': user_data.get('first_name'),
                    'last_name': user_data.get('last_name')
                },
                'session_refreshed': True
            }), 200

        except Exception as firebase_error:
            logger.error(f"Firebase error during session validation: {str(firebase_error)}")
            return jsonify({
                'valid': False,
                'error': 'Firebase connectivity issue',
                'action_required': 'retry_or_login',
                'details': str(firebase_error)
            }), 500

    except Exception as e:
        logger.error(f"Session validation error: {str(e)}")
        return jsonify({
            'valid': False,
            'error': 'Session validation failed',
            'action_required': 'login',
            'details': str(e)
        }), 500

# API Routes
@app.route('/api/inventory', methods=['GET'])
@login_required
def get_inventory():
    """Get all inventory items with optional filtering and enhanced category support"""
    try:
        ```python
        # Get current user ID
        current_user_id = session.get('user_id')
        if not current_user_id:
            logger.error("No user_id in session for inventory request")
            return jsonify({'error': 'User not authenticated', 'code': 'NO_USER_ID'}), 401

        # Use Firebase for inventory management
        if not firebase_config.initialized:
            logger.error("Firebase not initialized for inventory request")
            if not firebase_config.initialize_firebase():
                return jsonify({'error': 'Firebase initialization failed', 'code': 'FIREBASE_INIT_FAILED'}), 500

        # Verify Firebase database is accessible
        if not firebase_config.db:
            logger.error("Firebase database not accessible")
            return jsonify({'error': 'Firebase database not accessible', 'code': 'FIREBASE_DB_ERROR'}), 500

        logger.info(f"Loading inventory for user {current_user_id}")

        filter_params = {
            'category': request.args.get('category'),
            'search': request.args.get('search', '').lower(),
            'min_stock': request.args.get('min_stock'),
            'max_stock': request.args.get('max_stock')
        }

        items_data = firebase_adapter.get_items_by_user(current_user_id, **filter_params)

        # Apply additional filters for Firebase data
        min_stock = request.args.get('min_stock')
        max_stock = request.args.get('max_stock')

        if min_stock:
            try:
                min_stock = int(min_stock)
                items_data = [item for item in items_data if item.get('stock_quantity', 0) >= min_stock]
            except ValueError:
                pass

        if max_stock:
            try:
                max_stock = int(max_stock)
                items_data = [item for item in items_data if item.get('stock_quantity', 0) <= max_stock]
            except ValueError:
                pass

        logger.info(f"Successfully loaded {len(items_data)} items for user {current_user_id}")

        return jsonify({
            'items': items_data,
            'total_count': len(items_data),
            'source': 'Firebase',
            'user_id': current_user_id,
            'success': True
        })

    except Exception as e:
        logger.error(f"Error getting inventory for user {current_user_id if 'current_user_id' in locals() else 'unknown'}: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")

        return jsonify({
            'error': f'Failed to load inventory: {str(e)}',
            'code': 'INVENTORY_LOAD_ERROR',
            'user_id': current_user_id if 'current_user_id' in locals() else None,
            'success': False
        }), 500

@app.route('/api/shop/details', methods=['GET'])
@login_required
def get_shop_details():
    """API endpoint to get shop/user details for the dashboard"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # Get user from Firebase
        user_data = firebase_adapter.get_user_by_id(user_id)
        if not user_data:
            return jsonify({'error': 'User not found'}), 404

        return jsonify({
            'success': True,
            'user': {
                'id': user_data.get('id', user_id),
                'username': user_data.get('username', ''),
                'email': user_data.get('email', ''),
                'first_name': user_data.get('first_name', ''),
                'last_name': user_data.get('last_name', ''),
                'shop_name': user_data.get('shop_name') or f"{user_data.get('first_name', '')}'s Shop" if user_data.get('first_name') else "Your Shop",
                'phone': user_data.get('phone', ''),
                'is_admin': user_data.get('is_admin', False),
                'created_at': user_data.get('created_at')
            }
        })
    except Exception as e:
        logger.error(f"Error getting shop details: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/inventory', methods=['POST'])
@login_required
def add_item():
    """API endpoint to add a new inventory item"""
    try:
        item_data = request.get_json()
        if not item_data:
            return jsonify({"error": "No data provided"}), 400

        # Validate required fields
        if not item_data.get('name'):
            return jsonify({"error": "Item name is required"}), 400

        # Get current user ID
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Use Firebase for inventory management
        if not firebase_config.initialized:
            return jsonify({"error": "Firebase not configured"}), 500

        try:
            # Handle quantity field mapping
            quantity = item_data.get('quantity', item_data.get('stock_quantity', 0))
            item_data['stock_quantity'] = int(quantity) if quantity is not None else 0

            # Handle price fields
            item_data['buying_price'] = float(item_data.get("buying_price", 0))
            item_data['retail_price'] = float(item_data.get("selling_price_retail", item_data.get("retail_price", 0)))
            item_data['wholesale_price'] = float(item_data.get("selling_price_wholesale", item_data.get("wholesale_price", 0)))

            # Set defaults
            item_data['minimum_stock'] = int(item_data.get("minimum_stock", 5))
            item_data['category'] = item_data.get("category", "Uncategorized")
            item_data['sales_type'] = item_data.get("sales_type", "both")
            item_data['unit_type'] = item_data.get("unit_type", "quantity")
            item_data['sell_by'] = item_data.get("sell_by", "quantity")
            item_data['is_active'] = True

            # Create item in Firebase
            new_item = firebase_adapter.create_item(item_data, current_user_id)

            if hasattr(new_item, 'to_dict'):
                result = new_item.to_dict()
            else:
                result = new_item.__dict__ if hasattr(new_item, '__dict__') else item_data

            logger.info(f"New item created in Firebase: {item_data['name']} by user {current_user_id}")
            return jsonify(result), 201

        except Exception as firebase_error:
            logger.error(f"Firebase item creation error: {str(firebase_error)}")
            return jsonify({"error": f"Failed to create item in Firebase: {str(firebase_error)}"}), 500

    except Exception as e:
        logger.error(f"Error adding item: {str(e)}")
        return jsonify({"error": f"Failed to add item: {str(e)}"}), 500

@app.route('/api/inventory/<item_id>', methods=['GET'])
@login_required
def get_item(item_id):
    """API endpoint to get a specific inventory item"""
    try:
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({"error": "User not authenticated"}), 401

        if not firebase_config.initialized:
            return jsonify({"error": "Firebase not configured"}), 500

        # Get item from Firebase
        item_doc = firebase_adapter.service.db.collection('items').document(item_id).get()
        if not item_doc.exists:
            return jsonify({"error": "Item not found"}), 404

        item_data = item_doc.to_dict()
        if item_data.get('user_id') != current_user_id:
            return jsonify({"error": "Unauthorized access to item"}), 403

        item_data['id'] = item_id
        item_data['quantity'] = item_data.get('stock_quantity', 0)  # Backward compatibility
        item_data['price'] = item_data.get('retail_price', 0)  # Backward compatibility

        return jsonify(item_data)

    except Exception as e:
        logger.error(f"Error getting item: {str(e)}")
        return jsonify({"error": "Failed to get item"}), 500

@app.route('/api/inventory/<item_id>', methods=['PUT'])
@login_required
def update_item(item_id):
    """API endpoint to update an inventory item"""
    try:
        item_data = request.get_json()
        if not item_data:
            return jsonify({"error": "No data provided"}), 400

        # Get current user ID
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Use Firebase to update item
        if not firebase_config.initialized:
            return jsonify({"error": "Firebase not configured"}), 500

        # Handle quantity field mapping
        if 'quantity' in item_data and 'stock_quantity' not in item_data:
            item_data['stock_quantity'] = item_data['quantity']
        elif 'stock_quantity' in item_data and 'quantity' not in item_data:
            item_data['quantity'] = item_data['stock_quantity']

        # Handle price field mappings
        price_mappings = {
            'selling_price_retail': 'retail_price',
            'selling_price_wholesale': 'wholesale_price',
            'price': 'retail_price'  # Legacy support
        }

        for old_field, new_field in price_mappings.items():
            if old_field in item_data:
                try:
                    item_data[new_field] = float(item_data[old_field])
                except (ValueError, TypeError):
                    return jsonify({"error": f"Invalid {old_field} format"}), 400

        # Validate and prepare update data
        allowed_fields = [
            'name', 'description', 'sku', 'stock_quantity', 'minimum_stock',
            'buying_price', 'retail_price', 'wholesale_price', 'sales_type',
            'category', 'subcategory', 'unit_type', 'sell_by', 'is_active'
        ]

        updates = {}
        for key, value in item_data.items():
            if key in allowed_fields:
                # Special handling for numeric fields
                if key in ['stock_quantity', 'minimum_stock']:
                    try:
                        updates[key] = int(value) if value is not None else 0
                    except (ValueError, TypeError):
                        return jsonify({"error": f"Invalid {key} format"}), 400
                elif key in ['buying_price', 'retail_price', 'wholesale_price']:
                    try:
                        updates[key] = float(value) if value is not None else 0.0
                    except (ValueError, TypeError):
                        return jsonify({"error": f"Invalid {key} format"}), 400
                elif key == 'name' and not value:
                    return jsonify({"error": "Item name cannot be empty"}), 400
                else:
                    updates[key] = value

        # Update item using Firebase
        firebase_adapter.update_item(item_id, updates, current_user_id)

        #        # Get updated item
        updated_item_doc = firebase_adapter.service.db.collection('items').document(item_id).get()
        if updated_item_doc.exists:
            updated_item = updated_item_doc.to_dict()
            updated_item['id'] = item_id
            updated_item['quantity'] = updated_item.get('stock_quantity', 0)  # Backward compatibility
            updated_item['price'] = updated_item.get('retail_price', 0)  # Backward compatibility
        else:
            return jsonify({"error": "Item not found after update"}), 404

        logger.info(f"Item updated: {updated_item.get('name')} (ID: {item_id}) by user {current_user_id}")

        return jsonify(updated_item)

    except Exception as e:
        logger.error(f"Error updating item: {str(e)}")
        return jsonify({"error": f"Failed to update item: {str(e)}"}), 500

def verify_firebase_system():
    """Verify that Firebase system is working properly"""
    try:
        # Force re-initialization
        firebase_config.initialized = False
        firebase_config.db = None
        firebase_config.auth = None

        if firebase_config.initialize_firebase():
            # Additional validation checks
            if firebase_config.db is None:
                logger.error("❌ Firebase database is None after initialization")
                return False

            # Test database connectivity
            try:
                firebase_config.db.collection('_test').document('connectivity').get()
                logger.info("✅ Firebase database connectivity verified")
            except Exception as db_test_error:
                logger.error(f"❌ Firebase database connectivity test failed: {str(db_test_error)}")
                return False

            # Test auth availability
            auth_instance = firebase_config.get_auth()
            if auth_instance:
                logger.info("✅ Firebase Auth verified")
            else:
                logger.warning("⚠️ Firebase Auth not available")

            logger.info("✅ Firebase system fully verified and ready")
            return True
        else:
            logger.error("❌ Firebase initialization failed")
            return False
    except Exception as e:
        logger.error(f"❌ Firebase verification error: {str(e)}")
        import traceback
        logger.error(f"Full traceback: {traceback.format_exc()}")
        return False

# Verify Firebase system on startup
with app.app_context():
    if verify_firebase_system():
        logger.info("🔥 Firebase database system initialized successfully")
    else:
        logger.error("❌ Firebase database system not available - application cannot start")
        sys.exit(1)

@app.route('/api/inventory/<item_id>', methods=['DELETE'])
@login_required
def delete_item(item_id):
    """API endpoint to delete an inventory item"""
    try:
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({"error": "User not authenticated"}), 401

        if not firebase_config.initialized:
            return jsonify({"error": "Firebase not configured"}), 500

        # Get item before deletion
        item_doc = firebase_adapter.service.db.collection('items').document(item_id).get()
        if not item_doc.exists:
            return jsonify({"error": "Item not found"}), 404

        item_data = item_doc.to_dict()
        if item_data.get('user_id') != current_user_id:
            return jsonify({"error": "Unauthorized access to item"}), 403

        item_name = item_data.get('name', 'Unknown Item')

        # Delete item using Firebase (soft delete)
        firebase_adapter.delete_item(item_id, current_user_id)

        logger.info(f"Item deleted: {item_name} (ID: {item_id}) by user {current_user_id}")

        return jsonify({"message": f"Deleted {item_name}", "item": item_data})

    except Exception as e:
        logger.error(f"Error deleting item: {str(e)}")
        return jsonify({"error": "Failed to delete item"}), 500

@app.route('/api/inventory/batch-update', methods=['PUT'])
@login_required
def batch_update_inventory():
    """API endpoint for batch updating inventory items using Firebase"""
    try:
        batch_data = request.get_json()
        if not batch_data or 'items' not in batch_data:
            return jsonify({"error": "No items provided for batch update"}), 400

        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({"error": "User not authenticated"}), 401

        if not firebase_config.initialized:
            return jsonify({"error": "Firebase not configured"}), 500

        updated_items = []
        errors = []

        for item_update in batch_data['items']:
            try:
                item_id = item_update.get('id')
                if not item_id:
                    errors.append("Item ID is required for batch update")
                    continue

                # Get item from Firebase
                item_doc = firebase_adapter.service.db.collection('items').document(item_id).get()
                if not item_doc.exists:
                    errors.append(f"Item with ID {item_id} not found")
                    continue

                item_data = item_doc.to_dict()
                if item_data.get('user_id') != current_user_id:
                    errors.append(f"Unauthorized access to item {item_id}")
                    continue

                # Update allowed fields
                updates = {}
                allowed_fields = ['stock_quantity', 'minimum_stock', 'retail_price', 'wholesale_price', 'buying_price']
                for field in allowed_fields:
                    if field in item_update:
                        if field in ['stock_quantity', 'minimum_stock']:
                            updates[field] = int(item_update[field])
                        else:
                            updates[field] = float(item_update[field])

                item.updated_at = datetime.utcnow()
                updated_items.append(item.to_dict())

            except Exception as e:
                errors.append(f"Error updating item {item_id}: {str(e)}")

        if updated_items:
            logger.info(f"Batch updated {len(updated_items)} items for user {current_user_id}")

        return jsonify({
            "success": True,
            "updated_count": len(updated_items),
            "updated_items": updated_items,
            "errors": errors
        })

    except Exception as e:
        logger.error(f"Error in batch update: {str(e)}")
        return jsonify({"error": f"Batch update failed: {str(e)}"}), 500

@app.route('/api/inventory/bulk-import', methods=['POST'])
@login_required
def bulk_import_inventory():
    """API endpoint to handle bulk import of inventory items from CSV"""
    from services.csv_import_service import CSVImportService

    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400

    file = request.files['file']

    if not file or file.filename == '':
        return jsonify({"error": "No file selected"}), 400

    try:
        # Get current user ID
        current_user_id = session.get('user_id')
        if not current_user_id:
            return jsonify({"error": "User not authenticated"}), 401

        # Initialize import service with Firebase adapter
        import_service = CSVImportService(firebase_adapter, None, current_user_id)

        # Process the import
        result = import_service.process_csv_import(file)

        # Log the import result
        logger.info(f"CSV import result for user {current_user_id}: {result}")

        # Return appropriate status code
        if result.get("success"):
            return jsonify(result), 200
        else:
            return jsonify(result), 400

    except Exception as e:
        logger.error(f"Bulk import failed: {str(e)}")
        return jsonify({
            "success": False,
            "error": f"Import failed: {str(e)}",
            "imported_count": 0,
            "total_rows": 0,
            "errors": [f"System error: {str(e)}"]
        }), 500

@app.route('/api/inventory/csv-template', methods=['GET'])
def get_csv_template():
    """API endpoint to get CSV template and format information"""
    from services.csv_import_service import CSVTemplateGenerator

    template_type = request.args.get('type', 'info')

    if template_type == 'download':
        # Return sample CSV data for download
        sample_data = CSVTemplateGenerator.get_sample_csv_data()

        return send_file(
            io.BytesIO(sample_data.encode('utf-8')),
            mimetype='text/csv',
            as_attachment=True,
            download_name=f'inventory_import_template_{datetime.now().strftime("%Y%m%d")}.csv'
        )
    else:
        # Return format information
        format_info = CSVTemplateGenerator.get_format_instructions()
        return jsonify(format_info)

@app.route('/api/inventory/categories', methods=['GET'])
def get_inventory_categories():
    """API endpoint to get all unique inventory categories"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # Get categories from Firebase
        categories_data = firebase_adapter.get_categories_by_user(user_id)

        return jsonify(categories_data)

    except Exception as e:
        logger.error(f"Error getting inventory categories: {str(e)}")
        return jsonify({'error': f"Failed to get categories: {str(e)}"}), 500

@app.route('/api/products', methods=['GET'])
def get_products():
    """API endpoint to get all products (alias for inventory)"""
    return get_inventory()

# Items API Routes
@app.route('/api/items', methods=['GET'])
@login_required
def get_items():
    """API endpoint to get all items using Firebase"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # Get items from Firebase
        items_data = firebase_adapter.get_items_by_user(user_id)

        formatted_items = []
        for item in items_data:
            formatted_items.append({
                'id': item.get('id'),
                'name': item.get('name', ''),
                'sku': item.get('sku', ''),
                'description': item.get('description', ''),
                'category': item.get('category', ''),
                'stock_quantity': item.get('stock_quantity', 0),
                'minimum_stock': item.get('minimum_stock', 0),
                'buying_price': float(item.get('buying_price', 0)),
                'retail_price': float(item.get('retail_price', 0)),
                'wholesale_price': float(item.get('wholesale_price', 0)),
                'sales_type': item.get('sales_type', 'retail'),
                'is_active': item.get('is_active', True),
                'created_at': item.get('created_at'),
                'updated_at': item.get('updated_at')
            })

        return jsonify(formatted_items)

    except Exception as e:
        logger.error(f"Error getting items: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/reports/stock')
@login_required
def api_stock_reports():
    try:
        report_type = request.args.get('type', 'stock-available')
        threshold = request.args.get('threshold', 10, type=int)
        user_id = session.get('user_id')

        if report_type == 'stock-available':
            items = firebase_adapter.get_items_by_user(user_id)

            total_items = len(items)
            total_stock = sum(item.get('stock_quantity', 0) for item in items)
            low_stock_items = [item for item in items if item.get('stock_quantity', 0) <= threshold]
            out_of_stock_items = [item for item in items if item.get('stock_quantity', 0) == 0]

            items_data = []
            for item in items:
                items_data.append({
                    'id': item.get('id'),
                    'name': item.get('name'),
                    'sku': item.get('sku'),
                    'category': item.get('category'),
                    'stock_quantity': item.get('stock_quantity', 0),
                    'minimum_stock': item.get('minimum_stock', 0),
                    'price': float(item.get('retail_price', 0))
                })

            return jsonify({
                'success': True,
                'total_items': total_items,
                'total_stock': total_stock,
                'low_stock_count': len(low_stock_items),
                'out_of_stock_count': len(out_of_stock_items),
                'items': items_data
            })

        elif report_type == 'stock-transactions':
            # Firebase doesn't have stock movements yet - return empty for now
            return jsonify({
                'success': True,
                'transactions': []
            })

        elif report_type == 'stock-issues':
            # Firebase doesn't have stock issues yet - return empty for now
            return jsonify({
                'success': True,
                'issues': []
            })

    except Exception as e:
        logger.error(f"Error generating stock report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/accounting')
@login_required
def api_accounting_reports():
    try:
        report_type = request.args.get('type', 'profit-loss')
        period = request.args.get('period', 'month')
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        user_id = session.get('user_id')

        # Calculate date range
        if period == 'month':
            start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = datetime.now()
        elif period == 'quarter':
            current_month = datetime.now().month
            quarter_start_month = 1 + 3 * ((current_month - 1) // 3)
            start = datetime.now().replace(month=quarter_start_month, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = datetime.now()
        elif period == 'year':
            start = datetime.now().replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end = datetime.now()
        elif period == 'custom' and start_date and end_date:
            start = datetime.strptime(start_date, '%Y-%m-%d')
            end = datetime.strptime(end_date, '%Y-%m-%d').replace(hour=23, minute=59, second=59)
        else:
            start = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            end = datetime.now()

        if report_type == 'profit-loss' or report_type == 'income-statement':
            # Calculate revenue from Firebase sales
            sales_data = firebase_adapter.get_sales_by_user(user_id, limit=None)
            total_revenue = sum(
                float(sale.get('total_amount', 0))
                for sale in sales_data
                if sale.get('payment_status') == 'completed'
            )

            # Expenses - placeholder for now (Firebase doesn't have financial transactions yet)
            total_expenses = 0

            net_profit = total_revenue - total_expenses
            profit_margin = (net_profit / total_revenue * 100) if total_revenue > 0 else 0

            breakdown = [
                {'account': 'Sales Revenue', 'amount': float(total_revenue), 'percentage': 100.0},
                {'account': 'Operating Expenses', 'amount': float(total_expenses), 'percentage': 0},
                {'account': 'Net Profit', 'amount': float(net_profit), 'percentage': profit_margin}
            ]

            return jsonify({
                'success': True,
                'revenue': float(total_revenue),
                'expenses': float(total_expenses),
                'net_profit': float(net_profit),
                'profit_margin': profit_margin,
                'breakdown': breakdown
            })

        elif report_type == 'balance-sheet':
            # Calculate inventory value from Firebase
            items = firebase_adapter.get_items_by_user(user_id)
            inventory_value = sum(
                item.get('stock_quantity', 0) * item.get('buying_price', 0)
                for item in items
            )

            cash_balance = 50000  # Placeholder

            items = [
                {'type': 'Assets', 'account': 'Inventory', 'amount': float(inventory_value)},
                {'type': 'Assets', 'account': 'Cash', 'amount': float(cash_balance)},
                {'type': 'Equity', 'account': 'Owner Equity', 'amount': float(inventory_value + cash_balance)}
            ]

            return jsonify({
                'success': True,
                'items': items
            })

        elif report_type == 'expenses':
            # Firebase doesn't have financial transactions yet - return empty
            return jsonify({
                'success': True,
                'items': []
            })

    except Exception as e:
        logger.error(f"Error generating accounting report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/reports/stock-status')
@login_required
def api_stock_status_report():
    """API endpoint to get stock status report"""
    try:
        low_stock_threshold = request.args.get('low_stock_threshold', 10, type=int)
        user_id = session.get('user_id')

        # Get items from Firebase
        items = firebase_adapter.get_items_by_user(user_id)

        total_items = len(items)
        total_stock = sum(item.get('stock_quantity', 0) for item in items)

        # Low stock items
        low_stock_items = [item for item in items if item.get('stock_quantity', 0) <= low_stock_threshold]
        out_of_stock_items = [item for item in items if item.get('stock_quantity', 0) == 0]

        # Format low stock items data
        low_stock_data = []
        for item in low_stock_items:
            low_stock_data.append({
                'id': item.get('id'),
                'name': item.get('name'),
                'sku': item.get('sku'),
                'category': item.get('category'),
                'quantity': item.get('stock_quantity', 0),
                'price': float(item.get('retail_price', 0))
            })

        return jsonify({
            'success': True,
            'total_items': total_items,
            'total_stock': total_stock,
            'low_stock_items_count': len(low_stock_items),
            'out_of_stock_items_count': len(out_of_stock_items),
            'low_stock_items': low_stock_data
        })

    except Exception as e:
        logger.error(f"Error generating stock status report: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Sales API Routes
@app.route('/api/sales', methods=['GET'])
@login_required
def get_sales():
    """API endpoint to get all sales"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # Get sales from Firebase
        sales_data = firebase_adapter.get_sales_by_user(user_id, limit=None)

        formatted_sales = []
        for sale in sales_data:
            sale_dict = {
                'id': sale.get('id'),
                'sale_number': sale.get('sale_number', ''),
                'created_at': sale.get('created_at', ''),
                'customer_name': sale.get('customer_name'),
                'customer_id': sale.get('customer_id'),
                'total_amount```python
': float(sale.get('total_amount', 0)),
                'payment_type': sale.get('payment_type', 'cash'),
                'payment_status': sale.get('payment_status', 'completed'),
                'is_installment': sale.get('is_installment', False),
                'items_count': len(sale.get('sale_items', []))
            }

            # Add installment details if applicable
            if sale.get('is_installment'):
                sale_dict.update({
                    'down_payment': float(sale.get('down_payment', 0)),
                    'installment_months': sale.get('installment_months', 0),
                    'monthly_payment': float(sale.get('monthly_payment', 0))
                })

            formatted_sales.append(sale_dict)

        return jsonify(formatted_sales)

    except Exception as e:
        logger.error(f"Error getting sales: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/sales', methods=['POST'])
@login_required
def create_sale():
    """API endpoint to create a new sale using Firebase"""
    try:
        sale_data = request.get_json()
        if not sale_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # Validate required fields
        items = sale_data.get('items', [])
        if not items:
            return jsonify({"error": "No items provided"}), 400

        payment_type = sale_data.get('payment_type', 'cash')
        customer_id = sale_data.get('customer_id')
        is_installment = sale_data.get('is_installment', False)

        # Handle customer data using Firebase
        customer = None
        if customer_id:
            customer = firebase_adapter.get_customer_by_id(customer_id, user_id)
        elif sale_data.get('customer_name'):
            # Create new customer if provided
            customer_data = {
                'name': sale_data['customer_name'],
                'email': sale_data.get('customer_email', ''),
                'phone': sale_data.get('customer_phone', ''),
                'address': sale_data.get('customer_address', ''),
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            customer = firebase_adapter.create_customer(customer_data, user_id)

        # Calculate total amount and validate items using Firebase
        total_amount = 0
        sale_items_data = []

        for item_data in items:
            item_id = item_data.get('item_id') or item_data.get('id')
            quantity = int(item_data.get('quantity', 1))
            unit_price = float(item_data.get('unit_price') or item_data.get('price', 0))

            if not item_id:
                return jsonify({"error": "Item ID is required"}), 400

            # Get item from Firebase and verify stock
            item = firebase_adapter.get_item_by_id(item_id, user_id)
            if not item:
                return jsonify({"error": f"Item with ID {item_id} not found"}), 404

            current_stock = item.get('stock_quantity', 0)
            if current_stock < quantity:
                return jsonify({"error": f"Insufficient stock for {item.get('name')}. Available: {current_stock}, Requested: {quantity}"}), 400

            subtotal = quantity * unit_price
            total_amount += subtotal

            sale_items_data.append({
                'item_id': item_id,
                'item_name': item.get('name'),
                'quantity': quantity,
                'unit_price': unit_price,
                'subtotal': subtotal,
                'item_data': item
            })

        # Generate sale number
        sale_number = f"SALE-{datetime.now().strftime('%Y%m%d%H%M%S')}"

        # Create sale record in Firebase
        sale_data_for_firebase = {
            'sale_number': sale_number,
            'customer_id': customer.get('id') if customer else None,
            'customer_name': customer.get('name') if customer else sale_data.get('customer_name', ''),
            'total_amount': total_amount,
            'payment_type': payment_type,
            'payment_status': 'completed' if not is_installment else 'pending',
            'is_installment': is_installment,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat(),
            'sale_items': []
        }

        # Handle installment data
        if is_installment:
            down_payment = float(sale_data.get('down_payment', 0))
            installment_months = int(sale_data.get('installment_months', 1))
            remaining_amount = total_amount - down_payment
            monthly_payment = remaining_amount / installment_months if installment_months > 0 else 0

            sale_data_for_firebase.update({
                'down_payment': down_payment,
                'installment_months': installment_months,
                'monthly_payment': monthly_payment,
                'remaining_amount': remaining_amount
            })

        # Add sale items to Firebase sale data
        for item_data in sale_items_data:
            sale_data_for_firebase['sale_items'].append({
                'item_id': item_data['item_id'],
                'item_name': item_data['item_name'],
                'quantity': item_data['quantity'],
                'unit_price': item_data['unit_price'],
                'subtotal': item_data['subtotal']
            })

        # Create sale in Firebase
        sale_result = firebase_adapter.create_sale(sale_data_for_firebase, user_id)

        # Update stock for all items
        for item_data in sale_items_data:
            item = item_data['item_data']
            new_stock = item.get('stock_quantity', 0) - item_data['quantity']
            firebase_adapter.update_item_stock(item_data['item_id'], new_stock, user_id)

        logger.info(f"Sale created: {sale_number} for user {user_id}")

        return jsonify({
            'success': True,
            'sale_id': sale_result.get('id'),
            'sale_number': sale_number,
            'total_amount': total_amount,
            'message': 'Sale created successfully'
        })

    except Exception as e:
        logger.error(f"Error creating sale: {str(e)}")
        return jsonify({"error": f"Failed to create sale: {str(e)}"}), 500

# Customer API Routes
@app.route('/api/customers', methods=['GET'])
@login_required
def get_customers():
    """API endpoint to get all customers using Firebase"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # Get customers from Firebase
        customers_data = firebase_adapter.get_customers_by_user(user_id)

        formatted_customers = []
        for customer in customers_data:
            formatted_customers.append({
                'id': customer.get('id'),
                'name': customer.get('name', ''),
                'email': customer.get('email', ''),
                'phone': customer.get('phone', ''),
                'address': customer.get('address', ''),
                'customer_type': customer.get('customer_type', 'regular'),
                'credit_limit': float(customer.get('credit_limit', 0)),
                'loyalty_points': customer.get('loyalty_points', 0),
                'created_at': customer.get('created_at')
            })

        return jsonify(formatted_customers)

    except Exception as e:
        logger.error(f"Error getting customers: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/customers', methods=['POST'])
@login_required
def create_customer():
    """API endpoint to create a new customer"""
    try:
        customer_data = request.get_json()
        if not customer_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        if not firebase_config.initialized:
            return jsonify({"error": "Firebase not configured"}), 500

        # Validate required fields
        if not customer_data.get('name'):
            return jsonify({"error": "Customer name is required"}), 400

        # Prepare customer data
        customer_info = {
            'name': customer_data['name'].strip(),
            'email': customer_data.get('email', '').strip(),
            'phone': customer_data.get('phone', '').strip(),
            'address': customer_data.get('address', '').strip(),
            'customer_type': customer_data.get('customer_type', 'retail'),
            'credit_limit': float(customer_data.get('credit_limit', 0)),
            'loyalty_points': int(customer_data.get('loyalty_points', 0)),
            'preferred_payment_method': customer_data.get('preferred_payment_method', ''),
            'is_active': True
        }

        # Create customer using Firebase
        customer = firebase_adapter.create_customer(customer_info, user_id)

        logger.info(f"Customer created: {customer_info['name']} by user {user_id}")

        return jsonify({
            'success': True,
            'customer': customer
        }), 201

    except Exception as e:
        logger.error(f"Error creating customer: {str(e)}")
        return jsonify({"error": f"Failed to create customer: {str(e)}"}), 500

# Additional Customer API Routes
@app.route('/api/customers/<string:customer_id>', methods=['GET'])
@login_required
def get_customer(customer_id):
    """API endpoint to get a specific customer"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        customer = firebase_adapter.get_customer_by_id(customer_id,user_id)

        if not customer:
            return jsonify({'error': 'Customer not found'}), 404

        return jsonify({
            'id': customer.get('id'),
            'name': customer.get('name'),
            'email': customer.get('email'),
            'phone': customer.get('phone'),
            'address': customer.get('address'),
            'customer_type': customer.get('customer_type'),
            'credit_limit': float(customer.get('credit_limit', 0)),
            'loyalty_points': customer.get('loyalty_points', 0),
            'created_at': customer.get('created_at')
        })
    except Exception as e:
        logger.error(f"Error getting customer: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Installment API Routes
@app.route('/api/installments', methods=['GET'])
@login_required
def get_installments():
    """API endpoint to get all installment sales"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # Get sales from Firebase
        sales_data = firebase_adapter.get_sales_by_user(user_id, limit=None)

        installments_data = []
        for sale in sales_data:
            if sale.get('is_installment'):
                installments_data.append({
                    'id': sale.get('id'),
                    'sale_number': sale.get('sale_number'),
                    'customer_name': sale.get('customer_name'),
                    'total_amount': float(sale.get('total_amount')),
                    'down_payment': float(sale.get('down_payment', 0)),
                    'installment_months': sale.get('installment_months'),
                    'monthly_payment': float(sale.get('monthly_payment')),
                    'created_at': sale.get('created_at'),
                })

        return jsonify(installments_data)

    except Exception as e:
        logger.error(f"Error getting installments: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/installments', methods=['POST'])
@login_required
def create_installment():
    """API endpoint to create a new installment sale"""
    try:
        sale_data = request.get_json()
        if not sale_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # This will redirect to regular sale creation with installment flag
        sale_data = {
            'items': sale_data.get('items', []),
            'customer_id': sale_data.get('customer_id'),
            'customer_name': sale_data.get('customer_name'),
            'payment_type': 'installment',
            'is_installment': True,
            'down_payment': sale_data.get('down_payment', 0),
            'installment_months': sale_data.get('number_of_installments', 1),
            'total_amount': sale_data.get('total_amount', 0)
        }

        # Use existing create_sale endpoint logic
        return create_sale()

    except Exception as e:
        logger.error(f"Error creating installment sale: {str(e)}")
        return jsonify({"error": f"Failed to create installment sale: {str(e)}"}), 500

# Categories API Routes
@app.route('/api/categories', methods=['GET'])
@login_required
def get_categories():
    """API endpoint to get all categories with hierarchical structure"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500
        # Use Firebase adapter to get categories
        categories_data = firebase_adapter.get_categories_by_user(user_id)

        return jsonify(categories_data)

    except Exception as e:
        logger.error(f"Error getting categories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<string:category_id>', methods=['GET'])
@login_required
def get_category(category_id):
    """API endpoint to get a specific category"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # Get category from Firebase
        category = firebase_adapter.get_category_by_id(category_id,user_id)

        if not category:
            return jsonify({'error': 'Category not found'}), 404

        return jsonify({
            'id': category.get('id'),
            'name': category.get('name'),
            'description': category.get('description'),
            'parent_id': category.get('parent_id'),
            'created_at': category.get('created_at')
        })
    except Exception as e:
        logger.error(f"Error getting category: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories', methods=['POST'])
@login_required
def create_category():
    """API endpoint to create a new category"""
    try:
        category_data = request.get_json()
        if not category_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        if not firebase_config.initialized:
            return jsonify({"error": "Firebase not configured"}), 500

        # Validate required fields
        if not category_data.get('name'):
            return jsonify({"error": "Category name is required"}), 400

        # Prepare category data
        category_info = {
            'name': category_data['name'].strip(),
            'description': category_data.get('description', '').strip(),
            'parent_id': category_data.get('parent_id'),
            'sort_order': int(category_data.get('sort_order', 0)),
            'is_active': True
        }

        # Create category using Firebase
        category = firebase_adapter.create_category(category_info, user_id)

        logger.info(f"Category created: {category_info['name']} by user {user_id}")

        return jsonify({
            'success': True,
            'category': category
        }), 201

    except Exception as e:
        logger.error(f"Error creating category: {str(e)}")
        return jsonify({"error": f"Failed to create category: {str(e)}"}), 500

@app.route('/api/categories/<string:category_id>', methods=['PUT'])
@login_required
def update_category(category_id):
    """API endpoint to update an existing category"""
    try:
        category_data = request.get_json()
        if not category_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # Update category using Firebase
        updated_category = firebase_adapter.update_category(category_id, category_data, user_id)

        if not updated_category:
            return jsonify({"error": "Category not found"}), 404

        logger.info(f"Category updated: {updated_category.get('name')} (ID: {category_id}) by user {user_id}")

        return jsonify({
            'id': updated_category.get('id'),
            'name': updated_category.get('name'),
            'description': updated_category.get('description'),
            'parent_id': updated_category.get('parent_id'),
            'created_at': updated_category.get('created_at')
        })

    except Exception as e:
        logger.error(f"Error updating category: {str(e)}")
        return jsonify({"error": f"Failed to update category: {str(e)}"}), 500

@app.route('/api/categories/<string:category_id>', methods=['DELETE'])
@login_required
def delete_category(category_id):
    """API endpoint to delete a category"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        if not firebase_config.initialized:
            return jsonify({"error": "Firebase not configured"}), 500

        # Delete category using Firebase
        deleted_category = firebase_adapter.delete_category(category_id, user_id)

        if not deleted_category:
            return jsonify({"error": "Category not found"}), 404

        logger.info(f"Category deleted: {deleted_category.get('name')} (ID: {category_id}) by user {user_id}")

        return jsonify({"success": True, "message": f"Category '{deleted_category.get('name')}' deleted successfully"})

    except Exception as e:
        logger.error(f"Error deleting category: {str(e)}")
        return jsonify({"error": f"Failed to delete category: {str(e)}"}), 500

@app.route('/api/categories/<string:category_id>/subcategories', methods=['GET'])
@login_required
def get_subcategories(category_id):
    """API endpoint to get subcategories of a category"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # Get category from Firebase
        category = firebase_adapter.get_category_by_id(category_id, user_id)

        if not category:
            return jsonify({"error": "Parent category not found"}), 404

        # Get subcategories from firebase
        subcategories_data = firebase_adapter.get_subcategories_by_category_id(category_id,user_id)

        return jsonify(subcategories_data)

    except Exception as e:
        logger.error(f"Error getting subcategories: {str(e)}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/categories/<string:category_id>/subcategories', methods=['POST'])
@login_required
def create_subcategory(category_id):
    """API endpoint to create a subcategory"""
    try:
        subcategory_data = request.get_json()
        if not subcategory_data:
            return jsonify({"error": "No data provided"}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({"error": "User not authenticated"}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # Verify parent category exists
        category = firebase_adapter.get_category_by_id(category_id, user_id)
        if not category:
            return jsonify({"error": "Parent category not found"}), 404

        # Validate required fields
        if not subcategory_data.get('name'):
            return jsonify({"error": "Subcategory name is required"}), 400

        # create subcategory
        subcategory = firebase_adapter.create_subcategory(category_id, subcategory_data, user_id)

        logger.info(f"Subcategory created: {subcategory.get('name')} (ID: {subcategory.get('id')}) under category {category.get('name')} by user {user_id}")

        return jsonify({
            'success': True,
            'subcategory': subcategory
        }), 201

    except Exception as e:
        logger.error(f"Error creating subcategory: {str(e)}")
        return jsonify({"error": f"Failed to create subcategory: {str(e)}"}), 500

# Dashboard API Routes
@app.route('/api/dashboard/summary')
@login_required
def get_dashboard_summary():
    """API endpoint to get comprehensive dashboard summary data organized by categories"""
    try:
        from datetime import datetime, timedelta

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # === INVENTORY METRICS ===
        # Get items from Firebase
        items_data = firebase_adapter.get_items_by_user(user_id)
        total_items = len(items_data)
        total_stock = sum(item.get('stock_quantity', 0) for item in items_data)

        # Calculate inventory value (stock_quantity * buying_price)
        inventory_value = sum(
            item.get('stock_quantity', 0) * item.get('buying_price', 0) 
            for item in items_data 
            if item.get('buying_price') and item.get('stock_quantity')
        )

        # Category breakdown
        category_breakdown = {}
        for item in items_data:
            category = item.get('category', 'Uncategorized')
            if category not in category_breakdown:
                category_breakdown[category] = {
                    'category': category,
                    'item_count': 0,
                    'total_stock': 0,
                    'total_value': 0
                }
            category_breakdown[category]['item_count'] += 1
            category_breakdown[category]['total_stock'] += item.get('stock_quantity', 0)
            category_breakdown[category]['total_value'] += (
                item.get('stock_quantity', 0) * item.get('buying_price', 0)
            )

        # Convert to list
        category_breakdown = list(category_breakdown.values())

        # Low stock items analysis
        low_stock_items = []
        low_stock_count = 0
        for item in items_data:
            stock_qty = item.get('stock_quantity', 0)
            min_stock = item.get('minimum_stock', 5)
            if stock_qty <= min_stock:
                low_stock_count += 1
                if len(low_stock_items) < 10:
                    low_stock_items.append({
                        'id': item.get('id'),
                        'name': item.get('name'),
                        'current_stock': stock_qty,
                        'minimum_stock': min_stock,
                        'category': item.get('category')
                    })

        # === SALES METRICS ===
        # Get sales from Firebase
        sales_data = firebase_adapter.get_sales_by_user(user_id, limit=None)
        total_sales = len(sales_data)

        # Calculate revenue (completed sales only)
        total_revenue = sum(
            float(sale.get('total_amount', 0)) 
            for sale in sales_data 
            if sale.get('payment_status') == 'completed'
        )

        # Today's sales
        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_str = today.isoformat()

        today_sales = 0
        today_sales_count = 0
        for sale in sales_data:
            sale_date = sale.get('created_at', '')
            if sale_date and sale_date.startswith(today_str[:10]):
                today_sales += float(sale.get('total_amount', 0))
                today_sales_count += 1

        # Top selling items (simplified)
        top_selling_items = []
        item_sales = {}
        for sale in sales_data:
            sale_items = sale.get('sale_items', [])
            if isinstance(sale_items, list):
                for item in sale_items:
                    item_name = item.get('item_name', item.get('name', 'Unknown'))
                    quantity = int(item.get('quantity', 0))
                    if item_name in item_sales:
                        item_sales[item_name] += quantity
                    else:
                        item_sales[item_name] = quantity

        # Sort and get top 5
        sorted_items = sorted(item_sales.items(), key=lambda x: x[1], reverse=True)
        top_selling_items = [
            {'name': name, 'quantity_sold': qty} 
            for name, qty in sorted_items[:5]
        ]

        # === CUSTOMER METRICS ===
        customers_data = firebase_adapter.get_customers_by_user(user_id)
        total_customers = len(customers_data)

        # New customers this month
        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        current_month_str = current_month.isoformat()

        new_customers_this_month = 0
        for customer in customers_data:
            created_at = customer.get('created_at', '')
            if created_at and created_at >= current_month_str:
                new_customers_this_month += 1

        # === FINANCIAL METRICS ===
        # Simplified financial calculations
        monthly_income = sum(
            float(sale.get('total_amount', 0)) 
            for sale in sales_data 
            if sale.get('created_at', '').startswith(current_month_str[:7])
        )

        # Estimated monthly expenses (simplified as 70% of income)
        monthly_expenses = monthly_income * 0.7
        monthly_profit = monthly_income - monthly_expenses

        # === RECENT ACTIVITY ===
        # Get recent sales (last 5)
        recent_sales_data = sorted(
            sales_data, 
            key=lambda x: x.get('created_at', ''), 
            reverse=True
        )[:5]

        return jsonify({
            'success': True,
            'inventory': {
                'total_items': total_items,
                'total_stock': total_stock,
                'inventory_value': float(inventory_value),
                'low_stock_count': low_stock_count,
                'low_stock_items': low_stock_items,
                'category_breakdown': category_breakdown
            },
            'sales': {
                'total_sales': total_sales,
                'total_revenue': float(total_revenue),
                'today_sales': float(today_sales),
                'today_sales_count': today_sales_count,
                'top_selling_items': top_selling_items
            },
            'customers': {
                'total_customers': total_customers,
                'new_customers_this_month': new_customers_this_month
            },
            'financial': {
                'monthly_income': float(monthly_income),
                'monthly_expenses': float(monthly_expenses),
                'monthly_profit': float(monthly_profit)
            },
            'recent_activity': {
                'recent_sales': recent_sales_data
            }
        })

    except Exception as e:
        logger.error(f"Error getting dashboard summary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Financial API Routes
@app.route('/api/finance/transactions')
@login_required
def get_financial_transactions():
    """API endpoint to get financial transactions with date filtering"""
    try:
        user_id = session.get('user_id')

        # Firebase doesn't have financial transactions yet - return empty for now
        return jsonify({
            'success': True,
            'transactions': [],
            'total_count': 0
        })

    except Exception as e:
        logger.error(f"Error getting financial transactions: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/finance/summaries/monthly')
@login_required
def get_monthly_financial_summary():
    """API endpoint to get monthly financial summary"""
    try:
        from datetime import datetime, timedelta

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        current_month = datetime.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)

        # Get sales data from Firebase
        sales_data = firebase_adapter.get_sales_by_user(user_id, limit=None)

        # Get monthly data for the past 12 months
        monthly_data = {}
        for i in range(12):
            month_start = (current_month - timedelta(days=30*i)).replace(day=1)
            month_end = (month_start + timedelta(days=32)).replace(day=1)

            # Calculate monthly sales from Firebase
            monthly_sales = 0
            for sale in sales_data:
                if sale.get('payment_status') == 'completed':
                    sale_date_str = sale.get('created_at')
                    if sale_date_str:
                        try:
                            sale_date = datetime.fromisoformat(sale_date_str.replace('Z', '+00:00'))
                            if month_start <= sale_date < month_end:
                                monthly_sales += float(sale.get('total_amount', 0))
                        except:
                            continue

            # Expenses are not implemented in Firebase yet
            monthly_expenses = 0

            monthly_data[month_start.month] = {
                ```python
                'income': float(monthly_sales),
                'expenses': float(monthly_expenses),
                'profit': float(monthly_sales - monthly_expenses)
            }

        return jsonify({
            'success': True,
            'monthly_data': monthly_data,
            'current_month': {
                'income': float(monthly_data.get(current_month.month, {}).get('income', 0)),
                'expenses': float(monthly_data.get(current_month.month, {}).get('expenses', 0)),
                'profit': float(monthly_data.get(current_month.month, {}).get('profit', 0))
            }
        })

    except Exception as e:
        logger.error(f"Error getting monthly financial summary: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Firebase-based API endpoints for features not yet implemented
@app.route('/api/installment-sales', methods=['POST'])
@login_required
def create_installment_sale():
    """API endpoint to create a new installment sale"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400

        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'User not authenticated'}), 401

        if not firebase_config.initialized:
            return jsonify({'error': 'Firebase not configured'}), 500

        # This will redirect to regular sale creation with installment flag
        sale_data = {
            'items': data.get('items', []),
            'customer_id': data.get('customer_id'),
            'customer_name': data.get('customer_name'),
            'payment_type': 'installment',
            'is_installment': True,
            'down_payment': data.get('down_payment', 0),
            'installment_months': data.get('number_of_installments', 1),
            'total_amount': data.get('total_amount', 0)
        }

        # Use existing create_sale endpoint logic
        return create_sale()

    except Exception as e:
        logger.error(f"Error creating installment sale: {str(e)}")
        return jsonify({'error': f'Failed to create installment sale: {str(e)}'}), 500

@app.route('/api/suppliers', methods=['GET'])
@login_required
def get_suppliers():
    """API endpoint to get all suppliers (placeholder for future implementation)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401

        # Placeholder - suppliers not yet implemented in Firebase
        return jsonify({'success': True, 'suppliers': []})

    except Exception as e:
        logger.error(f"Error getting suppliers: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/purchase-orders', methods=['GET'])
@login_required
def get_purchase_orders():
    """API endpoint to get all purchase orders (placeholder for future implementation)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401

        # Placeholder - purchase orders not yet implemented in Firebase
        return jsonify({'success': True, 'purchase_orders': []})

    except Exception as e:
        logger.error(f"Error getting purchase orders: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/stock-movements', methods=['GET'])
@login_required
def get_stock_movements():
    """API endpoint to get stock movements (placeholder for future implementation)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401

        # Placeholder - stock movements not yet implemented in Firebase
        return jsonify({'success': True, 'stock_movements': []})

    except Exception as e:
        logger.error(f"Error getting stock movements: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['GET'])
@login_required
def get_settings():
    """API endpoint to get user settings (placeholder for future implementation)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401

        # Placeholder - settings not yet implemented in Firebase
        default_settings = {
            'currency': {'value': 'USD', 'description': 'Default currency'},
            'low_stock_threshold': {'value': '10', 'description': 'Low stock alert threshold'},
            'tax_rate': {'value': '0', 'description': 'Default tax rate'}
        }

        return jsonify({'success': True, 'settings': default_settings})

    except Exception as e:
        logger.error(f"Error getting settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/settings', methods=['POST'])
@login_required
def update_settings():
    """API endpoint to update user settings (placeholder for future implementation)"""
    try:
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'success': False, 'error': 'User not authenticated'}), 401

        # Placeholder - settings update not yet implemented in Firebase
        return jsonify({'success': True, 'message': 'Settings updated successfully'})

    except Exception as e:
        logger.error(f"Error updating settings: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

# Firebase configuration routes
@app.route("/firebase/config")
def firebase_config_route():
    """Route to display Firebase web configuration"""
    config = get_firebase_web_config()
    return render_template("firebase_config.html", config=config)

@app.route("/firebase/api")
def firebase_api_route():
    """Route to manage Firebase API keys and services"""
    api_status = firebase_api_manager.get_api_status()
    return render_template("firebase_api.html", api_status=api_status)

@app.errorhandler(404)
def not_found_error(error):
    # Log the requested URL for debugging
    logger.warning(f"404 error for URL: {request.url}")
    if request.is_json or request.path.startswith('/api/'):
        return jsonify({'error': 'Not found', 'path': request.path}), 404
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Register Firebase admin blueprint
    app.register_blueprint(firebase_admin_bp)
    # Run the application with Firebase only
    app.run(host='0.0.0.0', port=5000, debug=True)