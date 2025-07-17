
#!/usr/bin/env python3
"""
Quick reset using Flask app context
"""

from app import app, db
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def reset_all_data():
    """Reset all application data"""
    with app.app_context():
        try:
            print("🗑️  Resetting all application data...")
            
            # Drop all tables
            db.drop_all()
            print("✅ All tables dropped")
            
            # Recreate all tables
            db.create_all()
            print("✅ All tables recreated")
            
            print("\n🎉 Database reset complete!")
            print("All data has been removed and tables recreated.")
            
            return True
            
        except Exception as e:
            logger.error(f"Error during reset: {e}")
            return False

if __name__ == '__main__':
    confirm = input("⚠️  This will DELETE ALL DATA. Type 'RESET' to confirm: ")
    if confirm == "RESET":
        reset_all_data()
    else:
        print("❌ Operation cancelled")
