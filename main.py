#!/usr/bin/env python3
"""
Main entry point for the Flask application
"""

from app import app

if __name__ == '__main__':
    # Run the application
    app.run(host='0.0.0.0', port=5000, debug=True)