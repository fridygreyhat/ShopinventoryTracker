
#!/usr/bin/env python3
"""
WSGI entry point for production deployment
"""

import os
import sys
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(__file__))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    # Import the Flask app and initialize database
    from app import app, init_database
    
    # Initialize database on startup
    with app.app_context():
        try:
            success = init_database()
            if success:
                logger.info("✅ Database initialized successfully for WSGI")
            else:
                logger.error("❌ Database initialization failed")
        except Exception as e:
            logger.error(f"❌ Database initialization error: {str(e)}")
    
    # Make app available for WSGI server
    application = app
    
    if __name__ == "__main__":
        # Fallback for direct execution
        app.run(host='0.0.0.0', port=5000, debug=False)
        
except Exception as e:
    logger.error(f"❌ WSGI startup error: {str(e)}")
    raise
