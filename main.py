
from app import app

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
#!/usr/bin/env python3
"""
Main entry point for the Flask application
"""

import os
import logging
from app import app

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)

if __name__ == '__main__':
    # Get port from environment variable or default to 5000
    port = int(os.environ.get('PORT', 5000))
    
    # Run the Flask app
    app.run(
        host='0.0.0.0',
        port=port,
        debug=True
    )
