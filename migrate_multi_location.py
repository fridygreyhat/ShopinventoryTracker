
"""
Migration script to add multi-location inventory tables
Run this script to update your database with multi-location support
"""

from app import app, db
from models import Location, LocationStock, StockTransfer, StockTransferItem, Item, User

def migrate_database():
    """Create new tables and update existing ones for multi-location support"""
    
    with app.app_context():
        try:
            print("Creating multi-location tables...")
            
            # Create new tables
            db.create_all()
            
            # Add the track_by_location column to existing items table if it doesn't exist
            try:
                # This will fail if the column already exists, which is fine
                db.engine.execute('ALTER TABLE item ADD COLUMN track_by_location BOOLEAN DEFAULT 0')
                print("Added track_by_location column to items table")
            except Exception as e:
                print(f"Column track_by_location may already exist: {e}")
            
            # Create a default location for existing users who don't have any
            users_without_locations = db.session.query(User).outerjoin(Location).filter(Location.id == None).all()
            
            for user in users_without_locations:
                default_location = Location(
                    name="Main Location",
                    code="MAIN",
                    type="warehouse",
                    is_default=True,
                    is_active=True,
                    user_id=user.id
                )
                db.session.add(default_location)
                print(f"Created default location for user: {user.username}")
            
            db.session.commit()
            print("Multi-location database migration completed successfully!")
            print("\nNew features available:")
            print("- Multi-location inventory tracking")
            print("- Stock transfers between locations")
            print("- Location-specific reporting")
            print("- Stock level management per location")
            
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")
            raise

if __name__ == "__main__":
    migrate_database()
