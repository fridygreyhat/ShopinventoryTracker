#!/usr/bin/env python3
"""
Main entry point for the Flask application
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from flask import Flask
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import Firebase components
from extensions import configure_database
from firebase_config import firebase_config

def create_app():
    """Create Flask app with Firebase configuration"""
    app = Flask(__name__)

    # Configure secret key and session
    app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-change-in-production')
    app.config['SESSION_PERMANENT'] = False
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)

    # Configure Firebase database only
    if not configure_database(app, use_firebase=True):
        logger.error("❌ Firebase configuration failed. Please check your FIREBASE_CREDENTIALS environment variable.")
        sys.exit(1)

    return app

if __name__ == '__main__':
    # Import the main app from app.py
    from app import app

    # Run the application with Firebase
    app.run(host='0.0.0.0', port=5000, debug=True)