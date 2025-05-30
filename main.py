
#!/usr/bin/env python3
"""
Main entry point for the Flask application
"""

import os
import sys
import logging

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

try:
    from app import app
    
    if __name__ == '__main__':
        # Get port from environment or default to 5000
        port = int(os.environ.get('PORT', 5000))
        
        # Run the Flask app
        app.run(
            host='0.0.0.0',
            port=port,
            debug=True,
            use_reloader=True
        )
        
except ImportError as e:
    print(f"Error importing app: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error starting application: {e}")
    sys.exit(1)
