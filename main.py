#!/usr/bin/env python3
"""
Main entry point for the Flask application
"""

from app import app
from extensions import configure_database
import os

# Configure PostgreSQL database
configure_database(app)

if __name__ == '__main__':
    # Ensure database tables are created
    with app.app_context():
        from extensions import db
        try:
            db.create_all()
            print("✅ Database tables created/verified")
        except Exception as e:
            print(f"❌ Error creating database tables: {str(e)}")

    # Start the application
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)