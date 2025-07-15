#!/usr/bin/env python3
"""
Main entry point for the Flask application
"""

import os
import logging
from app import app, init_database

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if __name__ == '__main__':
    # Initialize database with proper error handling
    try:
        success = init_database()
        if not success:
            logger.error("Database initialization failed - exiting")
            exit(1)
        logger.info("✅ Database initialization completed successfully")
        
        # Print available routes for debugging
        logger.info("📍 Available routes:")
        for rule in app.url_map.iter_rules():
            logger.info(f"  {rule.rule} -> {rule.endpoint} [{', '.join(rule.methods)}]")
            
    except Exception as e:
        logger.error(f"❌ Critical error during startup: {str(e)}")
        exit(1)

    # Start the application
    port = int(os.environ.get('PORT', 5000))
    logger.info(f"🚀 Starting Flask application on 0.0.0.0:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)